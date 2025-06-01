"""BitBucket provider implementation.

This module provides the BitBucket provider for mgit, supporting repository
operations through the BitBucket API.
"""

import asyncio
import base64
import re
from typing import Any, AsyncIterator, Dict, List, Optional

import aiohttp

from ..security.credentials import mask_sensitive_data, validate_bitbucket_app_password

# Security imports
from ..security.logging import SecurityLogger
from ..security.monitor import get_security_monitor
from ..security.validation import SecurityValidator
from .base import AuthMethod, GitProvider, Organization, Project, Repository
from .exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    PermissionError,
    RepositoryNotFoundError,
)


class BitBucketProvider(GitProvider):
    """BitBucket provider implementation.

    Supports:
    - App Password authentication (future implementation)
    - OAuth 2.0 (future implementation)
    - Repository listing and cloning
    - Workspace (organization) management
    - Project hierarchy support

    Note: BitBucket uses workspaces (similar to organizations) and projects
    for repository organization.
    """

    PROVIDER_NAME = "bitbucket"
    SUPPORTED_AUTH_METHODS = [AuthMethod.APP_PASSWORD, AuthMethod.OAUTH]
    DEFAULT_API_VERSION = "2.0"  # BitBucket API version

    # BitBucket URL patterns
    BITBUCKET_PATTERNS = [
        r"https?://bitbucket\.org",
        r"git@bitbucket\.org",
        r"ssh://git@bitbucket\.org",
        r"https?://api\.bitbucket\.org",
    ]

    def __init__(self, config: Dict[str, Any]):
        """Initialize BitBucket provider.

        Args:
            config: Configuration dictionary with:
                - base_url: BitBucket API base URL (default: https://api.bitbucket.org/2.0)
                - auth_method: Authentication method (app_password or oauth)
                - username: BitBucket username (if auth_method is app_password)
                - app_password: App password (if auth_method is app_password)
                - oauth_token: OAuth token (if auth_method is oauth)
                - api_version: BitBucket API version (optional)
        """
        # Security components
        self._validator = SecurityValidator()
        self._monitor = get_security_monitor()

        self.base_url = config.get("base_url", "https://api.bitbucket.org/2.0")
        self.auth_method = config.get("auth_method", "app_password")
        self.username = config.get("username", "")
        self.app_password = config.get("app_password", "")
        self.workspace = config.get("workspace", "")
        self.oauth_token = config.get("oauth_token", "")
        self._session: Optional[aiohttp.ClientSession] = None
        self.logger = SecurityLogger(__name__)

        super().__init__(config)

    def _validate_config(self) -> None:
        """Validate BitBucket-specific configuration.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not self.workspace:
            raise ConfigurationError("BitBucket workspace is required")

        # Validate workspace name
        if not self._validator.validate_organization_name(self.workspace):
            self._monitor.log_validation_failure(
                "bitbucket_workspace", self.workspace, "Invalid workspace name format"
            )
            raise ConfigurationError("Invalid BitBucket workspace name format")

        # Validate base URL
        if not self._validator.validate_url(self.base_url):
            raise ConfigurationError(
                f"Invalid or insecure base_url: {mask_sensitive_data(self.base_url)}"
            )

        if self.auth_method == "app_password":
            if not self.username:
                raise ConfigurationError(
                    "Username is required for app_password authentication"
                )
            if not self.app_password:
                raise ConfigurationError(
                    "App password is required for app_password authentication"
                )
            # Validate app password format
            if not validate_bitbucket_app_password(self.app_password):
                self._monitor.log_validation_failure(
                    "bitbucket_app_password",
                    mask_sensitive_data(self.app_password),
                    "Invalid app password format",
                )
                raise ConfigurationError("Invalid BitBucket app password format")
        elif self.auth_method == "oauth":
            if not self.oauth_token:
                raise ConfigurationError(
                    "OAuth token is required for oauth authentication"
                )
        else:
            raise ConfigurationError(f"Unsupported auth method: {self.auth_method}")

    async def _ensure_session(self) -> None:
        """Ensure we have a valid session for the current event loop."""

        try:
            current_loop = asyncio.get_running_loop()

            # Check if we need a new session
            if not self._session or self._session.closed:
                self._session = aiohttp.ClientSession()
            else:
                # Check if session belongs to current loop
                if (
                    hasattr(self._session, "_loop")
                    and self._session._loop != current_loop
                ):
                    # Close old session and create new one
                    await self._session.close()
                    self._session = aiohttp.ClientSession()
        except Exception as e:
            self.logger.debug(f"Session creation error: {e}")
            self._session = aiohttp.ClientSession()

    async def authenticate(self) -> bool:
        """Authenticate with BitBucket.

        Returns:
            bool: True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        if self._authenticated:
            return True

        try:
            await self._ensure_session()

            # Test authentication with GET /user
            headers = self._get_auth_headers()

            async with self._session.get(
                f"{self.base_url}/user", headers=headers
            ) as response:
                if response.status == 200:
                    self._authenticated = True
                    self.logger.debug("BitBucket authentication successful")
                    return True
                elif response.status == 401:
                    raise AuthenticationError("Invalid credentials")
                else:
                    text = await response.text()
                    raise AuthenticationError(
                        f"Authentication failed with status {response.status}: {text}"
                    )

        except aiohttp.ClientError as e:
            raise ConnectionError(f"Network error during authentication: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during authentication: {e}")
            raise AuthenticationError(f"Authentication failed: {e}")

    async def test_connection(self) -> bool:
        """Test BitBucket API connection.

        Returns:
            bool: True if connection is valid

        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Test connection by attempting authentication
            result = await self.authenticate()
            return result
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
        # Don't cleanup here - the session will be reused for subsequent operations

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None
            self._authenticated = False

    async def list_organizations(self) -> List[Organization]:
        """List accessible BitBucket workspaces.

        Returns:
            List of Organization objects (workspaces in BitBucket)

        Raises:
            APIError: If API call fails
        """
        if not await self.authenticate():
            raise AuthenticationError("Authentication required")

        await self._ensure_session()
        headers = self._get_auth_headers()
        url = f"{self.base_url}/workspaces"
        organizations = []

        try:
            # Handle pagination
            while url:
                async with self._session.get(url, headers=headers) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise APIError(
                            f"Failed to list workspaces: {response.status} - {text}",
                            self.PROVIDER_NAME,
                        )

                    data = await response.json()

                    # Process workspaces from current page
                    for workspace_data in data.get("values", []):
                        organizations.append(
                            Organization(
                                name=workspace_data.get(
                                    "slug", workspace_data.get("name", "")
                                ),
                                url=workspace_data.get("links", {})
                                .get("html", {})
                                .get("href", ""),
                                provider=self.PROVIDER_NAME,
                                metadata={
                                    "uuid": workspace_data.get("uuid"),
                                    "display_name": workspace_data.get("name"),
                                    "type": workspace_data.get("type", "workspace"),
                                    "is_private": workspace_data.get(
                                        "is_private", False
                                    ),
                                },
                            )
                        )

                    # Get next page URL
                    url = data.get("next")

            return organizations

        except aiohttp.ClientError as e:
            raise ConnectionError(f"Network error while listing workspaces: {e}")

    async def list_projects(self, organization: str) -> List[Project]:
        """List projects in a BitBucket workspace.

        Args:
            organization: Workspace slug

        Returns:
            List of Project objects

        Raises:
            APIError: If API call fails
        """
        if not await self.authenticate():
            raise AuthenticationError("Authentication required")

        await self._ensure_session()
        headers = self._get_auth_headers()
        url = f"{self.base_url}/workspaces/{organization}/projects"
        projects = []

        try:
            # Handle pagination
            while url:
                async with self._session.get(url, headers=headers) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise APIError(
                            f"Failed to list projects: {response.status} - {text}",
                            self.PROVIDER_NAME,
                        )

                    data = await response.json()

                    # Process projects from current page
                    for project_data in data.get("values", []):
                        projects.append(
                            Project(
                                name=project_data.get("name", ""),
                                organization=organization,
                                description=project_data.get("description"),
                                metadata={
                                    "key": project_data.get("key"),
                                    "uuid": project_data.get("uuid"),
                                    "type": project_data.get("type", "project"),
                                    "is_private": project_data.get("is_private", False),
                                    "created_on": project_data.get("created_on"),
                                    "updated_on": project_data.get("updated_on"),
                                },
                            )
                        )

                    # Get next page URL
                    url = data.get("next")

            return projects

        except aiohttp.ClientError as e:
            raise ConnectionError(f"Network error while listing projects: {e}")

    async def list_repositories(
        self,
        organization: str,
        project: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Repository]:
        """List BitBucket repositories.

        Args:
            organization: Workspace slug
            project: Optional project key
            filters: Optional filters:
                - language: Filter by primary language
                - is_private: Filter private/public repos
                - updated_on: Filter by last update date
                - has_issues: Filter by issue tracker status

        Yields:
            Repository objects

        Raises:
            APIError: If API call fails
        """
        if not await self.authenticate():
            raise AuthenticationError("Authentication required")

        await self._ensure_session()
        headers = self._get_auth_headers()
        url = f"{self.base_url}/repositories/{organization}"

        # Add query parameters for filters
        params = {}
        if filters:
            if "language" in filters:
                params["q"] = f'language="{filters["language"]}"'
            if "is_private" in filters:
                private_filter = (
                    "is_private=true" if filters["is_private"] else "is_private=false"
                )
                if "q" in params:
                    params["q"] += f" AND {private_filter}"
                else:
                    params["q"] = private_filter

        try:
            # Handle pagination
            while url:
                async with self._session.get(
                    url, headers=headers, params=params
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise APIError(
                            f"Failed to list repositories: {response.status} - {text}",
                            self.PROVIDER_NAME,
                        )

                    data = await response.json()

                    # Yield repositories from current page
                    for repo_data in data.get("values", []):
                        yield self._convert_to_repository(repo_data)

                    # Get next page URL
                    url = data.get("next")
                    params = {}  # Clear params for subsequent pages

        except aiohttp.ClientError as e:
            raise ConnectionError(f"Network error while listing repositories: {e}")

    async def get_repository(
        self, organization: str, repository: str, project: Optional[str] = None
    ) -> Optional[Repository]:
        """Get specific BitBucket repository.

        Args:
            organization: Workspace slug
            repository: Repository slug
            project: Optional project key

        Returns:
            Repository object or None if not found

        Raises:
            RepositoryNotFoundError: If repository doesn't exist
            PermissionError: If access denied
        """
        if not await self.authenticate():
            raise AuthenticationError("Authentication required")

        await self._ensure_session()
        headers = self._get_auth_headers()
        url = f"{self.base_url}/repositories/{organization}/{repository}"

        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._convert_to_repository(data)
                elif response.status == 404:
                    raise RepositoryNotFoundError(
                        f"{organization}/{repository}", self.PROVIDER_NAME
                    )
                elif response.status == 403:
                    raise PermissionError(
                        f"Access denied to repository {organization}/{repository}",
                        self.PROVIDER_NAME,
                    )
                else:
                    text = await response.text()
                    raise APIError(
                        f"Failed to get repository: {response.status} - {text}",
                        self.PROVIDER_NAME,
                    )

        except aiohttp.ClientError as e:
            raise ConnectionError(f"Network error while getting repository: {e}")

    def get_authenticated_clone_url(self, repository: Repository) -> str:
        """Get authenticated clone URL.

        Args:
            repository: Repository object

        Returns:
            Clone URL with embedded authentication
        """
        from urllib.parse import quote

        if self.auth_method == "app_password":
            # Extract repository path from clone URL
            if repository.clone_url.startswith("https://bitbucket.org/"):
                repo_path = repository.clone_url.replace("https://bitbucket.org/", "")
                # URL encode credentials to handle special characters
                encoded_username = quote(self.username, safe="")
                encoded_password = quote(self.app_password, safe="")
                return f"https://{encoded_username}:{encoded_password}@bitbucket.org/{repo_path}"
        elif self.auth_method == "oauth":
            # For OAuth, we'll use the token as username with x-oauth-basic as password
            # This is a common pattern for OAuth tokens in git URLs
            if repository.clone_url.startswith("https://bitbucket.org/"):
                repo_path = repository.clone_url.replace("https://bitbucket.org/", "")
                encoded_token = quote(self.oauth_token, safe="")
                return (
                    f"https://{encoded_token}:x-oauth-basic@bitbucket.org/{repo_path}"
                )

        # Fallback to original URL if we can't authenticate it
        return repository.clone_url

    def supports_projects(self) -> bool:
        """BitBucket supports project hierarchy.

        Returns:
            bool: True
        """
        return True

    def get_rate_limit_info(self) -> Optional[Dict[str, Any]]:
        """Get BitBucket API rate limit information.

        Returns:
            Dict with rate limit info or None

        Note: BitBucket uses hourly rate limits per IP/user
        """
        # TODO: Implement rate limit check
        # - BitBucket doesn't have a dedicated rate limit endpoint
        # - Check response headers for rate limit info:
        #   - X-RateLimit-Limit
        #   - X-RateLimit-Remaining
        #   - X-RateLimit-Reset
        # - Cache and return last known values
        raise NotImplementedError("BitBucket rate limit info not yet implemented")

    @classmethod
    def match_url(cls, url: str) -> bool:
        """Check if URL is a BitBucket URL.

        Args:
            url: URL to check

        Returns:
            bool: True if URL matches BitBucket patterns
        """
        for pattern in cls.BITBUCKET_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    async def close(self) -> None:
        """Cleanup BitBucket provider resources."""
        if self._session and not self._session.closed:
            await self._session.close()
        await super().close()

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on auth method."""
        headers = {"Accept": "application/json"}

        if self.auth_method == "app_password":
            # Basic authentication with username:app_password
            credentials = f"{self.username}:{self.app_password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_credentials}"
        elif self.auth_method == "oauth":
            headers["Authorization"] = f"Bearer {self.oauth_token}"

        return headers

    def _convert_to_repository(self, repo_data: Dict[str, Any]) -> Repository:
        """Convert BitBucket API repository data to Repository object."""
        # Extract clone URLs
        clone_url = ""
        ssh_url = None

        if "links" in repo_data and "clone" in repo_data["links"]:
            for link in repo_data["links"]["clone"]:
                if link["name"] == "https":
                    clone_url = link["href"]
                elif link["name"] == "ssh":
                    ssh_url = link["href"]

        # Default branch
        default_branch = "main"
        if "mainbranch" in repo_data and repo_data["mainbranch"]:
            default_branch = repo_data["mainbranch"].get("name", "main")

        return Repository(
            name=repo_data["name"],
            clone_url=clone_url,
            ssh_url=ssh_url,
            is_disabled=False,  # BitBucket doesn't have disabled repos
            is_private=repo_data.get("is_private", True),
            default_branch=default_branch,
            size=repo_data.get("size", 0),  # Size in bytes, convert to KB
            description=repo_data.get("description"),
            created_at=repo_data.get("created_on"),
            updated_at=repo_data.get("updated_on"),
            provider=self.PROVIDER_NAME,
            metadata={
                "full_name": repo_data.get("full_name"),
                "uuid": repo_data.get("uuid"),
                "scm": repo_data.get("scm", "git"),
                "has_issues": repo_data.get("has_issues", False),
                "has_wiki": repo_data.get("has_wiki", False),
                "fork_policy": repo_data.get("fork_policy"),
                "language": repo_data.get("language"),
            },
        )

    # BitBucket-specific helper methods

    async def get_workspace_permissions(self, workspace: str) -> Dict[str, Any]:
        """Get current user's permissions for a workspace.

        Args:
            workspace: Workspace slug

        Returns:
            Dict with permission details
        """
        # TODO: Implement workspace permissions check
        # - GET /workspaces/{workspace}/permissions
        # - Parse permission levels
        # - Useful for determining available operations
        raise NotImplementedError("BitBucket workspace permissions not yet implemented")

    async def list_repository_branches(
        self, organization: str, repository: str
    ) -> List[Dict[str, Any]]:
        """List branches in a repository.

        Args:
            organization: Workspace slug
            repository: Repository slug

        Returns:
            List of branch information
        """
        # TODO: Implement branch listing
        # - GET /repositories/{workspace}/{repo_slug}/refs/branches
        # - Include branch name, target commit, etc.
        # - Useful for determining default branch
        raise NotImplementedError("BitBucket branch listing not yet implemented")

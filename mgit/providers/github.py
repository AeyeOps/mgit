"""GitHub provider implementation.

This module provides the GitHub provider for mgit, supporting repository
operations through the GitHub API.
"""

import asyncio
import re
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

import aiohttp

from ..security.credentials import mask_sensitive_data, validate_github_pat

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
    RateLimitError,
    RepositoryNotFoundError,
)

logger = SecurityLogger(__name__)


class GitHubProvider(GitProvider):
    """GitHub provider implementation.

    Supports:
    - Personal Access Token (PAT) authentication
    - OAuth (future implementation)
    - Repository listing and cloning
    - Organization management

    Note: GitHub does not have a project hierarchy like Azure DevOps,
    so project-related methods return empty results.
    """

    PROVIDER_NAME = "github"
    SUPPORTED_AUTH_METHODS = [AuthMethod.PAT, AuthMethod.OAUTH]
    DEFAULT_API_VERSION = "2022-11-28"  # GitHub API version

    # GitHub URL patterns
    GITHUB_PATTERNS = [
        r"https?://github\.com",
        r"git@github\.com",
        r"ssh://git@github\.com",
    ]

    def __init__(self, config: Dict[str, Any]):
        """Initialize GitHub provider.

        Args:
            config: Configuration dictionary with unified fields:
                - url: GitHub API base URL (e.g., https://api.github.com)
                - user: GitHub username
                - token: Personal access token or OAuth token
                - workspace: Optional workspace/organization name
        """
        # Security components
        self._validator = SecurityValidator()
        self._monitor = get_security_monitor()

        # Set attributes before calling super().__init__ which calls _validate_config
        # Fail-fast: require unified fields to be present
        if "token" not in config:
            raise ValueError("Missing required field: token")
            
        self.url = config.get("url", "https://api.github.com")
        self.user = config.get("user", "")
        self.token = config["token"]
        self.workspace = config.get("workspace", "")
        self.api_version = config.get("api_version", self.DEFAULT_API_VERSION)

        # HTTP session for API calls
        self._session: Optional[aiohttp.ClientSession] = None
        self._headers: Dict[str, str] = {}
        self._rate_limit_info: Optional[Dict[str, Any]] = None

        super().__init__(config)

    def _validate_config(self) -> None:
        """Validate GitHub-specific configuration.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not self.url:
            raise ConfigurationError("GitHub URL is required", self.PROVIDER_NAME)

        # Validate URL format and security
        if not self._validator.validate_url(self.url):
            raise ConfigurationError(
                f"Invalid or insecure URL: {mask_sensitive_data(self.url)}",
                self.PROVIDER_NAME,
            )

        if not self.token:
            raise ConfigurationError(
                "GitHub token is required", self.PROVIDER_NAME
            )
            
        # Validate token format
        if not validate_github_pat(self.token):
            self._monitor.log_validation_failure(
                "github_token", mask_sensitive_data(self.token), "Invalid token format"
            )
            raise ConfigurationError(
                "Invalid GitHub token format", self.PROVIDER_NAME
            )

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
            logger.debug(f"Session creation error: {e}")
            self._session = aiohttp.ClientSession()

    async def authenticate(self) -> bool:
        """Authenticate with GitHub.

        Returns:
            bool: True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        if self._authenticated:
            return True

        organization = self.url  # Use URL as organization identifier

        try:
            await self._ensure_session()

            # Set up authentication headers
            self._headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": self.api_version,
                "User-Agent": "mgit-client/1.0",
            }

            # Test authentication with /user endpoint
            url = f"{self.url}/user"
            async with self._session.get(url, headers=self._headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    username = user_data.get("login", "unknown")
                    logger.debug(
                        "GitHub authentication successful for user: %s", username
                    )

                    # Log successful authentication
                    self._monitor.log_authentication_attempt(
                        provider=self.PROVIDER_NAME,
                        organization=organization,
                        success=True,
                        details={"username": username},
                    )

                    self._authenticated = True
                    return True
                elif response.status == 401:
                    error_data = await response.json()
                    message = error_data.get("message", "Invalid credentials")

                    # Log failed authentication
                    self._monitor.log_authentication_attempt(
                        provider=self.PROVIDER_NAME,
                        organization=organization,
                        success=False,
                        details={"error": "invalid_credentials", "status": 401},
                    )

                    logger.error("GitHub authentication failed: Invalid credentials")
                    raise AuthenticationError(
                        f"GitHub authentication failed: {message}", self.PROVIDER_NAME
                    )
                elif response.status == 403:
                    error_data = await response.json()
                    message = error_data.get("message", "Access forbidden")

                    # Log failed authentication
                    self._monitor.log_authentication_attempt(
                        provider=self.PROVIDER_NAME,
                        organization=organization,
                        success=False,
                        details={"error": "access_forbidden", "status": 403},
                    )

                    logger.error("GitHub authentication failed: Access forbidden")
                    raise AuthenticationError(
                        f"GitHub authentication failed: {message}", self.PROVIDER_NAME
                    )
                else:
                    # Log failed authentication
                    self._monitor.log_authentication_attempt(
                        provider=self.PROVIDER_NAME,
                        organization=organization,
                        success=False,
                        details={
                            "error": "unexpected_status",
                            "status": response.status,
                        },
                    )

                    logger.error(
                        "GitHub authentication failed with status %d", response.status
                    )
                    raise AuthenticationError(
                        f"GitHub authentication failed with status {response.status}",
                        self.PROVIDER_NAME,
                    )

        except aiohttp.ClientError as e:
            # Log connection error
            self._monitor.log_authentication_attempt(
                provider=self.PROVIDER_NAME,
                organization=organization,
                success=False,
                details={"error": "connection_error", "exception": str(e)},
            )

            logger.error("GitHub authentication failed due to connection error")
            raise ConnectionError(
                f"Failed to connect to GitHub: {e}", self.PROVIDER_NAME
            )
        except Exception as e:
            # Log unexpected error
            self._monitor.log_authentication_attempt(
                provider=self.PROVIDER_NAME,
                organization=organization,
                success=False,
                details={"error": "unexpected_error", "exception": str(e)},
            )

            logger.error("Unexpected error during GitHub authentication")
            raise AuthenticationError(
                f"GitHub authentication failed: {e}", self.PROVIDER_NAME
            )

    async def test_connection(self) -> bool:
        """Test GitHub API connection.

        Returns:
            bool: True if connection is valid

        Raises:
            ConnectionError: If connection fails
        """
        try:
            if not self._authenticated:
                result = await self.authenticate()
                if not result:
                    return False

            if not self._session:
                return False

            # Test connection with rate_limit endpoint (doesn't require auth)
            url = f"{self.url}/rate_limit"
            async with self._session.get(url, headers=self._headers) as response:
                if response.status == 200:
                    rate_limit_data = await response.json()
                    self._rate_limit_info = rate_limit_data.get("rate", {})
                    logger.debug("GitHub connection test successful")
                    return True
                else:
                    logger.error(
                        "GitHub connection test failed with status %d", response.status
                    )
                    return False

        except aiohttp.ClientError as e:
            logger.error("GitHub connection test failed: %s", e)
            raise ConnectionError(
                f"Failed to connect to GitHub: {e}", self.PROVIDER_NAME
            )
        except Exception as e:
            logger.error("Unexpected error during GitHub connection test: %s", e)
            return False
        # Don't cleanup here - the session will be reused for subsequent operations

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None
            self._authenticated = False

    async def list_organizations(self) -> List[Organization]:
        """List accessible GitHub organizations.

        Returns:
            List of Organization objects

        Raises:
            APIError: If API call fails
        """
        if not await self.authenticate():
            return []

        organizations = []

        try:
            # Get user's organizations
            url = f"{self.url}/user/orgs"
            async with self._session.get(url, headers=self._headers) as response:
                if response.status == 200:
                    orgs_data = await response.json()
                    for org in orgs_data:
                        organizations.append(
                            Organization(
                                name=org["login"],
                                url=org["url"],
                                provider=self.PROVIDER_NAME,
                                metadata={
                                    "id": org["id"],
                                    "description": org.get("description"),
                                    "public_repos": org.get("public_repos"),
                                    "followers": org.get("followers"),
                                    "html_url": org.get("html_url"),
                                },
                            )
                        )
                elif response.status == 403:
                    logger.warning("No permission to list organizations")
                else:
                    logger.error(
                        "Failed to list organizations: status %d", response.status
                    )

            # Get user info to include personal namespace
            url = f"{self.url}/user"
            async with self._session.get(url, headers=self._headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    organizations.append(
                        Organization(
                            name=user_data["login"],
                            url=user_data["url"],
                            provider=self.PROVIDER_NAME,
                            metadata={
                                "id": user_data["id"],
                                "type": "User",
                                "name": user_data.get("name"),
                                "public_repos": user_data.get("public_repos"),
                                "followers": user_data.get("followers"),
                                "html_url": user_data.get("html_url"),
                            },
                        )
                    )

            logger.debug("Found %d GitHub organizations", len(organizations))
            return organizations

        except Exception as e:
            logger.error("Error listing GitHub organizations: %s", e)
            raise APIError(f"Failed to list organizations: {e}", self.PROVIDER_NAME)

    async def list_projects(self, organization: str) -> List[Project]:
        """List projects in organization.

        Note: GitHub doesn't have projects in the same sense as Azure DevOps.
        This method returns an empty list for GitHub.

        Args:
            organization: Organization/username

        Returns:
            Empty list (GitHub has no project hierarchy)
        """
        # GitHub doesn't have a project layer between org and repo
        return []

    async def list_repositories(
        self,
        organization: str,
        project: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Repository]:
        """List GitHub repositories.

        Args:
            organization: Organization name or username
            project: Ignored for GitHub
            filters: Optional filters:
                - language: Filter by primary language
                - archived: Include/exclude archived repos
                - visibility: public, private, or all
                - type: all, owner, member

        Yields:
            Repository objects

        Raises:
            APIError: If API call fails
            RateLimitError: If rate limit exceeded
        """
        if not await self.authenticate():
            return

        await self._ensure_session()
        try:
            # Build URL and query parameters
            url = f"{self.url}/orgs/{organization}/repos"
            params = {"per_page": 100, "page": 1}

            # Apply filters
            if filters:
                if "type" in filters:
                    params["type"] = filters["type"]
                if "visibility" in filters:
                    params["visibility"] = filters["visibility"]

            # Paginate through all repositories
            while True:
                async with self._session.get(
                    url, headers=self._headers, params=params
                ) as response:
                    await self._check_rate_limit(response)

                    if response.status == 200:
                        repos_data = await response.json()

                        if not repos_data:  # Empty page means we're done
                            break

                        for repo in repos_data:
                            # Apply additional filters
                            if filters:
                                if (
                                    "language" in filters
                                    and repo.get("language") != filters["language"]
                                ):
                                    continue
                                if "archived" in filters:
                                    if filters["archived"] is False and repo.get(
                                        "archived", False
                                    ):
                                        continue
                                    elif filters["archived"] is True and not repo.get(
                                        "archived", False
                                    ):
                                        continue

                            repository = self._convert_repo_data(repo)
                            yield repository

                        # Prepare for next page
                        params["page"] += 1

                        # Check if there are more pages using Link header
                        link_header = response.headers.get("Link", "")
                        if 'rel="next"' not in link_header:
                            break

                    elif response.status == 404:
                        # Try user repos endpoint instead
                        if "/orgs/" in url:
                            url = f"{self.url}/users/{organization}/repos"
                            continue
                        else:
                            logger.error(
                                "Organization/user '%s' not found", organization
                            )
                            break
                    elif response.status == 403:
                        error_data = await response.json()
                        if "rate limit" in error_data.get("message", "").lower():
                            raise RateLimitError(
                                "GitHub API rate limit exceeded", self.PROVIDER_NAME
                            )
                        else:
                            logger.error(
                                "Access denied to organization '%s'", organization
                            )
                            break
                    else:
                        error_text = await response.text()
                        logger.error(
                            "Failed to list repositories: status %d, response: %s",
                            response.status,
                            error_text,
                        )
                        raise APIError(
                            f"Failed to list repositories: status {response.status}",
                            self.PROVIDER_NAME,
                            response.status,
                        )

        except RateLimitError:
            raise
        except Exception as e:
            logger.error("Error listing GitHub repositories: %s", e)
            raise APIError(f"Failed to list repositories: {e}", self.PROVIDER_NAME)

    async def get_repository(
        self, organization: str, repository: str, project: Optional[str] = None
    ) -> Optional[Repository]:
        """Get specific GitHub repository.

        Args:
            organization: Organization name or username
            repository: Repository name
            project: Ignored for GitHub

        Returns:
            Repository object or None if not found

        Raises:
            RepositoryNotFoundError: If repository doesn't exist
            PermissionError: If access denied
        """
        if not await self.authenticate():
            return None

        try:
            url = f"{self.url}/repos/{organization}/{repository}"
            async with self._session.get(url, headers=self._headers) as response:
                await self._check_rate_limit(response)

                if response.status == 200:
                    repo_data = await response.json()
                    return self._convert_repo_data(repo_data)
                elif response.status == 404:
                    logger.debug(
                        "Repository '%s/%s' not found", organization, repository
                    )
                    raise RepositoryNotFoundError(
                        f"{organization}/{repository}", self.PROVIDER_NAME
                    )
                elif response.status == 403:
                    error_data = await response.json()
                    message = error_data.get("message", "Access denied")
                    logger.error(
                        "Access denied to repository '%s/%s': %s",
                        organization,
                        repository,
                        message,
                    )
                    raise PermissionError(
                        f"Access denied to repository {organization}/{repository}: {message}",
                        self.PROVIDER_NAME,
                        f"{organization}/{repository}",
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        "Failed to get repository: status %d, response: %s",
                        response.status,
                        error_text,
                    )
                    raise APIError(
                        f"Failed to get repository: status {response.status}",
                        self.PROVIDER_NAME,
                        response.status,
                    )

        except (RepositoryNotFoundError, PermissionError):
            raise
        except Exception as e:
            logger.error("Error getting GitHub repository: %s", e)
            raise APIError(f"Failed to get repository: {e}", self.PROVIDER_NAME)

        return None

    def get_authenticated_clone_url(self, repository: Repository) -> str:
        """Get authenticated clone URL.

        Args:
            repository: Repository object

        Returns:
            Clone URL with embedded authentication
        """
        clone_url = repository.clone_url

        # Convert HTTPS URL to authenticated format
        if clone_url.startswith("https://github.com/"):
            # Format: https://{token}@github.com/{owner}/{repo}.git
            return clone_url.replace(
                "https://github.com/", f"https://{self.token}@github.com/"
            )

        # If not HTTPS or already authenticated, return as-is
        return clone_url

    def supports_projects(self) -> bool:
        """GitHub doesn't support project hierarchy.

        Returns:
            bool: False
        """
        return False

    def get_rate_limit_info(self) -> Optional[Dict[str, Any]]:
        """Get GitHub API rate limit information.

        Returns:
            Dict with rate limit info:
                - limit: Rate limit maximum
                - remaining: Calls remaining
                - reset: Reset timestamp
                - used: Calls used
        """
        if self._rate_limit_info:
            return {
                "limit": self._rate_limit_info.get("limit", 0),
                "remaining": self._rate_limit_info.get("remaining", 0),
                "reset": self._rate_limit_info.get("reset", 0),
                "used": self._rate_limit_info.get("used", 0),
            }
        return None

    @classmethod
    def match_url(cls, url: str) -> bool:
        """Check if URL is a GitHub URL.

        Args:
            url: URL to check

        Returns:
            bool: True if URL matches GitHub patterns
        """
        for pattern in cls.GITHUB_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    async def _check_rate_limit(self, response: aiohttp.ClientResponse) -> None:
        """Check response for rate limit headers and update info.

        Args:
            response: HTTP response object

        Raises:
            RateLimitError: If rate limit exceeded
        """
        # Update rate limit info from headers
        if "X-RateLimit-Limit" in response.headers:
            self._rate_limit_info = {
                "limit": int(response.headers.get("X-RateLimit-Limit", 0)),
                "remaining": int(response.headers.get("X-RateLimit-Remaining", 0)),
                "reset": int(response.headers.get("X-RateLimit-Reset", 0)),
                "used": int(response.headers.get("X-RateLimit-Used", 0)),
            }

        # Check if rate limit exceeded
        if response.status == 403:
            error_data = await response.json()
            if "rate limit" in error_data.get("message", "").lower():
                reset_time = None
                if self._rate_limit_info and self._rate_limit_info.get("reset"):
                    reset_time = datetime.fromtimestamp(self._rate_limit_info["reset"])
                raise RateLimitError(
                    "GitHub API rate limit exceeded", self.PROVIDER_NAME, reset_time
                )

    def _convert_repo_data(self, repo_data: Dict[str, Any]) -> Repository:
        """Convert GitHub repository data to Repository object.

        Args:
            repo_data: GitHub API repository response

        Returns:
            Repository object
        """
        return Repository(
            name=repo_data["name"],
            clone_url=repo_data["clone_url"],
            ssh_url=repo_data.get("ssh_url"),
            is_disabled=repo_data.get("disabled", False),
            is_private=repo_data.get("private", False),
            default_branch=repo_data.get("default_branch", "main"),
            size=repo_data.get("size"),  # GitHub returns size in KB
            description=repo_data.get("description"),
            created_at=repo_data.get("created_at"),
            updated_at=repo_data.get("updated_at"),
            provider=self.PROVIDER_NAME,
            metadata={
                "id": repo_data["id"],
                "full_name": repo_data["full_name"],
                "html_url": repo_data["html_url"],
                "git_url": repo_data.get("git_url"),
                "language": repo_data.get("language"),
                "forks_count": repo_data.get("forks_count", 0),
                "stargazers_count": repo_data.get("stargazers_count", 0),
                "watchers_count": repo_data.get("watchers_count", 0),
                "open_issues_count": repo_data.get("open_issues_count", 0),
                "archived": repo_data.get("archived", False),
                "disabled": repo_data.get("disabled", False),
                "fork": repo_data.get("fork", False),
                "license": (
                    repo_data.get("license", {}).get("name")
                    if repo_data.get("license")
                    else None
                ),
                "topics": repo_data.get("topics", []),
                "visibility": repo_data.get(
                    "visibility", "private" if repo_data.get("private") else "public"
                ),
            },
        )

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "GitHubProvider":
        """Create GitHub provider from configuration.

        Args:
            config: Configuration dictionary

        Returns:
            GitHubProvider instance
        """
        # Map config to unified format
        github_config = {
            "url": config.get("url", "https://api.github.com"),
            "user": config.get("user", ""),
            "token": config.get("token", config.get("GITHUB_TOKEN", "")),
            "workspace": config.get("workspace", ""),
            "api_version": config.get("api_version", cls.DEFAULT_API_VERSION),
        }

        return cls(github_config)

    async def close(self) -> None:
        """Cleanup GitHub provider resources."""
        if self._session:
            await self._session.close()
            self._session = None

        # Clear sensitive data
        self._headers = {}
        self._rate_limit_info = None
        self._authenticated = False

        await super().close()

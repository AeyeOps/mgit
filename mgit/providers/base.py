"""Base abstract class for git providers.

This module defines the abstract base class and common data structures
that all git providers must implement. The GitProvider class serves as the
foundation for all provider-specific implementations (GitHub, GitLab, Azure DevOps, etc.)

Key Concepts:
- Repository: A git repository hosted on a provider
- Organization: A top-level grouping (GitHub org, Azure DevOps org, etc.)
- Project: An optional intermediate grouping (not all providers support this)
- Authentication: Various methods to authenticate with providers

Usage:
    To implement a new provider, subclass GitProvider and implement all abstract methods.
    See existing providers (github.py, azdevops.py, etc.) for examples.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional
import asyncio
import time


# Common data structures
@dataclass
class Repository:
    """Provider-agnostic repository representation."""

    name: str
    clone_url: str
    ssh_url: Optional[str] = None
    is_disabled: bool = False
    is_private: bool = True
    default_branch: str = "main"
    size: Optional[int] = None  # Size in KB
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    provider: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)  # Provider-specific data


@dataclass
class Organization:
    """Provider-agnostic organization/workspace representation."""

    name: str
    url: str
    provider: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Project:
    """Project/grouping representation (may be None for GitHub)."""

    name: str
    organization: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuthMethod(Enum):
    """Supported authentication methods."""

    PAT = "personal_access_token"
    OAUTH = "oauth"
    APP_PASSWORD = "app_password"
    SSH_KEY = "ssh_key"


class GitProvider(ABC):
    """Abstract base class for all git providers.

    This class defines the interface that all git provider implementations must follow.
    It provides both abstract methods that must be implemented and concrete utility
    methods that can be optionally overridden.

    Attributes:
        PROVIDER_NAME: Unique identifier for the provider (e.g., 'github', 'gitlab')
        SUPPORTED_AUTH_METHODS: List of authentication methods this provider supports
        DEFAULT_API_VERSION: Default API version to use for this provider
        config: Provider-specific configuration dictionary
        _client: Internal client instance for API communication
        _authenticated: Boolean flag indicating authentication status
    """

    # Class attributes to be overridden by subclasses
    PROVIDER_NAME: str = ""
    SUPPORTED_AUTH_METHODS: List[AuthMethod] = []
    DEFAULT_API_VERSION: str = ""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize provider with configuration.

        Args:
            config: Provider-specific configuration dictionary. Common keys include:
                - base_url: API base URL (optional for cloud providers)
                - auth_method: Authentication method to use
                - credentials: Authentication credentials (PAT, OAuth token, etc.)
                - api_version: API version to use (optional)
                - timeout: Request timeout in seconds (optional)
                - proxy: Proxy configuration (optional)

        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        self.config: Dict[str, Any] = config
        self._validate_config()
        self._client: Optional[Any] = None
        self._authenticated: bool = False

        # Rate limiter configuration
        self._rate_limiter_config = self._get_rate_limiter_config()
        self._rate_limit_info: Optional[Dict[str, Any]] = None

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider-specific configuration.

        This method should check that all required configuration values are present
        and valid for the specific provider. It should validate:
        - Required fields are present
        - Values are of correct type
        - URLs are properly formatted
        - Auth method is supported

        Raises:
            ConfigurationError: If configuration is invalid or missing required fields
            ValueError: If configuration values are of incorrect type
        """
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the provider.

        This method should establish authentication with the provider using the
        configured authentication method. It should:
        - Create and configure the API client
        - Validate credentials
        - Set up any required headers or authentication tokens
        - Store authentication state

        Returns:
            bool: True if authentication successful, False otherwise

        Raises:
            AuthenticationError: If authentication fails due to invalid credentials
            ConnectionError: If unable to connect to the provider
            ConfigurationError: If configuration is invalid
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the connection and authentication are valid.

        This method should perform a simple API call to verify:
        - Network connectivity to the provider
        - Authentication credentials are valid
        - User has basic read permissions

        Returns:
            bool: True if connection is valid and authenticated

        Raises:
            AuthenticationError: If authentication is invalid
            ConnectionError: If unable to connect to the provider
            PermissionError: If user lacks required permissions
        """
        pass

    @abstractmethod
    async def list_organizations(self) -> List[Organization]:
        """List all accessible organizations/workspaces.

        This method should return all organizations that the authenticated user
        has access to. The definition of 'organization' varies by provider:
        - GitHub: Organizations the user belongs to
        - Azure DevOps: Organizations (top-level)
        - GitLab: Groups (top-level)
        - Bitbucket: Workspaces

        Returns:
            List[Organization]: List of accessible organizations

        Raises:
            AuthenticationError: If not authenticated
            APIError: If the API request fails
            RateLimitError: If rate limited by the provider
        """
        pass

    @abstractmethod
    async def list_projects(self, organization: str) -> List[Project]:
        """List all projects in an organization.

        Projects are an optional hierarchical level between organizations and
        repositories. Not all providers support this concept:
        - Azure DevOps: Has projects
        - GitHub: No projects (returns empty list)
        - GitLab: Has subgroups (treated as projects)
        - Bitbucket: Has projects

        Args:
            organization: Organization/workspace name

        Returns:
            List[Project]: List of projects in the organization, or empty list
                         if provider doesn't support projects

        Raises:
            AuthenticationError: If not authenticated
            PermissionError: If user lacks access to the organization
            APIError: If the API request fails
        """
        pass

    @abstractmethod
    async def list_repositories(
        self,
        organization: str,
        project: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Repository]:
        """List repositories with optional filtering.

        This method should yield repositories as they are fetched, allowing for
        efficient handling of large numbers of repositories. It should handle
        pagination automatically.

        Args:
            organization: Organization/workspace name
            project: Optional project name (ignored if provider doesn't support projects)
            filters: Optional filters dictionary. Common filters include:
                - archived: bool - Include/exclude archived repositories
                - language: str - Filter by primary programming language
                - visibility: str - 'public', 'private', or 'all'
                - name_pattern: str - Regex pattern for repository names
                - updated_after: datetime - Only repos updated after this date
                - size_max_kb: int - Maximum repository size in KB

        Yields:
            Repository: Repository objects matching the criteria

        Raises:
            AuthenticationError: If not authenticated
            PermissionError: If user lacks access to the organization/project
            APIError: If the API request fails
            RateLimitError: If rate limited by the provider
        """
        pass

    @abstractmethod
    async def get_repository(
        self, organization: str, repository: str, project: Optional[str] = None
    ) -> Optional[Repository]:
        """Get a specific repository.

        This method should fetch detailed information about a single repository.

        Args:
            organization: Organization/workspace name
            repository: Repository name (without organization prefix)
            project: Optional project name (ignored if provider doesn't support projects)

        Returns:
            Optional[Repository]: Repository object if found, None if not found

        Raises:
            AuthenticationError: If not authenticated
            PermissionError: If user lacks access to the repository
            APIError: If the API request fails
            RepositoryNotFoundError: If the repository doesn't exist
        """
        pass

    @abstractmethod
    def get_authenticated_clone_url(self, repository: Repository) -> str:
        """Get clone URL with embedded authentication.

        This method should return a URL that can be used to clone the repository
        without requiring additional authentication. The method of embedding
        credentials varies by provider and authentication method:
        - PAT: Usually embedded as username:token@host
        - OAuth: May use bearer token in URL or require git credential helper
        - SSH: Returns SSH URL (assumes SSH key is configured)

        Args:
            repository: Repository object containing clone URLs

        Returns:
            str: Authenticated clone URL ready for git clone operation

        Raises:
            ConfigurationError: If authentication method doesn't support URL embedding
            ValueError: If repository object is missing required URL fields
        """
        pass

    # Common utility methods (not abstract)
    async def count_repositories(
        self,
        organization: str,
        project: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Count total repositories matching criteria.

        This is a utility method that counts repositories by iterating through
        list_repositories. Providers may override this with more efficient
        implementations if their API supports direct counting.

        Args:
            organization: Organization/workspace name
            project: Optional project name
            filters: Optional filters to apply

        Returns:
            int: Total number of repositories matching criteria

        Raises:
            Same exceptions as list_repositories
        """
        count = 0
        async for _ in self.list_repositories(organization, project, filters):
            count += 1
        return count

    def supports_projects(self) -> bool:
        """Check if provider supports project hierarchy.

        This method indicates whether the provider has a project level between
        organizations and repositories. Providers should override this to return
        False if they don't support projects (e.g., GitHub).

        Returns:
            bool: True if provider supports projects, False otherwise
        """
        return True  # Override in providers that don't

    def get_rate_limit_info(self) -> Optional[Dict[str, Any]]:
        """Get current rate limit information if available.

        Providers that implement rate limiting should override this method to
        return current rate limit status. This helps users understand their
        API usage and plan accordingly.

        Returns:
            Optional[Dict[str, Any]]: Rate limit information or None if not applicable.
                                    Common keys include:
                                    - limit: Maximum requests allowed
                                    - remaining: Requests remaining
                                    - reset: Timestamp when limit resets
                                    - used: Requests used in current window
        """
        return None  # Override in providers with rate limits

    async def close(self) -> None:
        """Cleanup provider resources.

        This method should be called when done with the provider to ensure
        proper cleanup of resources such as:
        - HTTP client sessions
        - Open connections
        - Temporary credentials
        - Any cached data

        Providers should override this if they need specific cleanup logic.
        """
        if self._client:
            # Close client connections if needed
            pass

    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information and capabilities.

        This method returns information about the provider instance,
        including its capabilities, limitations, and current configuration.
        Providers may override this to provide more detailed information.

        Returns:
            Dict[str, Any]: Provider information including:
                - name: Provider name
                - version: API version being used
                - capabilities: List of supported features
                - limitations: Known limitations or restrictions
                - authenticated: Current authentication status
                - base_url: API base URL (if applicable)
        """
        return {
            "name": self.PROVIDER_NAME,
            "version": self.DEFAULT_API_VERSION,
            "capabilities": [
                "repositories",
                "organizations",
                "authentication",
            ],
            "limitations": [],
            "authenticated": self._authenticated,
            "base_url": self.config.get("base_url", "N/A"),
            "supports_projects": self.supports_projects(),
        }

    async def validate_repository_access(
        self,
        organization: str,
        repository: str,
        project: Optional[str] = None,
        required_permissions: Optional[List[str]] = None,
    ) -> bool:
        """Validate user has required access to a repository.

        This method checks if the authenticated user has the necessary
        permissions to perform operations on a repository. Providers may
        override this with more efficient implementations.

        Args:
            organization: Organization/workspace name
            repository: Repository name
            project: Optional project name
            required_permissions: List of required permissions (provider-specific)
                                e.g., ['read', 'write', 'admin']

        Returns:
            bool: True if user has required access, False otherwise

        Raises:
            AuthenticationError: If not authenticated
            APIError: If the API request fails
        """
        try:
            repo = await self.get_repository(organization, repository, project)
            return repo is not None
        except (PermissionError, RepositoryNotFoundError):
            return False

    def _get_rate_limiter_config(self) -> Dict[str, Any]:
        """Get rate limiter configuration with defaults.

        Configuration options:
        - max_wait_seconds: Maximum time to wait for rate limit reset (default: 300)
        - exponential_rate: Base multiplier for exponential backoff (default: 2.0)
        - backoff_max_seconds: Maximum backoff delay (default: 60.0)
        """
        # Import here to avoid circular imports
        from ..config.yaml_manager import get_global_config

        global_config = get_global_config()
        rate_limiter_config = global_config.get("rate_limiter", {})

        return {
            "max_wait_seconds": rate_limiter_config.get("max_wait_seconds", 300),
            "exponential_rate": rate_limiter_config.get("exponential_rate", 2.0),
            "backoff_max_seconds": rate_limiter_config.get("backoff_max_seconds", 60.0),
        }

    async def _wait_for_rate_limit(self) -> None:
        """Wait if we're close to rate limit or if rate limited.

        This method implements intelligent rate limit handling:
        - Checks remaining requests against buffer
        - Calculates wait time based on reset timestamp
        - Uses exponential backoff with configurable multiplier
        - Always active (rate limiting is mandatory for API stability)
        """
        if not self._rate_limit_info:
            return

        remaining = self._rate_limit_info.get("remaining", 0)
        reset_time = self._rate_limit_info.get("reset", 0)

        # Check if we need to wait (when 1 or fewer requests remaining)
        if remaining <= 1:
            now = int(time.time())
            if reset_time > now:
                wait_seconds = reset_time - now + 1  # Add 1 second buffer

                # Respect max wait time
                max_wait = self._rate_limiter_config["max_wait_seconds"]
                if wait_seconds > max_wait:
                    raise Exception(f"Rate limit wait time ({wait_seconds}s) exceeds maximum ({max_wait}s)")

                # Use exponential backoff with configurable multiplier
                multiplier = self._rate_limiter_config["exponential_rate"]
                max_backoff = self._rate_limiter_config["backoff_max_seconds"]
                retry_count = self._retry_count()
                exponential_wait = 1.0 * (multiplier ** retry_count)  # Start at 1s, multiply by rate each retry
                wait_seconds = min(exponential_wait, max_backoff)

                # Add jitter to prevent thundering herd (0.1-1.0 seconds)
                import random
                jitter = random.uniform(0.1, 1.0)
                wait_seconds += jitter

                print(f"Rate limit: waiting {wait_seconds:.1f}s until reset")
                await asyncio.sleep(wait_seconds)

                # Reset rate limit info after waiting
                self._rate_limit_info = None

    def _retry_count(self) -> int:
        """Get current retry count for exponential backoff."""
        return getattr(self, '_retry_count_attr', 0)

    def _increment_retry_count(self) -> None:
        """Increment retry count for exponential backoff."""
        if not hasattr(self, '_retry_count_attr'):
            self._retry_count_attr = 0
        self._retry_count_attr += 1

    def _reset_retry_count(self) -> None:
        """Reset retry count after successful operation."""
        self._retry_count_attr = 0

    async def _check_rate_limit(self, response) -> None:
        """Check response for rate limit headers and update info.

        This is a generic implementation that can be overridden by providers
        that use different header formats.

        Args:
            response: HTTP response object with headers
        """
        # Default implementation - providers can override for their specific headers
        headers = getattr(response, 'headers', {})

        # Common rate limit headers across providers
        rate_limit_headers = {
            "limit": headers.get("X-RateLimit-Limit") or headers.get("X-Rate-Limit-Limit"),
            "remaining": headers.get("X-RateLimit-Remaining") or headers.get("X-Rate-Limit-Remaining"),
            "reset": headers.get("X-RateLimit-Reset") or headers.get("X-Rate-Limit-Reset"),
        }

        # Only update if we have at least one header
        if any(rate_limit_headers.values()):
            self._rate_limit_info = {
                "limit": int(rate_limit_headers["limit"] or 0),
                "remaining": int(rate_limit_headers["remaining"] or 0),
                "reset": int(rate_limit_headers["reset"] or 0),
            }

    async def _make_rate_limited_request(self, request_func, *args, **kwargs):
        """Make a request with automatic rate limit handling.

        Args:
            request_func: Async function that makes the HTTP request
            *args, **kwargs: Arguments to pass to request_func

        Returns:
            Response from the request function
        """
        # Wait if we're approaching rate limits
        await self._wait_for_rate_limit()

        # Make the request
        response = await request_func(*args, **kwargs)

        # Check and update rate limit info
        await self._check_rate_limit(response)

        # Reset retry count on successful response
        if hasattr(response, 'status') and 200 <= response.status < 300:
            self._reset_retry_count()
        else:
            self._increment_retry_count()

        return response

"""Base abstract class for git providers.

This module defines the abstract base class and common data structures
that all git providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, AsyncIterator
from enum import Enum
import asyncio


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
    """Abstract base class for all git providers."""
    
    # Class attributes to be overridden
    PROVIDER_NAME: str = ""
    SUPPORTED_AUTH_METHODS: List[AuthMethod] = []
    DEFAULT_API_VERSION: str = ""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize provider with configuration.
        
        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self._validate_config()
        self._client = None
        self._authenticated = False
        
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider-specific configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        pass
        
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the provider.
        
        Returns:
            bool: True if authentication successful
        """
        pass
        
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the connection and authentication are valid.
        
        Returns:
            bool: True if connection is valid
        """
        pass
        
    @abstractmethod
    async def list_organizations(self) -> List[Organization]:
        """List all accessible organizations/workspaces.
        
        Returns:
            List of Organization objects
        """
        pass
        
    @abstractmethod
    async def list_projects(self, organization: str) -> List[Project]:
        """List all projects in an organization.
        
        Note: May return empty list for providers without project concept
        
        Args:
            organization: Organization/workspace name
            
        Returns:
            List of Project objects
        """
        pass
        
    @abstractmethod
    async def list_repositories(
        self, 
        organization: str, 
        project: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Repository]:
        """List repositories with optional filtering.
        
        Args:
            organization: Organization/workspace name
            project: Optional project name
            filters: Optional filters (language, archived, etc.)
            
        Yields:
            Repository objects
        """
        pass
        
    @abstractmethod
    async def get_repository(
        self, 
        organization: str, 
        repository: str,
        project: Optional[str] = None
    ) -> Optional[Repository]:
        """Get a specific repository.
        
        Args:
            organization: Organization/workspace name
            repository: Repository name
            project: Optional project name
            
        Returns:
            Repository object or None if not found
        """
        pass
        
    @abstractmethod
    def get_authenticated_clone_url(self, repository: Repository) -> str:
        """Get clone URL with embedded authentication.
        
        Args:
            repository: Repository object
            
        Returns:
            Authenticated clone URL
        """
        pass
        
    # Common utility methods (not abstract)
    async def count_repositories(
        self, 
        organization: str, 
        project: Optional[str] = None
    ) -> int:
        """Count total repositories.
        
        Args:
            organization: Organization/workspace name
            project: Optional project name
            
        Returns:
            Total number of repositories
        """
        count = 0
        async for _ in self.list_repositories(organization, project):
            count += 1
        return count
        
    def supports_projects(self) -> bool:
        """Check if provider supports project hierarchy.
        
        Returns:
            bool: True if provider supports projects
        """
        return True  # Override in providers that don't
        
    def get_rate_limit_info(self) -> Optional[Dict[str, Any]]:
        """Get current rate limit information if available.
        
        Returns:
            Dict with rate limit info or None if not applicable
        """
        return None  # Override in providers with rate limits
        
    async def close(self) -> None:
        """Cleanup resources."""
        if self._client:
            # Close client connections if needed
            pass
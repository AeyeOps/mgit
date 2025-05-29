"""Git provider abstractions for mgit.

This package provides the abstract base class and supporting infrastructure
for implementing multi-provider support in mgit.
"""

# Base classes and data structures
from .base import (
    GitProvider,
    Repository,
    Organization,
    Project,
    AuthMethod,
)

# Factory pattern
from .factory import ProviderFactory

# Registry pattern
from .registry import (
    ProviderRegistry,
    register_provider,
    get_provider,
    get_provider_by_url,
    list_providers,
    get_provider_info,
    auto_discover,
    detect_provider_by_url,
    is_registered,
    unregister_provider,
    clear,
)

# Exceptions
from .exceptions import (
    ProviderError,
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    RateLimitError,
    ProviderNotFoundError,
    RepositoryNotFoundError,
    OrganizationNotFoundError,
    ProjectNotFoundError,
    PermissionError,
    APIError,
)

__all__ = [
    # Base classes
    "GitProvider",
    "Repository",
    "Organization",
    "Project",
    "AuthMethod",
    # Factory
    "ProviderFactory",
    # Registry
    "ProviderRegistry",
    "register_provider",
    "get_provider",
    "get_provider_by_url",
    "list_providers",
    "get_provider_info",
    "auto_discover",
    "detect_provider_by_url",
    "is_registered",
    "unregister_provider",
    "clear",
    # Exceptions
    "ProviderError",
    "AuthenticationError",
    "ConfigurationError", 
    "ConnectionError",
    "RateLimitError",
    "ProviderNotFoundError",
    "RepositoryNotFoundError",
    "OrganizationNotFoundError",
    "ProjectNotFoundError",
    "PermissionError",
    "APIError",
]
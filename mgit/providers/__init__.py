"""Git provider abstractions for mgit.

This package provides the abstract base class and supporting infrastructure
for implementing multi-provider support in mgit.
"""

# Base classes and data structures
# Import and register providers
from .azdevops import AzureDevOpsProvider
from .base import (
    AuthMethod,
    GitProvider,
    Organization,
    Project,
    Repository,
)
from .bitbucket import BitBucketProvider

# Exceptions
from .exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    OrganizationNotFoundError,
    PermissionError,
    ProjectNotFoundError,
    ProviderError,
    ProviderNotFoundError,
    RateLimitError,
    RepositoryNotFoundError,
)

# Factory pattern
from .factory import ProviderFactory
from .github import GitHubProvider

# Registry pattern
from .registry import (
    ProviderRegistry,
    auto_discover,
    clear,
    detect_provider_by_url,
    get_provider,
    get_provider_by_url,
    get_provider_info,
    is_registered,
    list_providers,
    register_provider,
    unregister_provider,
)

# Register available providers (Factory pattern)
ProviderFactory.register_provider("azuredevops", AzureDevOpsProvider)
ProviderFactory.register_provider("azdevops", AzureDevOpsProvider)  # Alias
ProviderFactory.register_provider("azure", AzureDevOpsProvider)  # Alias
ProviderFactory.register_provider("github", GitHubProvider)
ProviderFactory.register_provider("bitbucket", BitBucketProvider)

# Register with registry (new pattern)
register_provider("azuredevops", AzureDevOpsProvider)  # Primary name
register_provider("azure", AzureDevOpsProvider)  # Alias
register_provider("github", GitHubProvider)
register_provider("bitbucket", BitBucketProvider)

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
    # Providers
    "AzureDevOpsProvider",
    "GitHubProvider",
    "BitBucketProvider",
]

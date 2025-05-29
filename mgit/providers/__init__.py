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

# Provider implementations
from .github import GitHubProvider

# Register providers with factory
ProviderFactory.register_provider("github", GitHubProvider)

__all__ = [
    # Base classes
    "GitProvider",
    "Repository",
    "Organization",
    "Project",
    "AuthMethod",
    # Factory
    "ProviderFactory",
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
    # Provider implementations
    "GitHubProvider",
]
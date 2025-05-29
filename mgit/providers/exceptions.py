"""Provider-specific exceptions.

This module defines additional provider-specific exceptions that extend
the main mgit exception hierarchy.
"""

from typing import Optional
from datetime import datetime

# Import base exceptions from main exceptions module
from mgit.exceptions import (
    ProviderError as BaseProviderError,
    AuthenticationError as BaseAuthenticationError,
    ConfigurationError as BaseConfigurationError,
    ConnectionError as BaseConnectionError,
    OrganizationNotFoundError as BaseOrganizationNotFoundError,
    ProjectNotFoundError as BaseProjectNotFoundError,
    MgitError,
)


# Additional provider-specific exceptions
class RateLimitError(BaseProviderError):
    """Rate limit exceeded."""
    
    def __init__(self, message: str, provider: str, reset_time: Optional[datetime] = None):
        """Initialize rate limit error.
        
        Args:
            message: Error message
            provider: The provider that hit the rate limit
            reset_time: When the rate limit will reset
        """
        super().__init__(message, provider=provider, exit_code=12)
        self.reset_time = reset_time
        if reset_time:
            self.details = f"{self.details}, Reset time: {reset_time.isoformat()}"


class ProviderNotFoundError(BaseProviderError):
    """Provider type not found."""
    
    def __init__(self, provider_type: str):
        """Initialize provider not found error.
        
        Args:
            provider_type: The requested provider type
        """
        message = f"Provider type '{provider_type}' not found or not supported"
        super().__init__(message, provider=provider_type, exit_code=13)


class RepositoryNotFoundError(BaseProviderError):
    """Repository not found."""
    
    def __init__(self, repository: str, provider: str):
        """Initialize repository not found error.
        
        Args:
            repository: The repository name/path
            provider: The provider being used
        """
        message = f"Repository '{repository}' not found"
        super().__init__(message, provider=provider, exit_code=14)
        self.repository = repository


class PermissionError(BaseProviderError):
    """Insufficient permissions."""
    
    def __init__(self, message: str, provider: str, resource: Optional[str] = None):
        """Initialize permission error.
        
        Args:
            message: Error message
            provider: The provider where permission was denied
            resource: The resource that couldn't be accessed
        """
        super().__init__(message, provider=provider, exit_code=15)
        if resource:
            self.details = f"{self.details}, Resource: {resource}"


class APIError(BaseProviderError):
    """Generic API error from provider."""
    
    def __init__(self, message: str, provider: str, status_code: Optional[int] = None):
        """Initialize API error.
        
        Args:
            message: Error message
            provider: The provider that returned the error
            status_code: HTTP status code if applicable
        """
        super().__init__(message, provider=provider, exit_code=16)
        self.status_code = status_code
        if status_code:
            self.details = f"{self.details}, Status code: {status_code}"


# Re-export base exceptions for convenience
ProviderError = BaseProviderError
AuthenticationError = BaseAuthenticationError
ConfigurationError = BaseConfigurationError
ConnectionError = BaseConnectionError
OrganizationNotFoundError = BaseOrganizationNotFoundError
ProjectNotFoundError = BaseProjectNotFoundError


__all__ = [
    # Base exceptions (re-exported)
    "ProviderError",
    "AuthenticationError",
    "ConfigurationError",
    "ConnectionError",
    "OrganizationNotFoundError",
    "ProjectNotFoundError",
    # Provider-specific exceptions
    "RateLimitError",
    "ProviderNotFoundError",
    "RepositoryNotFoundError",
    "PermissionError",
    "APIError",
]
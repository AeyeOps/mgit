"""Provider factory for creating git provider instances.

This module implements the factory pattern for creating provider instances
based on provider type and configuration.
"""

from typing import Any, Dict, List, Type

from .base import GitProvider


class ProviderFactory:
    """Factory for creating provider instances."""

    _providers: Dict[str, Type[GitProvider]] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[GitProvider]) -> None:
        """Register a new provider type.

        Args:
            name: Provider name (e.g., 'azuredevops', 'github', 'bitbucket')
            provider_class: Provider class that inherits from GitProvider
        """
        cls._providers[name.lower()] = provider_class

    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> GitProvider:
        """Create a provider instance.

        Args:
            provider_type: Type of provider (azuredevops, github, bitbucket)
            config: Provider-specific configuration

        Returns:
            GitProvider instance

        Raises:
            ValueError: If provider type is unknown
        """
        provider_class = cls._providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(
                f"Unknown provider type: {provider_type}. "
                f"Available: {', '.join(cls._providers.keys())}"
            )

        return provider_class(config)

    @classmethod
    def list_providers(cls) -> List[str]:
        """List available provider types.

        Returns:
            List of registered provider names
        """
        return list(cls._providers.keys())

    @classmethod
    def is_registered(cls, provider_type: str) -> bool:
        """Check if a provider type is registered.

        Args:
            provider_type: Provider type to check

        Returns:
            bool: True if provider is registered
        """
        return provider_type.lower() in cls._providers

    @classmethod
    def unregister_provider(cls, name: str) -> None:
        """Unregister a provider type.

        Args:
            name: Provider name to unregister
        """
        cls._providers.pop(name.lower(), None)

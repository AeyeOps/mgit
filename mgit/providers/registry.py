"""Provider registry for auto-discovery and management of git providers.

This module implements a singleton registry pattern that manages all git provider
implementations. It provides auto-discovery of provider classes, URL pattern
matching, and validation of provider implementations.
"""

import importlib
import inspect
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type
from urllib.parse import urlparse

from .base import GitProvider
from .exceptions import ConfigurationError, ProviderNotFoundError

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Singleton registry for managing git provider implementations.

    The registry handles:
    - Registration of provider classes
    - Auto-discovery of providers in the providers package
    - URL pattern matching to determine provider type
    - Validation of provider implementations
    - Provider instance creation and caching
    """

    _instance: Optional["ProviderRegistry"] = None
    _initialized: bool = False

    # URL patterns for each provider type
    # Order matters - more specific patterns should come first
    URL_PATTERNS: List[Tuple[re.Pattern, str]] = [
        # Azure DevOps patterns
        (re.compile(r"https?://dev\.azure\.com/[^/]+", re.IGNORECASE), "azuredevops"),
        (
            re.compile(r"https?://[^/]+\.visualstudio\.com", re.IGNORECASE),
            "azuredevops",
        ),
        (
            re.compile(r"https?://[^/]+/tfs", re.IGNORECASE),
            "azuredevops",
        ),  # On-prem TFS
        # GitHub patterns
        (re.compile(r"https?://github\.com/[^/]+", re.IGNORECASE), "github"),
        (
            re.compile(r"https?://[^/]+/.*github", re.IGNORECASE),
            "github",
        ),  # GitHub Enterprise
        (re.compile(r"https?://api\.github\.com", re.IGNORECASE), "github"),
        # Bitbucket patterns
        (re.compile(r"https?://bitbucket\.org/[^/]+", re.IGNORECASE), "bitbucket"),
        (re.compile(r"https?://api\.bitbucket\.org", re.IGNORECASE), "bitbucket"),
        (
            re.compile(r"https?://[^/]+/.*bitbucket", re.IGNORECASE),
            "bitbucket",
        ),  # Bitbucket Server
        # GitLab patterns (for future extension)
        (re.compile(r"https?://gitlab\.com/[^/]+", re.IGNORECASE), "gitlab"),
        (re.compile(r"https?://[^/]+/.*gitlab", re.IGNORECASE), "gitlab"),
    ]

    def __new__(cls) -> "ProviderRegistry":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the registry (only once due to singleton)."""
        if not self._initialized:
            self._providers: Dict[str, Type[GitProvider]] = {}
            self._provider_instances: Dict[str, GitProvider] = {}
            self._auto_discovered = False
            ProviderRegistry._initialized = True
            logger.debug("ProviderRegistry initialized")

    def register_provider(
        self, name: str, provider_class: Type[GitProvider], validate: bool = True
    ) -> None:
        """Register a provider class.

        Args:
            name: Provider name (e.g., 'azuredevops', 'github', 'bitbucket')
            provider_class: Provider class that inherits from GitProvider
            validate: Whether to validate the provider implementation

        Raises:
            ConfigurationError: If provider doesn't properly implement GitProvider
        """
        name = name.lower()

        if validate:
            self._validate_provider_class(name, provider_class)

        if name in self._providers:
            logger.warning(
                "Overwriting existing provider '%s' with %s",
                name,
                provider_class.__name__,
            )

        self._providers[name] = provider_class
        logger.info("Registered provider '%s' -> %s", name, provider_class.__name__)

        # Clear any cached instance of this provider
        if name in self._provider_instances:
            del self._provider_instances[name]

    def _validate_provider_class(
        self, name: str, provider_class: Type[GitProvider]
    ) -> None:
        """Validate that a provider class properly implements GitProvider.

        Args:
            name: Provider name for error messages
            provider_class: The class to validate

        Raises:
            ConfigurationError: If validation fails
        """
        # Check inheritance
        if not issubclass(provider_class, GitProvider):
            raise ConfigurationError(
                f"Provider '{name}' must inherit from GitProvider",
                field="provider_class",
            )

        # Check required class attributes
        required_attrs = [
            "PROVIDER_NAME",
            "SUPPORTED_AUTH_METHODS",
            "DEFAULT_API_VERSION",
        ]
        for attr in required_attrs:
            if not hasattr(provider_class, attr):
                raise ConfigurationError(
                    f"Provider '{name}' missing required attribute: {attr}",
                    field="provider_class",
                )

        # Check that PROVIDER_NAME matches registered name (skip for aliases)
        if provider_class.PROVIDER_NAME.lower() != name:
            # Only warn for the primary name, not aliases
            if provider_class.PROVIDER_NAME.lower() not in [
                n.lower() for n in self._providers.keys()
            ]:
                logger.warning(
                    "Provider name mismatch: registered as '%s' but PROVIDER_NAME is '%s'",
                    name,
                    provider_class.PROVIDER_NAME,
                )

        # Verify abstract methods are implemented
        abstract_methods = [
            "_validate_config",
            "authenticate",
            "test_connection",
            "list_organizations",
            "list_projects",
            "list_repositories",
            "get_repository",
            "get_authenticated_clone_url",
        ]

        for method_name in abstract_methods:
            method = getattr(provider_class, method_name, None)
            if method is None:
                raise ConfigurationError(
                    f"Provider '{name}' missing required method: {method_name}",
                    field="provider_class",
                )

            # Check if it's still abstract
            if getattr(method, "__isabstractmethod__", False):
                raise ConfigurationError(
                    f"Provider '{name}' has unimplemented abstract method: {method_name}",
                    field="provider_class",
                )

    def get_provider(self, provider_type: str, config: Dict[str, Any]) -> GitProvider:
        """Get a provider instance by type.

        This method creates a new instance or returns a cached one based on
        the provider type and configuration.

        Args:
            provider_type: Type of provider (azuredevops, github, bitbucket)
            config: Provider-specific configuration

        Returns:
            GitProvider instance

        Raises:
            ProviderNotFoundError: If provider type is unknown
        """
        # Ensure auto-discovery has run
        if not self._auto_discovered:
            self.auto_discover()

        provider_type = provider_type.lower()

        if provider_type not in self._providers:
            raise ProviderNotFoundError(provider_type)

        # For now, always create a new instance
        # In the future, we might want to cache based on config hash
        provider_class = self._providers[provider_type]
        return provider_class(config)

    def get_provider_by_url(
        self, url: str, config: Optional[Dict[str, Any]] = None
    ) -> GitProvider:
        """Get a provider instance based on URL pattern matching.

        Args:
            url: URL to match against provider patterns
            config: Optional provider configuration (URL will be added if not present)

        Returns:
            GitProvider instance

        Raises:
            ProviderNotFoundError: If no provider matches the URL
        """
        provider_type = self.detect_provider_by_url(url)

        if config is None:
            config = {}

        # Add URL to config if not present
        if "url" not in config:
            config["url"] = url

        return self.get_provider(provider_type, config)

    def detect_provider_by_url(self, url: str) -> str:
        """Detect provider type from URL pattern.

        Args:
            url: URL to analyze

        Returns:
            Provider type string (e.g., 'github', 'azuredevops')

        Raises:
            ProviderNotFoundError: If no pattern matches
        """
        if not url:
            raise ProviderNotFoundError("Empty URL provided")

        # Normalize URL
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # Try each pattern
        for pattern, provider_type in self.URL_PATTERNS:
            if pattern.match(url):
                logger.debug("URL '%s' matched provider '%s'", url, provider_type)
                return provider_type

        # If no pattern matches, try to parse and make an educated guess
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        # Check hostname for provider keywords
        if "github" in hostname:
            return "github"
        elif "azure" in hostname or "visualstudio" in hostname:
            return "azuredevops"
        elif "bitbucket" in hostname:
            return "bitbucket"
        elif "gitlab" in hostname:
            return "gitlab"

        raise ProviderNotFoundError(
            f"Unable to determine provider type from URL: {url}"
        )

    def list_providers(self) -> List[str]:
        """List all registered provider types.

        Returns:
            List of registered provider names
        """
        # Ensure auto-discovery has run
        if not self._auto_discovered:
            self.auto_discover()

        return sorted(self._providers.keys())

    def is_registered(self, provider_type: str) -> bool:
        """Check if a provider type is registered.

        Args:
            provider_type: Provider type to check

        Returns:
            bool: True if provider is registered
        """
        return provider_type.lower() in self._providers

    def unregister_provider(self, name: str) -> None:
        """Unregister a provider type.

        Args:
            name: Provider name to unregister
        """
        name = name.lower()

        if name in self._providers:
            del self._providers[name]
            logger.info("Unregistered provider: %s", name)

        if name in self._provider_instances:
            del self._provider_instances[name]

    def auto_discover(self, package_path: Optional[Path] = None) -> None:
        """Auto-discover provider implementations in the providers package.

        This method scans the providers package for classes that inherit from
        GitProvider and automatically registers them based on their PROVIDER_NAME.

        Args:
            package_path: Optional path to scan (defaults to providers package)
        """
        if self._auto_discovered and package_path is None:
            return

        if package_path is None:
            # Get the providers package directory
            package_path = Path(__file__).parent

        logger.debug("Auto-discovering providers in: %s", package_path)

        # Find all Python files in the package
        for py_file in package_path.glob("*.py"):
            # Skip special files
            if py_file.name.startswith("_") or py_file.stem in [
                "base",
                "registry",
                "factory",
                "exceptions",
            ]:
                continue

            module_name = f"mgit.providers.{py_file.stem}"

            try:
                # Import the module
                module = importlib.import_module(module_name)

                # Scan for GitProvider subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, GitProvider)
                        and obj is not GitProvider
                        and hasattr(obj, "PROVIDER_NAME")
                        and obj.PROVIDER_NAME
                    ):
                        provider_name = obj.PROVIDER_NAME.lower()

                        # Skip if already registered (manual registration takes precedence)
                        if provider_name not in self._providers:
                            self.register_provider(provider_name, obj, validate=True)
                            logger.info(
                                "Auto-discovered provider: %s from %s",
                                provider_name,
                                module_name,
                            )

            except ImportError as e:
                logger.warning("Failed to import %s: %s", module_name, e)
            except Exception as e:
                logger.error("Error discovering providers in %s: %s", module_name, e)

        self._auto_discovered = True
        logger.info("Auto-discovery complete. Found %d providers", len(self._providers))

    def clear(self) -> None:
        """Clear all registered providers and cached instances.

        This is mainly useful for testing.
        """
        self._providers.clear()
        self._provider_instances.clear()
        self._auto_discovered = False
        logger.debug("Cleared provider registry")

    def get_provider_info(self, provider_type: str) -> Dict[str, Any]:
        """Get information about a registered provider.

        Args:
            provider_type: Provider type to get info for

        Returns:
            Dictionary with provider information

        Raises:
            ProviderNotFoundError: If provider not found
        """
        provider_type = provider_type.lower()

        if provider_type not in self._providers:
            raise ProviderNotFoundError(provider_type)

        provider_class = self._providers[provider_type]

        return {
            "name": provider_type,
            "class_name": provider_class.__name__,
            "provider_name": provider_class.PROVIDER_NAME,
            "supported_auth_methods": [
                m.value for m in provider_class.SUPPORTED_AUTH_METHODS
            ],
            "default_api_version": provider_class.DEFAULT_API_VERSION,
            "supports_projects": (
                provider_class().supports_projects()
                if hasattr(provider_class(), "supports_projects")
                else True
            ),
            "module": provider_class.__module__,
        }


# Create singleton instance
_registry = ProviderRegistry()

# Export convenience functions that use the singleton
register_provider = _registry.register_provider
get_provider = _registry.get_provider
get_provider_by_url = _registry.get_provider_by_url
list_providers = _registry.list_providers
is_registered = _registry.is_registered
unregister_provider = _registry.unregister_provider
auto_discover = _registry.auto_discover
detect_provider_by_url = _registry.detect_provider_by_url
get_provider_info = _registry.get_provider_info
clear = _registry.clear


__all__ = [
    "ProviderRegistry",
    "register_provider",
    "get_provider",
    "get_provider_by_url",
    "list_providers",
    "is_registered",
    "unregister_provider",
    "auto_discover",
    "detect_provider_by_url",
    "get_provider_info",
    "clear",
]

"""Modern provider manager for mgit with named configuration support.

This module provides a new provider manager that works with YAML-based
named configurations and supports multiple providers of the same type.
"""

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from mgit.config.yaml_manager import (
    detect_provider_type,
    get_default_provider_config,
    get_default_provider_name,
    get_provider_config,
    list_provider_names,
)

from .base import GitProvider
from .exceptions import ConfigurationError, ProviderNotFoundError
from .factory import ProviderFactory

logger = logging.getLogger(__name__)


class ProviderManager:
    """Modern provider manager with named configuration support.

    This manager works with YAML-based configurations and supports:
    - Named provider configurations (e.g., 'ado_myorg', 'github_personal')
    - Multiple configurations per provider type
    - Auto-detection from URLs
    - Fallback to default provider
    """

    def __init__(
        self, provider_name: Optional[str] = None, auto_detect_url: Optional[str] = None
    ):
        """Initialize provider manager.

        Args:
            provider_name: Named provider configuration (e.g., 'ado_myorg')
            auto_detect_url: URL to auto-detect provider type from
        """
        self.provider_name = provider_name
        self.auto_detect_url = auto_detect_url
        self._provider: Optional[GitProvider] = None
        self._provider_type: Optional[str] = None
        self._config: Optional[Dict[str, Any]] = None

        # Resolve provider configuration
        self._resolve_provider()

    def _resolve_provider(self) -> None:
        """Resolve which provider configuration to use."""
        try:
            if self.provider_name:
                # Use explicit named configuration
                self._config = get_provider_config(self.provider_name)
                self._provider_type = detect_provider_type(self.provider_name)
                logger.debug(
                    f"Using named provider '{self.provider_name}' of type '{self._provider_type}'"
                )

            elif self.auto_detect_url:
                # Auto-detect provider type from URL and use default config of that type
                self._provider_type = self._detect_provider_from_url(
                    self.auto_detect_url
                )
                self._config = self._find_config_by_type(self._provider_type)
                logger.debug(
                    f"Auto-detected provider type '{self._provider_type}' from URL"
                )

            else:
                # Use default provider
                default_name = get_default_provider_name()
                if default_name:
                    self.provider_name = default_name
                    self._config = get_default_provider_config()
                    self._provider_type = detect_provider_type(default_name)
                    logger.debug(
                        f"Using default provider '{default_name}' of type '{self._provider_type}'"
                    )
                else:
                    raise ConfigurationError(
                        "No provider specified and no default provider configured"
                    )

        except Exception as e:
            logger.error(f"Failed to resolve provider configuration: {e}")
            raise ConfigurationError(f"Provider resolution failed: {e}")

    def _detect_provider_from_url(self, url: str) -> str:
        """Detect provider type from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            if "dev.azure.com" in domain or "visualstudio.com" in domain:
                return "azuredevops"
            elif "github.com" in domain:
                return "github"
            elif "bitbucket.org" in domain:
                return "bitbucket"
            else:
                raise ValueError(f"Unknown provider domain: {domain}")

        except Exception as e:
            raise ValueError(f"Failed to parse URL '{url}': {e}")

    def _find_config_by_type(self, provider_type: str) -> Dict[str, Any]:
        """Find first configuration of given provider type."""
        from mgit.config.yaml_manager import get_provider_configs

        providers = get_provider_configs()
        for name, config in providers.items():
            try:
                if detect_provider_type(name) == provider_type:
                    self.provider_name = name
                    logger.debug(
                        f"Found '{name}' configuration for provider type '{provider_type}'"
                    )
                    return config
            except ValueError:
                continue

        raise ConfigurationError(
            f"No configuration found for provider type '{provider_type}'"
        )

    def get_provider(self) -> GitProvider:
        """Get the configured provider instance.

        Returns:
            GitProvider instance

        Raises:
            ProviderNotFoundError: If provider cannot be created
            ConfigurationError: If provider configuration is invalid
        """
        if self._provider:
            return self._provider

        if not self._config or not self._provider_type:
            raise ConfigurationError("Provider configuration not resolved")

        # Validate required fields based on provider type
        self._validate_config()

        # Create provider instance
        try:
            self._provider = ProviderFactory.create_provider(
                self._provider_type, self._config
            )
            logger.debug(
                f"Created {self._provider_type} provider from config '{self.provider_name}'"
            )
            return self._provider

        except Exception as e:
            raise ProviderNotFoundError(
                f"Failed to create {self._provider_type} provider: {e}"
            )

    def _validate_config(self) -> None:
        """Validate provider configuration has required fields."""
        if not self._config:
            raise ConfigurationError("No configuration available")

        # Map YAML field names to provider field names
        if self._provider_type == "azuredevops":
            required_yaml = ["org_url", "pat"]
            # Map to provider expected field names
            if "org_url" in self._config:
                self._config["organization_url"] = self._config["org_url"]
        elif self._provider_type == "github":
            required_yaml = ["token"]
            # Map token to pat for GitHub provider
            if "token" in self._config:
                self._config["pat"] = self._config["token"]
                # Also set base_url if not present
                if "base_url" not in self._config:
                    self._config["base_url"] = "https://api.github.com"
        elif self._provider_type == "bitbucket":
            required_yaml = ["username", "app_password"]
            # Map fields for BitBucket
            if "default_workspace" in self._config:
                self._config["workspace"] = self._config["default_workspace"]
            # Set default base_url if not present
            if "base_url" not in self._config:
                self._config["base_url"] = "https://api.bitbucket.org/2.0"
        else:
            raise ConfigurationError(f"Unknown provider type: {self._provider_type}")

        missing = [field for field in required_yaml if not self._config.get(field)]
        if missing:
            raise ConfigurationError(
                f"Missing required fields for {self._provider_type}: {missing}. "
                f"Available fields: {list(self._config.keys())}"
            )

    async def test_connection_async(self) -> bool:
        """Test provider connection and authentication (async).

        Returns:
            bool: True if connection successful
        """
        try:
            provider = self.get_provider()

            # Most providers have async authenticate
            if hasattr(provider, "authenticate"):
                return await provider.authenticate()

            return True

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def test_connection(self) -> bool:
        """Test provider connection and authentication (sync wrapper).

        Returns:
            bool: True if connection successful
        """
        import asyncio

        try:
            # Check if we're in an async context
            try:
                asyncio.get_running_loop()
                # We're in an async context
                logger.warning(
                    "test_connection called from async context - use test_connection_async instead"
                )
                # Create a new thread to run the async code
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.test_connection_async())
                    return future.result()
            except RuntimeError:
                # Not in an async context, safe to use asyncio.run
                return asyncio.run(self.test_connection_async())
        except Exception as e:
            logger.error(f"Error in test_connection: {e}")
            return False

    def supports_provider(self) -> bool:
        """Check if the provider type is supported.

        Returns:
            bool: True if provider is supported
        """
        if not self._provider_type:
            return False
        return ProviderFactory.is_registered(self._provider_type)

    @property
    def provider_type(self) -> str:
        """Get the provider type."""
        return self._provider_type or "unknown"

    @property
    def config(self) -> Dict[str, Any]:
        """Get the provider configuration."""
        return self._config or {}

    def get_available_providers(self) -> Dict[str, str]:
        """Get all available provider names and their types.

        Returns:
            Dict mapping provider names to their types
        """
        result = {}
        for name in list_provider_names():
            try:
                provider_type = detect_provider_type(name)
                result[name] = provider_type
            except ValueError as e:
                logger.warning(f"Could not detect type for provider '{name}': {e}")

        return result

    async def list_repositories_async(self, project: str):
        """List repositories for a project (async).

        Args:
            project: Project name or identifier

        Returns:
            List of Repository objects

        Raises:
            ProviderNotFoundError: If no suitable provider available
        """
        try:
            provider = self.get_provider()
            repos = []
            try:
                # For GitHub and BitBucket, project is the organization/workspace name
                # For Azure DevOps, we need both organization and project
                if self._provider_type in ["github", "bitbucket"]:
                    async for repo in provider.list_repositories(project, None):
                        repos.append(repo)
                else:
                    # Azure DevOps style: organization, project
                    async for repo in provider.list_repositories("", project):
                        repos.append(repo)
                return repos
            finally:
                # Don't close provider here - it might be reused
                pass
        except Exception as e:
            logger.error(f"Failed to list repositories: {e}")
            raise ProviderNotFoundError(
                f"No suitable provider available for {self._provider_type}: {e}"
            )

    def list_repositories(self, project: str):
        """List repositories for a project (sync wrapper).

        Args:
            project: Project name or identifier

        Returns:
            List of Repository objects

        Raises:
            ProviderNotFoundError: If no suitable provider available
        """
        import asyncio

        try:
            # Check if we're in an async context
            try:
                asyncio.get_running_loop()
                # We're in an async context
                logger.warning(
                    "list_repositories called from async context - use list_repositories_async instead"
                )
                # Create a new thread to run the async code
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, self.list_repositories_async(project)
                    )
                    return future.result()
            except RuntimeError:
                # Not in an async context, safe to use asyncio.run
                return asyncio.run(self.list_repositories_async(project))
        except Exception as e:
            logger.error(f"Error in list_repositories: {e}")
            raise

    def get_authenticated_clone_url(self, repository) -> str:
        """Get clone URL with embedded authentication for a repository.

        Args:
            repository: Repository object or dict with clone_url

        Returns:
            Authenticated clone URL
        """
        try:
            provider = self.get_provider()

            # Convert dict to Repository object if needed
            if isinstance(repository, dict):
                from mgit.providers.base import Repository

                repo = Repository(
                    name=repository.get("name", ""),
                    clone_url=repository.get("clone_url", ""),
                    is_disabled=repository.get("is_disabled", False),
                    provider=self._provider_type,
                )
            else:
                repo = repository

            return provider.get_authenticated_clone_url(repo)
        except Exception as e:
            logger.error(f"Failed to get authenticated URL: {e}")
            # Fallback to regular clone URL
            if hasattr(repository, "clone_url"):
                return repository.clone_url
            elif isinstance(repository, dict) and "clone_url" in repository:
                return repository["clone_url"]
            else:
                raise

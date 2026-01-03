"""Modern provider manager for mgit with named configuration support.

This module provides a new provider manager that works with YAML-based
named configurations and supports multiple providers of the same type.
"""

import logging
from typing import Any
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
        self, provider_name: str | None = None, auto_detect_url: str | None = None
    ):
        """Initialize provider manager.

        Args:
            provider_name: Named provider configuration (e.g., 'ado_myorg')
            auto_detect_url: URL to auto-detect provider type from
        """
        self.provider_name = provider_name
        self.auto_detect_url = auto_detect_url
        self._provider: GitProvider | None = None
        self._provider_type: str | None = None
        self._config: dict[str, Any] | None = None

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
                _, self._config = self._find_config_by_type(self._provider_type)
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

    def _find_config_by_type(
        self, provider_type: str, *, set_name: bool = True
    ) -> tuple[str, dict[str, Any]]:
        """Find first configuration of given provider type."""
        from mgit.config.yaml_manager import get_provider_configs

        providers = get_provider_configs()
        for name, config in providers.items():
            try:
                if detect_provider_type(name) == provider_type:
                    if set_name:
                        self.provider_name = name
                    logger.debug(
                        f"Found '{name}' configuration for provider type '{provider_type}'"
                    )
                    return name, config
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

        # Validate unified fields exist
        required_unified = ["url", "user", "token"]
        missing = [field for field in required_unified if field not in self._config]
        if missing:
            raise ConfigurationError(
                f"Missing required unified fields: {missing}. "
                f"All providers must have: url, user, token, workspace (optional)"
            )

        # No field mapping needed - providers now use unified fields directly
        if self._provider_type not in ["azuredevops", "github", "bitbucket"]:
            raise ConfigurationError(f"Unknown provider type: {self._provider_type}")

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
    def config(self) -> dict[str, Any]:
        """Get the provider configuration."""
        return self._config or {}

    def get_available_providers(self) -> dict[str, str]:
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
                    # Azure DevOps style: parse org/project/repo pattern
                    parts = project.split("/")
                    if len(parts) >= 3:
                        # Full pattern: org/project/repo - use org and project only
                        org_name = parts[0]
                        project_name = parts[1]
                        # Note: parts[2] is the repo pattern, filtering happens elsewhere
                        async for repo in provider.list_repositories(
                            org_name, project_name
                        ):
                            repos.append(repo)
                    elif len(parts) == 2:
                        # Two parts: org/project
                        org_name, project_name = parts
                        async for repo in provider.list_repositories(
                            org_name, project_name
                        ):
                            repos.append(repo)
                    else:
                        # Just project name
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
            # Try to use provider specific to repository provider type if present
            repo_provider_type = None
            clone_url = None
            name = None
            is_disabled = False
            if hasattr(repository, "provider"):
                repo_provider_type = repository.provider
                clone_url = getattr(repository, "clone_url", None)
                name = getattr(repository, "name", None)
                is_disabled = getattr(repository, "is_disabled", False)
            elif isinstance(repository, dict):
                repo_provider_type = repository.get("provider")
                clone_url = repository.get("clone_url")
                name = repository.get("name")
                is_disabled = repository.get("is_disabled", False)

            provider = self.get_provider()
            if repo_provider_type and repo_provider_type != self._provider_type:
                try:
                    _, temp_config = self._find_config_by_type(
                        repo_provider_type, set_name=False
                    )
                    provider = ProviderFactory.create_provider(
                        repo_provider_type, temp_config
                    )
                except Exception:
                    provider = self.get_provider()

            # Convert to Repository object if needed
            if isinstance(repository, dict):
                from mgit.providers.base import Repository

                repo = Repository(
                    name=name or "",
                    clone_url=clone_url or "",
                    is_disabled=is_disabled,
                    provider=repo_provider_type or self._provider_type,
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

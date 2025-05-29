"""Provider manager for mgit.

This module provides a unified interface for working with different git providers,
handling provider selection, configuration, and fallback to legacy implementations.
"""

import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from .factory import ProviderFactory
from .registry import detect_provider_by_url, get_provider_by_url
from .base import GitProvider, Repository
from .exceptions import ProviderNotFoundError, ConfigurationError
from mgit.config.providers import get_provider_config, validate_provider_config

# Import legacy Azure DevOps manager for fallback
from mgit.legacy.azdevops_manager import AzDevOpsManager

logger = logging.getLogger(__name__)


class ProviderManager:
    """Unified provider manager with fallback support.
    
    This class provides a bridge between the CLI and provider infrastructure,
    handling provider selection and graceful fallback to legacy implementations
    when providers are not fully implemented.
    """
    
    def __init__(
        self, 
        provider_type: Optional[str] = None,
        auto_detect_url: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize provider manager.
        
        Args:
            provider_type: Explicit provider type (azuredevops, github, bitbucket)
            auto_detect_url: URL to auto-detect provider from
            config: Optional explicit configuration
        """
        self.provider_type = provider_type
        self.auto_detect_url = auto_detect_url
        self.config = config or {}
        self._provider: Optional[GitProvider] = None
        self._legacy_manager: Optional[Any] = None
        
        # Auto-detect provider if URL provided
        if auto_detect_url and not provider_type:
            try:
                self.provider_type = detect_provider_by_url(auto_detect_url)
                logger.debug(f"Auto-detected provider: {self.provider_type}")
            except Exception as e:
                logger.warning(f"Failed to auto-detect provider from {auto_detect_url}: {e}")
                self.provider_type = "azuredevops"  # Default fallback
        
        # Default to Azure DevOps if no provider specified
        if not self.provider_type:
            self.provider_type = "azuredevops"
            
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
            
        # Get provider configuration
        if not self.config:
            self.config = get_provider_config(self.provider_type)
            
        # Validate configuration
        validation_errors = validate_provider_config(self.provider_type, self.config)
        if validation_errors:
            raise ConfigurationError(
                f"Provider configuration invalid: {', '.join(validation_errors)}"
            )
            
        # Try to create provider
        try:
            self._provider = ProviderFactory.create_provider(self.provider_type, self.config)
            logger.debug(f"Created {self.provider_type} provider")
            return self._provider
        except NotImplementedError:
            # Provider is not fully implemented yet
            logger.warning(
                f"{self.provider_type} provider not fully implemented, "
                "checking for legacy support"
            )
            raise ProviderNotFoundError(
                f"Provider {self.provider_type} is not fully implemented yet"
            )
    
    def get_legacy_manager(self):
        """Get legacy Azure DevOps manager for fallback.
        
        Returns:
            AzDevOpsManager instance or None if not available
        """
        if self.provider_type != "azuredevops":
            return None
            
        if self._legacy_manager:
            return self._legacy_manager
            
        try:
            # Create Azure DevOps manager with current config
            org_url = self.config.get("organization_url")
            pat = self.config.get("pat")
            
            # Create AzDevOpsManager instance with current config
            self._legacy_manager = AzDevOpsManager(organization_url=org_url, pat=pat)
            logger.debug("Created legacy Azure DevOps manager")
            return self._legacy_manager
        except Exception as e:
            logger.error(f"Failed to create legacy Azure DevOps manager: {e}")
            return None
    
    def supports_provider(self) -> bool:
        """Check if the current provider is supported.
        
        Returns:
            bool: True if provider is available (either new or legacy)
        """
        try:
            # Try new provider first
            self.get_provider()
            return True
        except (ProviderNotFoundError, NotImplementedError):
            # Check for legacy support
            if self.provider_type == "azuredevops":
                return self.get_legacy_manager() is not None
            return False
    
    def list_repositories(self, project: str) -> List[Repository]:
        """List repositories for a project.
        
        Args:
            project: Project name or identifier
            
        Returns:
            List of Repository objects
            
        Raises:
            ProviderNotFoundError: If no suitable provider available
        """
        # Try new provider first
        try:
            provider = self.get_provider()
            # Handle async list_repositories method
            import asyncio
            async def _async_list():
                repos = []
                try:
                    # For GitHub and BitBucket, project is the organization/workspace name
                    # For Azure DevOps, we need both organization and project
                    if self.provider_type in ["github", "bitbucket"]:
                        async for repo in provider.list_repositories(project, None):
                            repos.append(repo)
                    else:
                        # Azure DevOps style: organization, project
                        async for repo in provider.list_repositories("", project):
                            repos.append(repo)
                    return repos
                finally:
                    # Ensure cleanup of async resources
                    if hasattr(provider, 'close'):
                        await provider.close()
            return asyncio.run(_async_list())
        except (ProviderNotFoundError, NotImplementedError):
            # Fall back to legacy for Azure DevOps
            if self.provider_type == "azuredevops":
                legacy_manager = self.get_legacy_manager()
                if legacy_manager:
                    # Convert legacy response to Repository objects
                    # This requires calling the legacy SDK methods
                    return self._convert_legacy_repos(legacy_manager, project)
            
            raise ProviderNotFoundError(
                f"No suitable provider available for {self.provider_type}"
            )
    
    def _convert_legacy_repos(self, ado_manager, project: str) -> List[Repository]:
        """Convert legacy Azure DevOps repositories to Repository objects.
        
        Args:
            ado_manager: Legacy AzDevOpsManager instance
            project: Project name
            
        Returns:
            List of Repository objects
        """
        repositories = []
        
        try:
            # Get project details
            project_details = ado_manager.get_project(project)
            if not project_details:
                return []
                
            # Get repositories using SDK
            repos = ado_manager.git_client.get_repositories(project=project_details.id)
            
            # Convert to Repository objects
            for repo in repos:
                repository = Repository(
                    id=repo.id,
                    name=repo.name,
                    full_name=f"{project}/{repo.name}",
                    description=None,  # Azure DevOps repos don't have descriptions
                    clone_url=repo.remote_url,
                    ssh_url=repo.ssh_url if hasattr(repo, 'ssh_url') else None,
                    default_branch=repo.default_branch,
                    is_private=True,  # Azure DevOps repos are typically private
                    is_disabled=repo.is_disabled,
                    size=getattr(repo, 'size', 0),
                    created_at=None,  # Not available in current SDK response
                    updated_at=None,  # Not available in current SDK response
                    owner=project,
                    provider=self.provider_type
                )
                repositories.append(repository)
                
        except Exception as e:
            logger.error(f"Failed to convert legacy repositories: {e}")
            
        return repositories
    
    def test_connection(self) -> bool:
        """Test connection to the provider.
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Try new provider first
            provider = self.get_provider()
            # Handle async test_connection method
            if hasattr(provider.test_connection, '__call__'):
                import inspect
                if inspect.iscoroutinefunction(provider.test_connection):
                    import asyncio
                    return asyncio.run(provider.test_connection())
                else:
                    return provider.test_connection()
            return False
        except (ProviderNotFoundError, NotImplementedError):
            # Fall back to legacy for Azure DevOps
            if self.provider_type == "azuredevops":
                legacy_manager = self.get_legacy_manager()
                if legacy_manager:
                    return legacy_manager.test_connection()
            return False
    
    @staticmethod
    def auto_detect_provider(url: str) -> str:
        """Auto-detect provider type from URL.
        
        Args:
            url: Repository or organization URL
            
        Returns:
            Provider type string
            
        Raises:
            ValueError: If provider cannot be detected
        """
        try:
            return detect_provider_by_url(url)
        except Exception:
            # Try to detect manually from common patterns
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            
            if "github.com" in domain:
                return "github"
            elif "bitbucket.org" in domain or "bitbucket.com" in domain:
                return "bitbucket"  
            elif "dev.azure.com" in domain or "visualstudio.com" in domain:
                return "azuredevops"
            else:
                raise ValueError(f"Cannot auto-detect provider from URL: {url}")
                
    @staticmethod
    def list_supported_providers() -> List[str]:
        """List all supported provider types.
        
        Returns:
            List of provider type strings
        """
        return ProviderFactory.list_providers()
        
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider.
        
        Returns:
            Dictionary with provider information
        """
        return {
            "type": self.provider_type,
            "config": self.config,
            "supported": self.supports_provider(),
            "is_legacy": self.provider_type == "azuredevops" and not self._provider
        }
"""
Main credential manager for mgit.

This module provides the high-level API for credential management,
coordinating between storage backends and providing a clean interface
for the rest of the application.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from mgit.auth.models import Credential, Provider
from mgit.auth.storage import CompositeStorage, StorageBackend

logger = logging.getLogger(__name__)


class CredentialManager:
    """
    High-level credential management interface.
    
    This class provides a simple API for storing, retrieving, and managing
    credentials across different providers. It automatically handles storage
    backend selection and fallback.
    """
    
    def __init__(self, storage_backend: Optional[StorageBackend] = None):
        """
        Initialize the credential manager.
        
        Args:
            storage_backend: Optional custom storage backend. 
                           If not provided, uses CompositeStorage with automatic fallback.
        """
        self.storage = storage_backend or CompositeStorage()
    
    def store_credential(
        self,
        provider: Provider,
        name: str,
        token: str,
        username: Optional[str] = None,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store a credential securely.
        
        Args:
            provider: The git provider (e.g., Provider.AZURE_DEVOPS)
            name: A unique name for this credential
            token: The authentication token/password
            username: Optional username
            url: Optional associated URL
            metadata: Optional provider-specific metadata
            
        Returns:
            True if successfully stored, False otherwise
        """
        try:
            # Check if credential already exists
            existing = self.get_credential(provider, name)
            
            # Create new or update existing credential
            credential = Credential(
                provider=provider,
                name=name,
                token=token,
                username=username,
                url=url,
                metadata=metadata,
                created_at=existing.created_at if existing else None,
                updated_at=datetime.now()
            )
            
            success = self.storage.store(credential)
            if success:
                action = "Updated" if existing else "Stored"
                logger.info(f"{action} credential '{name}' for {provider.value}")
            else:
                logger.error(f"Failed to store credential '{name}' for {provider.value}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error storing credential: {e}")
            return False
    
    def get_credential(self, provider: Provider, name: str) -> Optional[Credential]:
        """
        Retrieve a credential.
        
        Args:
            provider: The git provider
            name: The credential name
            
        Returns:
            The credential if found, None otherwise
        """
        try:
            credential = self.storage.get(provider, name)
            if credential:
                logger.debug(f"Retrieved credential '{name}' for {provider.value}")
            else:
                logger.debug(f"Credential '{name}' not found for {provider.value}")
            return credential
            
        except Exception as e:
            logger.error(f"Error retrieving credential: {e}")
            return None
    
    def get_credential_for_url(self, url: str) -> Optional[Credential]:
        """
        Get the most appropriate credential for a given URL.
        
        This method attempts to find a credential that matches the URL,
        first by exact match, then by provider detection.
        
        Args:
            url: The repository URL
            
        Returns:
            The best matching credential, or None if not found
        """
        try:
            # Detect provider from URL
            provider = Provider.from_url(url)
            
            # Get all credentials for this provider
            credentials = self.list_credentials(provider)
            
            # First, try exact URL match
            for cred in credentials:
                if cred.url and cred.url.lower() in url.lower():
                    logger.debug(f"Found credential by URL match: {cred.name}")
                    return cred
            
            # Then, try to find a default credential for the provider
            for cred in credentials:
                if cred.name.lower() in ["default", "main", provider.value]:
                    logger.debug(f"Found default credential: {cred.name}")
                    return cred
            
            # Return the first credential for this provider
            if credentials:
                logger.debug(f"Using first available credential: {credentials[0].name}")
                return credentials[0]
            
            logger.debug(f"No credential found for URL: {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting credential for URL: {e}")
            return None
    
    def delete_credential(self, provider: Provider, name: str) -> bool:
        """
        Delete a credential.
        
        Args:
            provider: The git provider
            name: The credential name
            
        Returns:
            True if successfully deleted, False otherwise
        """
        try:
            success = self.storage.delete(provider, name)
            if success:
                logger.info(f"Deleted credential '{name}' for {provider.value}")
            else:
                logger.warning(f"Failed to delete credential '{name}' for {provider.value}")
            return success
            
        except Exception as e:
            logger.error(f"Error deleting credential: {e}")
            return False
    
    def list_credentials(self, provider: Optional[Provider] = None) -> List[Credential]:
        """
        List all stored credentials.
        
        Args:
            provider: Optional provider to filter by
            
        Returns:
            List of credentials
        """
        try:
            credentials = self.storage.list(provider)
            if provider:
                logger.debug(f"Found {len(credentials)} credentials for {provider.value}")
            else:
                logger.debug(f"Found {len(credentials)} total credentials")
            return credentials
            
        except Exception as e:
            logger.error(f"Error listing credentials: {e}")
            return []
    
    def migrate_from_config(self, config_values: Dict[str, Any]) -> bool:
        """
        Migrate credentials from old config format to secure storage.
        
        This helps users transition from storing PATs in config files
        to using secure credential storage.
        
        Args:
            config_values: Dictionary of config values that may contain credentials
            
        Returns:
            True if any credentials were migrated
        """
        migrated = False
        
        try:
            # Check for Azure DevOps PAT
            if "AZURE_DEVOPS_EXT_PAT" in config_values:
                pat = config_values["AZURE_DEVOPS_EXT_PAT"]
                org_url = config_values.get("AZURE_DEVOPS_ORG_URL", "")
                
                if pat and not self.get_credential(Provider.AZURE_DEVOPS, "default"):
                    success = self.store_credential(
                        provider=Provider.AZURE_DEVOPS,
                        name="default",
                        token=pat,
                        url=org_url,
                        metadata={"migrated_from": "config"}
                    )
                    if success:
                        logger.info("Migrated Azure DevOps PAT to secure storage")
                        migrated = True
            
            # Future: Add migration for other providers
            
            return migrated
            
        except Exception as e:
            logger.error(f"Error during credential migration: {e}")
            return False
    
    def validate_credential(self, credential: Credential) -> bool:
        """
        Validate a credential (basic validation, not authentication test).
        
        Args:
            credential: The credential to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not credential.name:
            logger.error("Credential name is required")
            return False
        
        if not credential.token:
            logger.error("Credential token is required")
            return False
        
        # Provider-specific validation
        if credential.provider == Provider.AZURE_DEVOPS:
            # Azure DevOps PATs should be reasonable length
            if len(credential.token) < 20:
                logger.warning("Azure DevOps PAT seems too short")
        
        elif credential.provider == Provider.GITHUB:
            # GitHub tokens have specific prefixes
            if not any(credential.token.startswith(prefix) for prefix in ["ghp_", "ghs_", "ghr_"]):
                logger.warning("GitHub token doesn't match expected format")
        
        return True


# Singleton instance for convenience
_default_manager = None


def get_credential_manager() -> CredentialManager:
    """Get the default credential manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = CredentialManager()
    return _default_manager
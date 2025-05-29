"""
Utility functions for authentication and credential integration.

This module provides helper functions to integrate credential management
with the rest of the mgit application.
"""

import logging
from typing import Optional, Tuple

from mgit.auth import CredentialManager, Provider
from mgit.auth.manager import get_credential_manager
from mgit.config.manager import get_config_value

logger = logging.getLogger(__name__)


def get_azure_devops_credentials(
    organization_url: Optional[str] = None,
    pat: Optional[str] = None,
    credential_name: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get Azure DevOps credentials with the following priority:
    1. Provided arguments
    2. Secure credential storage (if credential_name provided)
    3. Environment variables
    4. Config file
    5. Default credential from secure storage
    
    Args:
        organization_url: Optional organization URL
        pat: Optional PAT
        credential_name: Optional credential name to retrieve from storage
        
    Returns:
        Tuple of (organization_url, pat)
    """
    # If both are provided as arguments, return them
    if organization_url and pat:
        return organization_url, pat
    
    # Try to get from credential storage if name provided
    if credential_name:
        manager = get_credential_manager()
        credential = manager.get_credential(Provider.AZURE_DEVOPS, credential_name)
        if credential:
            logger.debug(f"Using credential '{credential_name}' from secure storage")
            return credential.url or organization_url, credential.token
    
    # Get from config/env if not provided
    final_org = organization_url or get_config_value("AZURE_DEVOPS_ORG_URL")
    final_pat = pat or get_config_value("AZURE_DEVOPS_EXT_PAT")
    
    # If still no PAT, try default credential from storage
    if not final_pat and final_org:
        manager = get_credential_manager()
        # Try to find a credential for this URL
        credential = manager.get_credential_for_url(final_org)
        if credential:
            logger.debug(f"Using credential '{credential.name}' from secure storage for {final_org}")
            final_pat = credential.token
            if credential.url:
                final_org = credential.url
    
    return final_org, final_pat


def get_credential_for_repo_url(url: str) -> Optional[str]:
    """
    Get the appropriate credential (PAT/token) for a repository URL.
    
    Args:
        url: Repository URL
        
    Returns:
        The authentication token if found, None otherwise
    """
    manager = get_credential_manager()
    credential = manager.get_credential_for_url(url)
    
    if credential:
        logger.debug(f"Found credential '{credential.name}' for URL: {url}")
        return credential.token
    
    # Fallback to environment variable for backward compatibility
    provider = Provider.from_url(url)
    if provider == Provider.AZURE_DEVOPS:
        pat = get_config_value("AZURE_DEVOPS_EXT_PAT")
        if pat:
            logger.debug("Using PAT from environment/config for Azure DevOps")
            return pat
    
    return None


def migrate_existing_credentials():
    """
    Migrate credentials from environment/config to secure storage.
    
    This should be called on application startup to help users
    transition to secure credential storage.
    """
    try:
        from mgit.config.manager import load_config_file
        
        config_values = load_config_file()
        manager = get_credential_manager()
        
        # Only attempt migration if there are credentials in config
        if "AZURE_DEVOPS_EXT_PAT" in config_values:
            if manager.migrate_from_config(config_values):
                logger.info("Successfully migrated credentials to secure storage")
                logger.info("Consider removing PAT values from config files for security")
    except Exception as e:
        # Don't fail the application if migration fails
        logger.debug(f"Credential migration check failed: {e}")


def embed_credentials_in_url(url: str, credential: Optional[str] = None) -> str:
    """
    Embed credentials in a git URL if available.
    
    Args:
        url: The repository URL
        credential: Optional credential to use (will auto-detect if not provided)
        
    Returns:
        URL with embedded credentials if available
    """
    if not credential:
        credential = get_credential_for_repo_url(url)
    
    if credential:
        provider = Provider.from_url(url)
        
        if provider == Provider.AZURE_DEVOPS:
            # Use the existing embed_pat_in_url function
            from mgit.git import embed_pat_in_url
            return embed_pat_in_url(url, credential)
        
        elif provider == Provider.GITHUB:
            # GitHub uses token as username
            if "github.com" in url:
                if url.startswith("https://"):
                    return url.replace("https://", f"https://{credential}@")
                
        elif provider == Provider.BITBUCKET:
            # BitBucket might need username:password format
            # For now, just use token
            if "bitbucket.org" in url:
                if url.startswith("https://"):
                    return url.replace("https://", f"https://x-token-auth:{credential}@")
    
    return url
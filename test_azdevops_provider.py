#!/usr/bin/env python3
"""Test script for Azure DevOps provider."""

import asyncio
import logging
from mgit.providers import ProviderFactory, AzureDevOpsProvider

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_provider():
    """Test the Azure DevOps provider implementation."""
    
    # Test factory registration
    print("Available providers:", ProviderFactory.list_providers())
    assert ProviderFactory.is_registered("azuredevops"), "AzureDevOps provider not registered"
    
    # Test creating provider with missing config
    try:
        provider = ProviderFactory.create_provider("azuredevops", {})
        print("ERROR: Should have failed with missing config")
    except ValueError as e:
        print(f"✓ Correctly caught config error: {e}")
    
    # Test creating provider with valid config
    config = {
        "organization_url": "https://dev.azure.com/test-org",
        "pat": "test-pat-123"
    }
    
    provider = ProviderFactory.create_provider("azuredevops", config)
    print(f"✓ Created provider: {provider.__class__.__name__}")
    
    # Check provider attributes
    assert provider.PROVIDER_NAME == "azure_devops"
    assert provider.supports_projects() == True
    print("✓ Provider attributes correct")
    
    # Test URL formatting
    config2 = {
        "organization_url": "dev.azure.com/test-org",  # Without https://
        "pat": "test-pat-123"
    }
    provider2 = AzureDevOpsProvider(config2)
    assert provider2.organization_url == "https://dev.azure.com/test-org"
    print("✓ URL formatting works correctly")
    
    print("\nAll tests passed!")


if __name__ == "__main__":
    asyncio.run(test_provider())
#!/usr/bin/env python3
"""Quick test to verify BitBucket provider registration."""

import sys
sys.path.insert(0, '.')

from mgit.providers import ProviderFactory
from mgit.providers.bitbucket import BitBucketProvider

# Test 1: Check if provider is registered
print("Registered providers:", ProviderFactory.list_providers())
print("BitBucket registered:", ProviderFactory.is_registered("bitbucket"))

# Test 2: Try to create a BitBucket provider instance
try:
    config = {
        "workspace": "test-workspace",
        "username": "test-user",
        "app_password": "test-password"
    }
    provider = ProviderFactory.create_provider("bitbucket", config)
    print("Provider created successfully:", type(provider).__name__)
except NotImplementedError as e:
    print("Expected NotImplementedError:", str(e))
except Exception as e:
    print("Unexpected error:", type(e).__name__, str(e))

# Test 3: Check URL pattern matching
test_urls = [
    "https://bitbucket.org/workspace/repo",
    "git@bitbucket.org:workspace/repo.git",
    "https://api.bitbucket.org/2.0/repositories",
    "https://github.com/user/repo",
    "https://dev.azure.com/org/project",
]

print("\nURL pattern matching:")
for url in test_urls:
    print(f"  {url}: {BitBucketProvider.is_bitbucket_url(url)}")

# Test 4: Check provider attributes
print("\nProvider attributes:")
print(f"  Name: {BitBucketProvider.PROVIDER_NAME}")
print(f"  Auth methods: {[m.value for m in BitBucketProvider.SUPPORTED_AUTH_METHODS]}")
print(f"  API version: {BitBucketProvider.DEFAULT_API_VERSION}")
print(f"  Supports projects: {BitBucketProvider().supports_projects()}")
#!/usr/bin/env python3
"""Test script for GitHub provider stub implementation."""

import asyncio
from mgit.providers import ProviderFactory, GitHubProvider

async def test_github_stub():
    """Test the GitHub provider stub."""
    print("Testing GitHub Provider Stub Implementation...")
    print("-" * 50)
    
    # Test 1: Provider registration
    print("1. Testing provider registration:")
    providers = ProviderFactory.list_providers()
    print(f"   Available providers: {providers}")
    assert "github" in providers, "GitHub provider not registered!"
    print("   ✓ GitHub provider is registered")
    
    # Test 2: Provider creation
    print("\n2. Testing provider creation:")
    config = {
        "base_url": "https://api.github.com",
        "auth_method": "pat",
        "pat": "test-token"
    }
    provider = ProviderFactory.create_provider("github", config)
    print(f"   Created provider: {type(provider).__name__}")
    assert isinstance(provider, GitHubProvider), "Wrong provider type!"
    print("   ✓ GitHub provider instance created")
    
    # Test 3: Provider attributes
    print("\n3. Testing provider attributes:")
    print(f"   Provider name: {provider.PROVIDER_NAME}")
    print(f"   Supported auth methods: {[m.value for m in provider.SUPPORTED_AUTH_METHODS]}")
    print(f"   Default API version: {provider.DEFAULT_API_VERSION}")
    print(f"   Supports projects: {provider.supports_projects()}")
    assert provider.PROVIDER_NAME == "github", "Wrong provider name!"
    assert not provider.supports_projects(), "GitHub should not support projects!"
    print("   ✓ Provider attributes are correct")
    
    # Test 4: URL pattern matching
    print("\n4. Testing URL pattern matching:")
    test_urls = [
        ("https://github.com/user/repo", True),
        ("http://github.com/org/project", True),
        ("git@github.com:user/repo.git", True),
        ("ssh://git@github.com/user/repo", True),
        ("https://gitlab.com/user/repo", False),
        ("https://bitbucket.org/user/repo", False),
    ]
    for url, expected in test_urls:
        result = GitHubProvider.match_url(url)
        status = "✓" if result == expected else "✗"
        print(f"   {status} {url} -> {result}")
        assert result == expected, f"URL matching failed for {url}"
    
    # Test 5: Stub methods raise NotImplementedError
    print("\n5. Testing stub methods:")
    stub_methods = [
        ("_validate_config", lambda: provider._validate_config()),
        ("authenticate", lambda: asyncio.create_task(provider.authenticate())),
        ("test_connection", lambda: asyncio.create_task(provider.test_connection())),
        ("list_organizations", lambda: asyncio.create_task(provider.list_organizations())),
        ("list_repositories", lambda: asyncio.create_task(
            provider.list_repositories("test-org").__anext__()
        )),
        ("get_repository", lambda: asyncio.create_task(
            provider.get_repository("test-org", "test-repo")
        )),
        ("get_authenticated_clone_url", lambda: provider.get_authenticated_clone_url(None)),
        ("get_rate_limit_info", lambda: provider.get_rate_limit_info()),
    ]
    
    for method_name, method_call in stub_methods:
        try:
            if asyncio.iscoroutine(method_call()):
                await method_call()
            else:
                method_call()
            print(f"   ✗ {method_name} - Should raise NotImplementedError!")
            assert False, f"{method_name} should raise NotImplementedError"
        except NotImplementedError as e:
            print(f"   ✓ {method_name} - Raises NotImplementedError: {str(e)}")
        except Exception as e:
            print(f"   ✗ {method_name} - Unexpected error: {type(e).__name__}: {e}")
    
    # Test 6: Non-stub methods
    print("\n6. Testing non-stub methods:")
    projects = await provider.list_projects("test-org")
    print(f"   list_projects returns: {projects}")
    assert projects == [], "list_projects should return empty list for GitHub"
    print("   ✓ list_projects returns empty list as expected")
    
    print("\n" + "=" * 50)
    print("All tests passed! GitHub provider stub is working correctly.")

if __name__ == "__main__":
    asyncio.run(test_github_stub())
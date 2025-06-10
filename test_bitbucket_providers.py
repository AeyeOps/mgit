#!/usr/bin/env python3
"""
Test script for BitBucket provider configurations.
Tests both bitbucket_pdi and bitbucket_p97 configurations.
"""

import asyncio
import sys
from typing import List, Dict, Any
from mgit.config.yaml_manager import get_provider_config
from mgit.providers.bitbucket import BitBucketProvider


async def test_bitbucket_provider(name: str) -> Dict[str, Any]:
    """Test a single BitBucket provider configuration."""
    print(f"\n{'='*60}")
    print(f"Testing BitBucket Provider: {name}")
    print(f"{'='*60}")
    
    try:
        # Load configuration
        config = get_provider_config(name)
        print(f"Configuration loaded:")
        print(f"  User: {config.get('user', 'Not set')}")
        print(f"  URL: {config.get('url', 'Not set')}")
        print(f"  Workspace: {config.get('workspace', 'Not set')}")
        
        # Create provider instance
        provider = BitBucketProvider(config)
        print(f"  Provider instance created successfully")
        
        # Test authentication
        print(f"\nTesting authentication...")
        is_authenticated = await provider.authenticate()
        if not is_authenticated:
            print(f"  ❌ Authentication failed")
            return {"success": False, "error": "Authentication failed"}
        print(f"  ✅ Authentication successful")
        
        # List organizations/workspaces
        print(f"\nListing workspaces...")
        organizations = await provider.list_organizations()
        print(f"  Found {len(organizations)} workspace(s):")
        for i, org in enumerate(organizations, 1):
            print(f"    {i}. {org.name}")
            print(f"       URL: {org.url}")
        
        if not organizations:
            print(f"  ⚠️  No workspaces found")
            return {"success": True, "workspaces": 0, "repositories": 0}
        
        # List repositories from first workspace
        first_workspace = organizations[0]
        print(f"\nListing repositories from workspace '{first_workspace.name}'...")
        
        # Collect repositories from async iterator
        repositories = []
        repo_count = 0
        async for repo in provider.list_repositories(first_workspace.name):
            repositories.append(repo)
            repo_count += 1
            # Stop after 3 repositories for testing
            if repo_count >= 3:
                break
        
        print(f"  Found {repo_count}+ repositories (showing first {len(repositories)}):")
        
        for i, repo in enumerate(repositories, 1):
            print(f"    {i}. {repo.name}")
            print(f"       URL: {repo.clone_url}")
            print(f"       Description: {repo.description or 'No description'}")
            print()
        
        return {
            "success": True,
            "workspaces": len(organizations),
            "repositories": len(repositories),
            "workspace_name": first_workspace.name
        }
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return {"success": False, "error": str(e)}


async def main():
    """Main test function."""
    print("BitBucket Provider Configuration Test")
    print("====================================")
    
    providers = ['bitbucket_pdi', 'bitbucket_p97']
    results = {}
    
    for provider_name in providers:
        try:
            result = await test_bitbucket_provider(provider_name)
            results[provider_name] = result
        except Exception as e:
            print(f"❌ Failed to test {provider_name}: {str(e)}")
            results[provider_name] = {"success": False, "error": str(e)}
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    for provider_name, result in results.items():
        status = "✅ SUCCESS" if result.get("success") else "❌ FAILED"
        print(f"\n{provider_name}: {status}")
        
        if result.get("success"):
            print(f"  Workspaces: {result.get('workspaces', 0)}")
            print(f"  Repositories: {result.get('repositories', 0)}")
            if result.get('workspace_name'):
                print(f"  Primary workspace: {result.get('workspace_name')}")
        else:
            print(f"  Error: {result.get('error', 'Unknown error')}")
    
    # Overall status
    successful_providers = sum(1 for r in results.values() if r.get("success"))
    total_providers = len(results)
    
    print(f"\nOverall: {successful_providers}/{total_providers} providers working correctly")
    
    if successful_providers == total_providers:
        print("🎉 All BitBucket providers are configured and working!")
    else:
        print("⚠️  Some BitBucket providers need attention")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {str(e)}")
        sys.exit(1)
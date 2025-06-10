#!/usr/bin/env python3
"""
GitHub Provider Configuration Summary Test

Tests all GitHub providers and shows a concise summary of results.
"""

import asyncio
import sys
from typing import List, Dict

from mgit.config.yaml_manager import get_provider_config
from mgit.providers.github import GitHubProvider


async def test_provider_summary(name: str) -> Dict:
    """Test a provider and return summary info."""
    result = {
        "name": name,
        "status": "❌ ERROR",
        "user": "",
        "organizations": 0,
        "first_org": "",
        "repositories": 0,
        "error": None
    }
    
    try:
        # Load config and create provider
        config = get_provider_config(name)
        provider = GitHubProvider(config)
        result["user"] = provider.user
        
        # Test authentication
        if not await provider.authenticate():
            result["error"] = "Authentication failed"
            return result
            
        # List organizations
        organizations = await provider.list_organizations()
        result["organizations"] = len(organizations)
        
        if organizations:
            result["first_org"] = organizations[0].name
            
            # Count repositories in first org
            repo_count = 0
            async for repo in provider.list_repositories(organizations[0].name):
                repo_count += 1
                if repo_count >= 10:  # Limit for testing
                    break
            result["repositories"] = repo_count
        
        result["status"] = "✅ SUCCESS"
        
        # Cleanup
        await provider.cleanup()
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def main():
    """Test all GitHub providers and show summary."""
    print("🔍 GitHub Provider Configuration Summary")
    print("=" * 80)
    
    providers = ['github_pdi', 'github_aeyeops', 'github_steveant', 'github_gasbuddy']
    results = []
    
    # Test all providers
    for provider_name in providers:
        print(f"Testing {provider_name}...", end=" ", flush=True)
        result = await test_provider_summary(provider_name)
        results.append(result)
        print("Done" if result["status"] == "✅ SUCCESS" else f"Failed - {result['error']}")
    
    # Display summary table
    print("\n📊 RESULTS SUMMARY")
    print("=" * 80)
    print(f"{'Provider':<20} {'Status':<12} {'User':<15} {'Orgs':<6} {'First Org':<20} {'Repos':<6}")
    print("-" * 80)
    
    for result in results:
        first_org = result["first_org"][:18] + ".." if len(result["first_org"]) > 18 else result["first_org"]
        
        print(f"{result['name']:<20} "
              f"{result['status']:<12} "
              f"{result['user']:<15} "
              f"{result['organizations']:<6} "
              f"{first_org:<20} "
              f"{result['repositories']:<6}")
    
    # Count successes
    successful = sum(1 for r in results if r["status"] == "✅ SUCCESS")
    
    print("\n" + "=" * 80)
    print(f"Overall Result: {successful}/{len(providers)} providers working correctly")
    
    if successful == len(providers):
        print("🎉 All GitHub providers are configured and working!")
        return 0
    else:
        print("⚠️  Some providers have configuration issues")
        # Show errors
        for result in results:
            if result["error"]:
                print(f"   {result['name']}: {result['error']}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
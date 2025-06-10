#!/usr/bin/env python3
"""
Test script for GitHub provider configurations.

Tests all GitHub configurations in ~/.config/mgit/config.yaml:
- github_pdi
- github_aeyeops  
- github_steveant
- github_gasbuddy

For each provider:
1. Load configuration
2. Create provider instance
3. Test authentication
4. List organizations
5. List first 3 repositories from first organization
"""

import asyncio
import sys
from typing import List

from mgit.config.yaml_manager import get_provider_config
from mgit.providers.github import GitHubProvider


async def test_github_provider(name: str) -> dict:
    """Test a single GitHub provider configuration.
    
    Args:
        name: Provider configuration name
        
    Returns:
        Dict with test results
    """
    print(f"\n{'='*60}")
    print(f"Testing GitHub Provider: {name}")
    print(f"{'='*60}")
    
    result = {
        "name": name,
        "config_loaded": False,
        "provider_created": False,
        "authenticated": False,
        "organizations": [],
        "repositories": [],
        "error": None
    }
    
    try:
        # 1. Load configuration
        print(f"📁 Loading configuration for '{name}'...")
        config = get_provider_config(name)
        result["config_loaded"] = True
        
        # Show config (mask sensitive data)
        config_display = config.copy()
        if "token" in config_display:
            token = config_display["token"]
            config_display["token"] = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else "***"
        print(f"   Config: {config_display}")
        
        # Show all config keys for debugging
        print(f"   Available config keys: {list(config.keys())}")
        
        # 2. Create provider instance
        print(f"🔧 Creating GitHub provider instance...")
        provider = GitHubProvider(config)
        result["provider_created"] = True
        print(f"   URL: {provider.url}")
        print(f"   User: {provider.user}")
        
        # 3. Test authentication
        print(f"🔐 Testing authentication...")
        auth_success = await provider.authenticate()
        result["authenticated"] = auth_success
        
        if not auth_success:
            result["error"] = "Authentication failed"
            print(f"   ❌ Authentication failed")
            return result
            
        print(f"   ✅ Authentication successful")
        
        # 4. List organizations
        print(f"🏢 Listing organizations...")
        organizations = await provider.list_organizations()
        result["organizations"] = [{"name": org.name, "url": org.url} for org in organizations]
        
        if not organizations:
            print(f"   ⚠️  No organizations found")
            return result
            
        print(f"   Found {len(organizations)} organizations:")
        for org in organizations:
            org_type = org.metadata.get("type", "Organization")
            print(f"     • {org.name} ({org_type})")
        
        # 5. List repositories from first organization
        if organizations:
            first_org = organizations[0]
            print(f"📚 Listing repositories from '{first_org.name}'...")
            
            repo_count = 0
            async for repo in provider.list_repositories(first_org.name):
                if repo_count >= 3:  # Limit to first 3 repos
                    break
                    
                result["repositories"].append({
                    "name": repo.name,
                    "clone_url": repo.clone_url,
                    "private": repo.is_private,
                    "language": repo.metadata.get("language"),
                    "description": repo.description
                })
                
                privacy = "🔒 Private" if repo.is_private else "🌐 Public"
                language = repo.metadata.get("language", "N/A")
                description = repo.description[:50] + "..." if repo.description and len(repo.description) > 50 else repo.description or "No description"
                
                print(f"     • {repo.name} ({privacy}, {language})")
                print(f"       {description}")
                
                repo_count += 1
            
            if repo_count == 0:
                print(f"   ⚠️  No repositories found in '{first_org.name}'")
            else:
                print(f"   Listed {repo_count} repositories")
        
        # Clean up
        await provider.cleanup()
        
        print(f"✅ Test completed successfully for '{name}'")
        
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ Error testing '{name}': {e}")
        
        # Try to clean up provider if it was created
        try:
            if "provider" in locals():
                await provider.cleanup()
        except:
            pass
    
    return result


async def main():
    """Test all GitHub provider configurations."""
    print("🚀 GitHub Provider Configuration Test")
    print("=" * 60)
    
    # List of GitHub providers to test
    providers = ['github_pdi', 'github_aeyeops', 'github_steveant', 'github_gasbuddy']
    
    results = []
    
    for provider_name in providers:
        try:
            result = await test_github_provider(provider_name)
            results.append(result)
        except KeyboardInterrupt:
            print(f"\n⚠️  Test interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error testing {provider_name}: {e}")
            results.append({
                "name": provider_name,
                "config_loaded": False,
                "provider_created": False,
                "authenticated": False,
                "organizations": [],
                "repositories": [],
                "error": str(e)
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    successful_tests = 0
    
    for result in results:
        name = result["name"]
        if result["error"]:
            status = f"❌ FAILED - {result['error']}"
        elif result["authenticated"]:
            status = f"✅ SUCCESS - {len(result['organizations'])} orgs, {len(result['repositories'])} repos"
            successful_tests += 1
        else:
            status = "⚠️  PARTIAL - Config loaded but auth failed"
        
        print(f"{name:20} | {status}")
    
    print(f"\nResults: {successful_tests}/{len(providers)} providers working correctly")
    
    if successful_tests == len(providers):
        print("🎉 All GitHub providers are working!")
        return 0
    else:
        print("⚠️  Some providers have issues - check configuration")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
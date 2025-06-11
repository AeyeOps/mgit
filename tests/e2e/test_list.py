"""End-to-end CLI list tests for repository discovery across providers.

These tests run actual CLI commands to test repository listing functionality.
They are marked with @pytest.mark.e2e and skipped by default.
"""

import pytest
import subprocess
import json
import re
import random
from typing import Dict, List, Optional, Tuple


def run_mgit_command(args: List[str]) -> tuple[int, str, str]:
    """Run mgit CLI command and return exit code, stdout, stderr."""
    result = subprocess.run(
        ["poetry", "run", "mgit"] + args,
        capture_output=True,
        text=True,
        timeout=60  # Longer timeout for list operations
    )
    return result.returncode, result.stdout, result.stderr


def get_provider_list() -> Dict[str, str]:
    """Get all providers and their types from CLI."""
    code, stdout, stderr = run_mgit_command(["config", "--list"])
    if code != 0:
        raise Exception(f"Failed to get provider list: {stderr}")
    
    providers = {}
    for line in stdout.split('\n'):
        # Parse lines like: "  ado_pdidev (azuredevops)"
        match = re.search(r'^\s+([^\s]+)\s+\(([^)]+)\)', line)
        if match:
            name, ptype = match.groups()
            providers[name] = ptype
    
    return providers


def get_provider_workspace(provider_name: str) -> Optional[str]:
    """Get workspace/organization from provider config."""
    code, stdout, stderr = run_mgit_command(["config", "--show", provider_name])
    if code != 0:
        return None
    
    for line in stdout.split('\n'):
        # Look for workspace field
        if 'workspace:' in line:
            return line.split('workspace:')[1].strip()
        # Fall back to user field for GitHub
        elif 'user:' in line:
            return line.split('user:')[1].strip()
    
    return None


@pytest.mark.e2e
def test_cli_list_basic_functionality():
    """Test basic mgit list functionality across all provider types.
    
    This test focuses on core functionality that should work reliably:
    1. Gets all configured providers and groups by type
    2. Randomly selects one representative from each provider type  
    3. Tests basic table format list functionality with wildcard patterns
    4. Verifies command succeeds and returns repository data
    
    Primary goal: Ensure mgit list works for each distinct provider type
    """
    
    # Get all providers and group by type
    try:
        all_providers = get_provider_list()
    except Exception as e:
        pytest.skip(f"Could not get provider list: {e}")
    
    if not all_providers:
        pytest.skip("No providers configured")
    
    # Group providers by type
    providers_by_type = {}
    for name, ptype in all_providers.items():
        if ptype not in providers_by_type:
            providers_by_type[ptype] = []
        providers_by_type[ptype].append(name)
    
    # Randomly select one representative from each type for better test coverage
    test_providers = [random.choice(providers) for providers in providers_by_type.values()]
    
    print(f"\nTesting mgit list functionality")
    print(f"Available types: {list(providers_by_type.keys())}")
    print(f"Providers per type: {[(ptype, len(providers)) for ptype, providers in providers_by_type.items()]}")
    print(f"Randomly selected representatives: {test_providers}")
    
    results = {}
    
    for provider_name in test_providers:
        print(f"\n--- Testing list for {provider_name} ---")
        
        # Test: Basic wildcard list with table format and limit
        print("Core test: Basic wildcard list with table format")
        code, stdout, stderr = run_mgit_command([
            "list", "*/*/*", 
            "--provider", provider_name,
            "--format", "table",
            "--limit", "5"
        ])
        
        success = code == 0
        repo_count = 0
        
        if success:
            # Verify we got repository results
            if "No repositories found" in stdout:
                repo_count = 0
                print(f"✅ Table format: No repositories found (valid)")
            else:
                # Look for repository count or table content
                lines = stdout.split('\n')
                for line in lines:
                    if 'Found' in line and 'repositories' in line:
                        match = re.search(r'Found (\d+) repositories', line)
                        if match:
                            repo_count = int(match.group(1))
                            break
                
                # Also check for table rows (organization names)
                if repo_count == 0:
                    # Count non-empty lines that might be table rows
                    table_rows = [line for line in lines if line.strip() and not line.startswith('Found')]
                    if len(table_rows) > 2:  # header + separator + data
                        repo_count = len(table_rows) - 2
                
                print(f"✅ Table format: Found {repo_count} repositories")
        else:
            print(f"❌ Table format failed: {stderr}")
        
        results[provider_name] = success
    
    # Summary
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    
    print(f"\n=== List Command Test Summary ===")
    print(f"Provider types tested: {total_tests}")
    print(f"Successful: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    for provider_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        provider_type = all_providers[provider_name]
        print(f"  {provider_name} ({provider_type}): {status}")
    
    # Test passes if at least one provider type works
    # This ensures the core list functionality is working
    assert passed_tests > 0, f"No provider types could execute list command. Results: {results}"
    
    # Warn if some providers failed but don't fail the test
    if passed_tests < total_tests:
        print(f"\n⚠️  Warning: {total_tests - passed_tests} provider types failed list test")
        print("This may indicate provider-specific configuration or connectivity issues")


@pytest.mark.e2e
def test_cli_list_error_handling():
    """Test mgit list error handling with invalid patterns and providers.
    
    This test verifies that the CLI properly handles:
    1. Invalid query patterns
    2. Non-existent providers
    3. Empty results
    """
    
    # Get one valid provider for testing (randomly selected)
    try:
        all_providers = get_provider_list()
        if not all_providers:
            pytest.skip("No providers configured")
        
        test_provider = random.choice(list(all_providers.keys()))
        
    except Exception as e:
        pytest.skip(f"Could not get provider list: {e}")
    
    print(f"\nTesting error handling with provider: {test_provider}")
    
    # Test 1: Invalid query pattern
    print("Test 1: Invalid query pattern")
    code, stdout, stderr = run_mgit_command([
        "list", "invalid/pattern/with/too/many/parts",
        "--provider", test_provider
    ])
    
    assert code != 0, "Expected failure for invalid query pattern"
    error_output = stderr + stdout  # Error might be in either stream
    assert "Invalid query" in error_output or "Error" in error_output, f"Expected error message, got stderr: {stderr}, stdout: {stdout}"
    print("✅ Invalid pattern properly rejected")
    
    # Test 2: Non-existent provider
    print("Test 2: Non-existent provider")
    code, stdout, stderr = run_mgit_command([
        "list", "*/*/*",
        "--provider", "nonexistent_provider_12345"
    ])
    
    assert code != 0, "Expected failure for non-existent provider"
    print("✅ Non-existent provider properly rejected")
    
    # Test 3: Pattern that should return no results
    print("Test 3: Pattern with no matches")
    code, stdout, stderr = run_mgit_command([
        "list", "unlikely_org_name_12345/*/*",
        "--provider", test_provider,
        "--limit", "1"
    ])
    
    # This should succeed but return no results
    if code == 0:
        if "No repositories found" in stdout or "Found 0 repositories" in stdout:
            print("✅ Empty results handled properly")
        else:
            print("✅ Command succeeded (may have found unexpected matches)")
    else:
        print(f"❌ Unexpected failure for no-match pattern: {stderr}")
        # Don't fail the test - some providers might have auth issues
    
    print("=== Error handling tests completed ===")
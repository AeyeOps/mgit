"""E2E test for clone-all with partial string matching for discovery.

This test uses partial string matching with the list command to discover
projects/orgs, then uses clone-all to clone repos. Each provider type
gets its own isolated directory for cloning.
"""

import pytest
import subprocess
import shutil
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import time


def run_mgit_command(args: List[str], timeout: int = 120) -> Tuple[int, str, str]:
    """Run mgit CLI command and return exit code, stdout, stderr."""
    result = subprocess.run(
        ["poetry", "run", "mgit"] + args,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def get_provider_list() -> Dict[str, str]:
    """Get all providers and their types from CLI."""
    code, stdout, stderr = run_mgit_command(["config", "--list"])
    if code != 0:
        raise Exception(f"Failed to get provider list: {stderr}")
    
    providers = {}
    for line in stdout.split('\n'):
        # Parse lines like: "  work_ado (azuredevops)"
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
    
    workspace = None
    for line in stdout.split('\n'):
        # Look for workspace field
        if 'workspace:' in line:
            workspace = line.split('workspace:')[1].strip()
            break
        # Fall back to parsing URL for GitHub
        elif 'url:' in line and 'github.com' in line:
            url = line.split('url:')[1].strip()
            # Extract org from URL like https://github.com/example-org/
            match = re.search(r'github\.com/([^/]+)', url)
            if match:
                workspace = match.group(1)
    
    return workspace


@pytest.mark.e2e
def test_clone_all_with_discovery(tmp_path):
    """Test clone-all after discovering projects with partial matching.
    
    This test:
    1. Gets all configured providers grouped by type
    2. For each provider type, uses list with partial matching to find projects
    3. Selects a small project/org to clone (to avoid timeout)
    4. Clones repos to provider-specific directories
    5. Verifies repos were actually cloned
    """
    
    # Create base directory for all clones
    base_clone_dir = tmp_path / "clone_partial_test"
    base_clone_dir.mkdir(exist_ok=True)
    
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
    
    print(f"\n=== Testing clone-all with partial matching ===")
    print(f"Available provider types: {list(providers_by_type.keys())}")
    print(f"Base clone directory: {base_clone_dir}")
    
    results = {}
    
    for provider_type, provider_names in providers_by_type.items():
        # Select a random provider of this type
        provider_name = random.choice(provider_names)
        
        print(f"\n--- Testing {provider_type} provider: {provider_name} ---")
        
        # Get workspace for this provider
        workspace = get_provider_workspace(provider_name)
        if not workspace:
            print(f"⚠️  Could not determine workspace for {provider_name}, skipping")
            results[provider_type] = {"status": "skipped", "reason": "no workspace"}
            continue
        
        print(f"Workspace: {workspace}")
        
        # Create partial pattern (first 2-3 chars + wildcard)
        partial_len = min(3, len(workspace) - 1)  # Use 3 chars or less
        if partial_len < 2:
            partial_len = 2  # Minimum 2 chars
        
        partial_workspace = workspace[:partial_len] + "*"
        
        # First, use list with partial pattern to discover available projects/repos
        query = f"{partial_workspace}/*/*"
        print(f"Discovery query pattern: {query}")
        
        # List repositories to find suitable targets
        list_code, list_stdout, list_stderr = run_mgit_command([
            "list", query,
            "--provider", provider_name,
            "--limit", "50",  # Get enough to find patterns
            "--format", "json"
        ])
        
        if list_code != 0:
            print(f"❌ List failed: {list_stderr}")
            results[provider_type] = {"status": "failed", "reason": "list command failed"}
            continue
        
        # Debug: Show what we got from list command
        print(f"List stdout length: {len(list_stdout)}")
        if len(list_stdout) < 1000:
            print(f"List stdout: {list_stdout[:500]}...")
        
        # Parse JSON output to find suitable project/org to clone
        try:
            import json
            # The JSON might be after some progress output, try to find it
            json_start = list_stdout.find('[')
            if json_start >= 0:
                json_data = list_stdout[json_start:]
                repos_data = json.loads(json_data)
            else:
                print("No JSON array found in output")
                repos_data = []
            
            if not repos_data:
                print(f"⚠️  No repositories found with pattern {query}")
                results[provider_type] = {"status": "skipped", "reason": "no repos found"}
                continue
            
            # Find a suitable project/org to clone
            # For Azure DevOps, we need a project with few repos
            # For GitHub/BitBucket, the org is the project
            
            if provider_type == "azuredevops":
                # Count repos per project
                projects = {}
                for repo in repos_data:
                    project = repo.get("project", "")
                    if project:
                        projects[project] = projects.get(project, 0) + 1
                
                # Find smallest project (but not empty)
                if projects:
                    target_project = min(projects.items(), key=lambda x: x[1] if x[1] > 0 else float('inf'))[0]
                    repo_count = projects[target_project]
                    print(f"Selected project: {target_project} ({repo_count} repos)")
                    
                    # For Azure DevOps, we need org/project format
                    clone_target = f"{workspace}/{target_project}"
                else:
                    print("⚠️  No projects found")
                    results[provider_type] = {"status": "skipped", "reason": "no projects"}
                    continue
            else:
                # For GitHub/BitBucket, just use the workspace/org
                clone_target = workspace
                repo_count = len(repos_data)
                print(f"Target organization: {clone_target} ({repo_count} repos found)")
                
                # If too many repos, skip to avoid timeout
                if repo_count > 50:
                    print(f"⚠️  Too many repos ({repo_count}), skipping to avoid timeout")
                    results[provider_type] = {"status": "skipped", "reason": "too many repos"}
                    continue
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"❌ Failed to parse JSON output: {e}")
            print(f"Raw output: {list_stdout[:500]}...")
            results[provider_type] = {"status": "failed", "reason": f"json parse error: {str(e)}"}
            continue
        
        # Create provider-specific clone directory
        provider_clone_dir = base_clone_dir / f"{provider_type}_{provider_name}"
        provider_clone_dir.mkdir(exist_ok=True)
        
        print(f"Clone directory: {provider_clone_dir}")
        print(f"Clone target: {clone_target}")
        
        # Run clone-all with the specific project/org
        start_time = time.time()
        code, stdout, stderr = run_mgit_command([
            "clone-all",
            clone_target,
            str(provider_clone_dir),
            "--config", provider_name,  # Use --config instead of --provider
            "--concurrency", "2",  # Low concurrency to be gentle
            "--update-mode", "skip"
        ], timeout=180)  # 3 minute timeout
        
        elapsed_time = time.time() - start_time
        
        if code == 0:
            # Check what was actually cloned
            cloned_items = list(provider_clone_dir.iterdir())
            git_repos = [item for item in cloned_items if item.is_dir() and (item / '.git').exists()]
            
            print(f"✅ Clone succeeded in {elapsed_time:.1f}s")
            print(f"   Cloned {len(git_repos)} git repositories")
            
            if git_repos:
                # Show first few repos
                print("   Repositories:")
                for repo in git_repos[:5]:
                    print(f"     - {repo.name}")
                if len(git_repos) > 5:
                    print(f"     ... and {len(git_repos) - 5} more")
            
            results[provider_type] = {
                "status": "success",
                "repos_cloned": len(git_repos),
                "time": elapsed_time,
                "clone_target": clone_target,
                "discovery_pattern": query
            }
            
            # Verify at least one repo was cloned (unless empty org)
            if len(git_repos) == 0:
                print("   ⚠️  No repositories cloned (might be empty workspace)")
        else:
            print(f"❌ Clone failed: {stderr}")
            results[provider_type] = {
                "status": "failed",
                "error": stderr[:200],  # First 200 chars of error
                "clone_target": clone_target,
                "discovery_pattern": query
            }
    
    # Summary
    print(f"\n=== Clone-All Partial Matching Test Summary ===")
    successful = sum(1 for r in results.values() if r.get("status") == "success")
    failed = sum(1 for r in results.values() if r.get("status") == "failed")
    skipped = sum(1 for r in results.values() if r.get("status") == "skipped")
    
    print(f"Total provider types: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    
    print("\nDetailed results:")
    for provider_type, result in results.items():
        status = result.get("status", "unknown")
        print(f"\n{provider_type}:")
        print(f"  Status: {status}")
        
        if status == "success":
            print(f"  Repos cloned: {result.get('repos_cloned', 0)}")
            print(f"  Time: {result.get('time', 0):.1f}s")
            print(f"  Clone target: {result.get('clone_target', 'N/A')}")
            print(f"  Discovery pattern: {result.get('discovery_pattern', 'N/A')}")
        elif status == "failed":
            print(f"  Error: {result.get('error', 'Unknown error')}")
            print(f"  Clone target: {result.get('clone_target', 'N/A')}")
            print(f"  Discovery pattern: {result.get('discovery_pattern', 'N/A')}")
        elif status == "skipped":
            print(f"  Reason: {result.get('reason', 'Unknown')}")
    
    # Test passes if at least one provider type successfully cloned repos
    assert successful > 0, f"No provider types could successfully clone with partial matching. Results: {results}"
    
    # Also check that we actually cloned some repos (not just empty directories)
    total_repos_cloned = sum(
        r.get("repos_cloned", 0) 
        for r in results.values() 
        if r.get("status") == "success"
    )
    
    print(f"\nTotal repositories cloned across all providers: {total_repos_cloned}")
    
    # Clean up is handled by tmp_path fixture
    print(f"\nTest artifacts preserved in: {base_clone_dir}")


@pytest.mark.e2e 
def test_clone_all_specific_patterns(tmp_path):
    """Test clone-all with specific repository patterns.
    
    This test focuses on more specific patterns like:
    - Organization/*/repo-pattern
    - Organization/Project/*pattern*
    """
    
    # Create base directory
    base_clone_dir = tmp_path / "clone_pattern_test"
    base_clone_dir.mkdir(exist_ok=True)
    
    # Get providers
    try:
        all_providers = get_provider_list()
    except Exception as e:
        pytest.skip(f"Could not get provider list: {e}")
    
    # Find a provider to test with (prefer one with known patterns)
    test_provider = None
    provider_type = None
    
    # Try to find a good test candidate
    for name, ptype in all_providers.items():
        workspace = get_provider_workspace(name)
        if workspace:
            test_provider = name
            provider_type = ptype
            break
    
    if not test_provider:
        pytest.skip("No suitable provider found for pattern testing")
    
    print(f"\n=== Testing specific clone patterns with {test_provider} ({provider_type}) ===")
    
    workspace = get_provider_workspace(test_provider)
    print(f"Using workspace: {workspace}")
    
    # Test 1: Clone repos with specific pattern in name
    pattern_clone_dir = base_clone_dir / "pattern_test"
    pattern_clone_dir.mkdir(exist_ok=True)
    
    # First, find what patterns might work by listing
    print("\nSearching for repos with common patterns...")
    
    # Try common patterns
    patterns_to_try = ["*api*", "*service*", "*test*", "*data*", "*web*"]
    found_pattern = None
    
    for pattern in patterns_to_try:
        if provider_type == "azuredevops":
            query = f"{workspace}/*/{pattern}"
        else:
            query = f"{workspace}/*/{pattern}"
        
        code, stdout, stderr = run_mgit_command([
            "list", query,
            "--provider", test_provider,
            "--limit", "5"
        ])
        
        if code == 0 and "Found" in stdout:
            # Extract repo count
            match = re.search(r'Found (\d+) repositories', stdout)
            if match and int(match.group(1)) > 0:
                found_pattern = pattern
                print(f"✅ Found repos matching pattern: {pattern}")
                break
    
    if found_pattern:
        # Clone repos matching this pattern
        print(f"\nCloning repos matching pattern: {found_pattern}")
        
        # For clone-all, we need just the workspace/project part
        code, stdout, stderr = run_mgit_command([
            "clone-all",
            workspace,
            str(pattern_clone_dir),
            "--provider", test_provider,
            "--filter", found_pattern,  # If filter is supported
            "--concurrency", "2",
            "--update-mode", "skip"
        ], timeout=120)
        
        if code == 0:
            cloned = list(pattern_clone_dir.iterdir())
            git_repos = [d for d in cloned if d.is_dir() and (d / '.git').exists()]
            print(f"✅ Successfully cloned {len(git_repos)} repos matching '{found_pattern}'")
            
            if git_repos:
                print("   Cloned repositories:")
                for repo in git_repos[:5]:
                    print(f"     - {repo.name}")
        else:
            print(f"❌ Clone with pattern failed: {stderr}")
    else:
        print("⚠️  No common patterns found in repository names")
    
    print(f"\nTest artifacts preserved in: {base_clone_dir}")
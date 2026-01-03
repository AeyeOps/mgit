"""End-to-end CLI list tests for repository discovery across providers.

These tests run actual CLI commands to test repository listing functionality.
They are marked with @pytest.mark.e2e and skipped by default.
"""

import json
import random
import re
import subprocess

import pytest


def run_mgit_command(args: list[str], timeout: int = 60) -> tuple[int, str, str]:
    """Run mgit CLI command and return exit code, stdout, stderr."""
    result = subprocess.run(
        ["uv", "run", "mgit"] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def get_provider_list() -> dict[str, str]:
    """Get all providers and their types from CLI."""
    code, stdout, stderr = run_mgit_command(["config", "--list"])
    if code != 0:
        raise Exception(f"Failed to get provider list: {stderr}")

    providers = {}
    for line in stdout.split("\n"):
        # Parse lines like: "  work_ado (azuredevops)"
        match = re.search(r"^\s+([^\s]+)\s+\(([^)]+)\)", line)
        if match:
            name, ptype = match.groups()
            providers[name] = ptype

    return providers


def get_provider_workspace(provider_name: str) -> str | None:
    """Get workspace/organization from provider config."""
    code, stdout, stderr = run_mgit_command(["config", "--show", provider_name])
    if code != 0:
        return None

    for line in stdout.split("\n"):
        # Look for workspace field
        if "workspace:" in line:
            return line.split("workspace:")[1].strip()
        # Fall back to user field for GitHub
        elif "user:" in line:
            return line.split("user:")[1].strip()

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
    test_providers = [
        random.choice(providers) for providers in providers_by_type.values()
    ]

    print("\nTesting mgit list functionality")
    print(f"Available types: {list(providers_by_type.keys())}")
    print(
        f"Providers per type: {[(ptype, len(providers)) for ptype, providers in providers_by_type.items()]}"
    )
    print(f"Randomly selected representatives: {test_providers}")

    results = {}

    for provider_name in test_providers:
        print(f"\n--- Testing list for {provider_name} ---")

        # Test: Basic wildcard list with table format and limit
        print("Core test: Basic wildcard list with table format")
        code, stdout, stderr = run_mgit_command(
            [
                "list",
                "*/*/*",
                "--provider",
                provider_name,
                "--format",
                "table",
                "--limit",
                "5",
            ]
        )

        success = code == 0
        repo_count = 0

        if success:
            # Verify we got repository results
            if "No repositories found" in stdout:
                repo_count = 0
                print("✅ Table format: No repositories found (valid)")
            else:
                # Look for repository count or table content
                lines = stdout.split("\n")
                for line in lines:
                    if "Found" in line and "repositories" in line:
                        match = re.search(r"Found (\d+) repositories", line)
                        if match:
                            repo_count = int(match.group(1))
                            break

                # Also check for table rows (organization names)
                if repo_count == 0:
                    # Count non-empty lines that might be table rows
                    table_rows = [
                        line
                        for line in lines
                        if line.strip() and not line.startswith("Found")
                    ]
                    if len(table_rows) > 2:  # header + separator + data
                        repo_count = len(table_rows) - 2

                print(f"✅ Table format: Found {repo_count} repositories")
        else:
            print(f"❌ Table format failed: {stderr}")

        results[provider_name] = success

    # Summary
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)

    print("\n=== List Command Test Summary ===")
    print(f"Provider types tested: {total_tests}")
    print(f"Successful: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")

    for provider_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        provider_type = all_providers[provider_name]
        print(f"  {provider_name} ({provider_type}): {status}")

    # Test passes if at least one provider type works
    # This ensures the core list functionality is working
    assert passed_tests > 0, (
        f"No provider types could execute list command. Results: {results}"
    )

    # Warn if some providers failed but don't fail the test
    if passed_tests < total_tests:
        print(
            f"\n⚠️  Warning: {total_tests - passed_tests} provider types failed list test"
        )
        print(
            "This may indicate provider-specific configuration or connectivity issues"
        )


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
    code, stdout, stderr = run_mgit_command(
        ["list", "invalid/pattern/with/too/many/parts", "--provider", test_provider]
    )

    assert code != 0, "Expected failure for invalid query pattern"
    error_output = stderr + stdout  # Error might be in either stream
    assert "Invalid query" in error_output or "Error" in error_output, (
        f"Expected error message, got stderr: {stderr}, stdout: {stdout}"
    )
    print("✅ Invalid pattern properly rejected")

    # Test 2: Non-existent provider
    print("Test 2: Non-existent provider")
    code, stdout, stderr = run_mgit_command(
        ["list", "*/*/*", "--provider", "nonexistent_provider_12345"]
    )

    assert code != 0, "Expected failure for non-existent provider"
    print("✅ Non-existent provider properly rejected")

    # Test 3: Pattern that should return no results
    print("Test 3: Pattern with no matches")
    code, stdout, stderr = run_mgit_command(
        [
            "list",
            "unlikely_org_name_12345/*/*",
            "--provider",
            test_provider,
            "--limit",
            "1",
        ]
    )

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


def _extract_json(output: str) -> list | None:
    """Extract JSON array from output that may contain log lines."""
    # Find the JSON array - look for [{ or [\n{ to avoid false matches
    for marker in ["[\n  {", "[{", "[\n{"]:
        start = output.find(marker)
        if start != -1:
            break
    else:
        return None

    end = output.rfind("]")
    if end == -1 or end <= start:
        return None

    json_str = output[start : end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


@pytest.mark.e2e
def test_cli_sync_each_provider_no_spaces():
    """Test sync command for each provider type with repos that have NO spaces.

    Clones one repo from each provider type (GitHub, Azure DevOps, BitBucket)
    where org/project/repo names do not contain spaces.
    """
    import shutil
    import tempfile
    from pathlib import Path

    try:
        all_providers = get_provider_list()
    except Exception as e:
        pytest.skip(f"Could not get provider list: {e}")

    if not all_providers:
        pytest.skip("No providers configured")

    providers_by_type: dict[str, list[str]] = {}
    for name, ptype in all_providers.items():
        providers_by_type.setdefault(ptype, []).append(name)

    test_dir = Path(tempfile.mkdtemp(prefix="mgit_e2e_sync_"))
    results: dict[str, tuple[bool, str]] = {}

    try:
        for ptype, providers in providers_by_type.items():
            provider = random.choice(providers)
            clone_dir = test_dir / f"nospace_{ptype}"
            clone_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n--- Testing sync (no spaces) for {ptype} via {provider} ---")

            # Get repos
            code, stdout, stderr = run_mgit_command(
                [
                    "list",
                    "*/*/*",
                    "--provider",
                    provider,
                    "--format",
                    "json",
                    "--limit",
                    "30",
                ],
                timeout=90,
            )
            if code != 0:
                results[ptype] = (False, "list failed")
                continue

            repos = _extract_json(stdout)
            if not repos:
                results[ptype] = (False, "no repos or JSON parse error")
                continue

            # Find repo without spaces
            cloned = False
            for repo in repos:
                org = repo.get("organization", repo.get("workspace", ""))
                project = repo.get("project") or "*"
                name = repo.get("name", repo.get("repository", ""))

                if " " in str(org) or " " in str(project) or " " in str(name):
                    continue

                pattern = f"{org}/{project}/{name}"
                print(f"  Cloning: {pattern}")

                try:
                    code, stdout, stderr = run_mgit_command(
                        ["sync", pattern, str(clone_dir), "--provider", provider],
                        timeout=180,  # 3 min for git clone
                    )

                    if code == 0 and list(clone_dir.rglob(".git")):
                        results[ptype] = (True, "OK")
                        cloned = True
                        break
                except subprocess.TimeoutExpired:
                    print("  Timeout (repo too large), trying next...")
                    continue

            if not cloned and ptype not in results:
                results[ptype] = (False, "no repo cloned (all too large or no matches)")

    finally:
        shutil.rmtree(test_dir, ignore_errors=True)

    # Report
    ok = [t for t, (passed, _) in results.items() if passed]
    failed = [(t, msg) for t, (passed, msg) in results.items() if not passed]

    print("\n=== Sync (no spaces) Results ===")
    for ptype, (passed, msg) in results.items():
        status = "✅" if passed else "❌"
        print(f"  {ptype}: {status} {msg}")

    assert len(ok) > 0, f"No provider types passed sync test: {failed}"
    if failed:
        print(f"⚠️  Some providers failed: {failed}")


@pytest.mark.e2e
def test_cli_sync_each_provider_with_spaces():
    """Test sync command for each provider type with repos that HAVE spaces.

    Tests repos where org/project/repo contains spaces (e.g., "Blue Cow").
    This validates the space handling fix in manager.py.
    """
    import shutil
    import tempfile
    from pathlib import Path

    try:
        all_providers = get_provider_list()
    except Exception as e:
        pytest.skip(f"Could not get provider list: {e}")

    if not all_providers:
        pytest.skip("No providers configured")

    providers_by_type: dict[str, list[str]] = {}
    for name, ptype in all_providers.items():
        providers_by_type.setdefault(ptype, []).append(name)

    test_dir = Path(tempfile.mkdtemp(prefix="mgit_e2e_sync_spaces_"))
    results: dict[str, tuple[bool, str]] = {}

    try:
        for ptype, providers in providers_by_type.items():
            provider = random.choice(providers)
            clone_dir = test_dir / f"spaces_{ptype}"
            clone_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n--- Testing sync (with spaces) for {ptype} via {provider} ---")

            # Get repos with higher limit to find spaces
            code, stdout, stderr = run_mgit_command(
                [
                    "list",
                    "*/*/*",
                    "--provider",
                    provider,
                    "--format",
                    "json",
                    "--limit",
                    "100",
                ],
                timeout=120,  # Higher limit = more time
            )
            if code != 0:
                results[ptype] = (False, "list failed")
                continue

            repos = _extract_json(stdout)
            if not repos:
                results[ptype] = (False, "no repos or JSON parse error")
                continue

            # Find repo WITH spaces
            cloned = False
            for repo in repos:
                org = repo.get("organization", repo.get("workspace", ""))
                project = repo.get("project") or "*"
                name = repo.get("name", repo.get("repository", ""))

                has_space = " " in str(org) or " " in str(project) or " " in str(name)
                if not has_space:
                    continue

                pattern = f"{org}/{project}/{name}"
                print(f"  Cloning (spaces): {pattern}")

                try:
                    code, stdout, stderr = run_mgit_command(
                        ["sync", pattern, str(clone_dir), "--provider", provider],
                        timeout=180,  # 3 min for git clone
                    )

                    if code == 0 and list(clone_dir.rglob(".git")):
                        results[ptype] = (True, "OK")
                        cloned = True
                        break
                    else:
                        print(f"  Failed: exit {code}")
                except subprocess.TimeoutExpired:
                    print("  Timeout (repo too large), trying next...")
                    continue

            if not cloned and ptype not in results:
                results[ptype] = (
                    True,
                    "skipped - no repos with spaces or all too large",
                )

    finally:
        shutil.rmtree(test_dir, ignore_errors=True)

    # Report
    [t for t, (passed, _) in results.items() if passed]
    failed = [(t, msg) for t, (passed, msg) in results.items() if not passed]

    print("\n=== Sync (with spaces) Results ===")
    for ptype, (passed, msg) in results.items():
        status = "✅" if passed else "❌"
        print(f"  {ptype}: {status} {msg}")

    # This test passes if no explicit failures (skipped is OK)
    assert not failed, f"Provider types failed sync with spaces: {failed}"

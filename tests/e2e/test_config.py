"""End-to-end CLI config tests for default provider functionality.

These tests run actual CLI commands to test configuration management.
They are marked with @pytest.mark.e2e and skipped by default.
"""

import re
import subprocess

import pytest


def run_mgit_command(args: list[str]) -> tuple[int, str, str]:
    """Run mgit CLI command and return exit code, stdout, stderr."""
    result = subprocess.run(
        ["poetry", "run", "mgit"] + args, capture_output=True, text=True, timeout=30
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


def get_current_default() -> str | None:
    """Get current default provider from CLI."""
    code, stdout, stderr = run_mgit_command(["config", "--global"])
    if code != 0:
        return None

    for line in stdout.split("\n"):
        match = re.search(r"default_provider:\s+(.+)", line)
        if match:
            return match.group(1).strip()

    return None


def get_provider_with_default_marker() -> str | None:
    """Get which provider shows (default) marker in list."""
    code, stdout, stderr = run_mgit_command(["config", "--list"])
    if code != 0:
        return None

    for line in stdout.split("\n"):
        if "(default)" in line:
            # Parse lines like: "  work_ado (azuredevops) (default)"
            match = re.search(r"^\s+([^\s]+)", line)
            if match:
                return match.group(1)

    return None


@pytest.mark.e2e
def test_cli_config_default_provider():
    """Test CLI default provider functionality across all provider types.

    This test:
    1. Gets all configured providers and groups by type
    2. Selects one representative from each provider type
    3. For each representative, tests setting as default
    4. Verifies default shows correctly in --list and --global
    5. Restores original default
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

    # Select one representative from each type
    test_providers = [providers[0] for providers in providers_by_type.values()]

    print("\nTesting default provider functionality")
    print(f"Available types: {list(providers_by_type.keys())}")
    print(f"Testing with representatives: {test_providers}")

    # Save original default
    original_default = get_current_default()
    print(f"Original default: {original_default}")

    try:
        # Test each representative provider
        for provider_name in test_providers:
            print(f"\n--- Testing {provider_name} as default ---")

            # Set as default
            code, stdout, stderr = run_mgit_command(
                ["config", "--set-default", provider_name]
            )
            assert code == 0, f"Failed to set {provider_name} as default: {stderr}"
            print(f"✅ Set {provider_name} as default")

            # Verify in --global
            current_default = get_current_default()
            assert current_default == provider_name, (
                f"Global config shows {current_default}, expected {provider_name}"
            )
            print(f"✅ Global config shows correct default: {current_default}")

            # Verify in --list (correct provider has marker)
            marked_provider = get_provider_with_default_marker()
            assert marked_provider == provider_name, (
                f"List shows {marked_provider} with (default), expected {provider_name}"
            )
            print(
                f"✅ List shows (default) marker on correct provider: {marked_provider}"
            )

            # Verify other providers don't have marker
            code, stdout, stderr = run_mgit_command(["config", "--list"])
            assert code == 0, f"Failed to get provider list: {stderr}"

            default_count = stdout.count("(default)")
            assert default_count == 1, (
                f"Found {default_count} (default) markers, expected exactly 1"
            )
            print("✅ Exactly one provider shows (default) marker")

        print(
            f"\n=== All {len(test_providers)} provider types passed default tests ==="
        )

    finally:
        # Restore original default
        if original_default:
            print(f"\nRestoring original default: {original_default}")
            code, stdout, stderr = run_mgit_command(
                ["config", "--set-default", original_default]
            )
            if code != 0:
                print(f"⚠️  Failed to restore original default: {stderr}")
            else:
                # Verify restoration
                restored_default = get_current_default()
                if restored_default == original_default:
                    print(
                        f"✅ Successfully restored original default: {restored_default}"
                    )
                else:
                    print(
                        f"⚠️  Restoration mismatch: got {restored_default}, expected {original_default}"
                    )
        else:
            print("\nNo original default to restore")

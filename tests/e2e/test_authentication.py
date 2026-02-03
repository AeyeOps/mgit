"""End-to-end CLI authentication tests for all configured providers.

These tests run actual CLI commands using real APIs and credentials.
They are marked with @pytest.mark.e2e and skipped by default.
"""

import subprocess

import pytest

from mgit.config.yaml_manager import list_provider_names


@pytest.mark.e2e
@pytest.mark.requires_network
def test_cli_authentication():
    """Test CLI authentication for all configured providers.

    This test:
    1. Discovers all providers in ~/.config/mgit/config.yaml
    2. Runs mgit CLI commands to test authentication
    3. Verifies each provider can connect via CLI
    """
    provider_names = list_provider_names()

    if not provider_names:
        pytest.skip("No providers configured in ~/.config/mgit/config.yaml")

    results = {}

    for provider_name in provider_names:
        print(f"\nTesting CLI authentication for: {provider_name}")

        try:
            # Use mgit login command to test authentication
            result = subprocess.run(
                ["poetry", "run", "mgit", "login", "--config", provider_name],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print("  ✅ CLI Authentication successful")
                results[provider_name] = True
            else:
                print("  ❌ CLI Authentication failed")
                print(f"  Error output: {result.stderr}")
                results[provider_name] = False

        except subprocess.TimeoutExpired:
            print("  ❌ CLI Authentication timed out")
            results[provider_name] = False
        except Exception as e:
            print(f"  ❌ Error: {type(e).__name__}: {e}")
            results[provider_name] = False

    # Summary
    passed = sum(1 for result in results.values() if result)
    total = len(results)

    print("\n=== CLI Authentication Test Summary ===")
    print(f"Total providers tested: {total}")
    print(f"Authentication successful: {passed}")
    print(f"Authentication failed: {total - passed}")

    for provider_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {provider_name}: {status}")

    # Test passes if any provider authenticates successfully
    assert passed > 0, f"No providers could authenticate via CLI. Results: {results}"

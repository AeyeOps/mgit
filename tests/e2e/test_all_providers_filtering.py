#!/usr/bin/env python3
"""
Comprehensive end-to-end test for all 8 configured providers.
Tests all 3 segments of filtering (org/project/repo) with various patterns.
"""

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

# Add mgit to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class TestCase:
    """A test case for provider filtering."""

    provider: str
    pattern: str
    description: str
    expected_min_repos: int = 0  # Minimum repos expected (0 means any)
    expected_org: Optional[str] = None  # Expected organization in results


@dataclass
class TestResult:
    """Result of a single test."""

    test_case: TestCase
    success: bool
    repos_found: int
    error: Optional[str] = None
    sample_repos: List[str] = None


class ProviderFilterTester:
    """Tests all providers with various filter patterns."""

    def __init__(self):
        self.results: List[TestResult] = []

    def run_mgit_list(self, pattern: str, provider: str = None) -> Dict:
        """Run mgit list command and return results."""
        cmd = [
            "poetry",
            "run",
            "mgit",
            "list",
            pattern,
            "--format",
            "json",
            "--limit",
            "100",
        ]
        if provider:
            cmd.extend(["--provider", provider])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, cwd="/opt/aeo/mgit"
            )

            if result.returncode != 0:
                return {"error": result.stderr, "repos": []}

            # Parse JSON output
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                # Find the JSON line (skip log messages)
                for line in reversed(lines):
                    if line.startswith("[") or line.startswith("{"):
                        return {"repos": json.loads(line), "error": None}
            return {"repos": [], "error": "No JSON output"}

        except subprocess.TimeoutExpired:
            return {"error": "Command timed out", "repos": []}
        except Exception as e:
            return {"error": str(e), "repos": []}

    def test_provider(self, test_case: TestCase) -> TestResult:
        """Test a single provider with a pattern."""
        print(f"\n🔍 Testing {test_case.provider}: {test_case.description}")
        print(f"   Pattern: {test_case.pattern}")

        result = self.run_mgit_list(test_case.pattern, test_case.provider)

        if result["error"]:
            print(f"   ❌ Error: {result['error'][:100]}")
            return TestResult(
                test_case=test_case, success=False, repos_found=0, error=result["error"]
            )

        repos = result["repos"]
        repo_count = len(repos)

        # Check minimum repos expectation
        success = True
        if test_case.expected_min_repos > 0:
            success = repo_count >= test_case.expected_min_repos

        # Check organization expectation
        if success and test_case.expected_org and repos:
            orgs = set(r.get("organization", "") for r in repos)
            if test_case.expected_org not in orgs:
                success = False

        # Get sample repo names
        sample_repos = []
        if repos:
            sample_repos = [
                f"{r.get('organization')}/{r.get('repository')}" for r in repos[:3]
            ]

        status = "✅" if success else "❌"
        print(f"   {status} Found {repo_count} repositories")
        if sample_repos:
            print(f"   Sample: {', '.join(sample_repos)}")

        return TestResult(
            test_case=test_case,
            success=success,
            repos_found=repo_count,
            sample_repos=sample_repos,
        )


def create_test_cases() -> List[TestCase]:
    """Create comprehensive test cases for all providers."""
    return [
        # Azure DevOps Tests (org/project/repo pattern)
        TestCase("ado_pdidev", "*/*/*", "ADO PDI: All repos (wildcard all segments)"),
        TestCase("ado_pdidev", "PDI/*/*", "ADO PDI: Org filter (first segment)"),
        TestCase(
            "ado_pdidev", "*/AeyeOps/*", "ADO PDI: Project filter (middle segment)"
        ),
        TestCase("ado_pdidev", "*/*/*Service*", "ADO PDI: Repo filter (last segment)"),
        TestCase("ado_p97", "*/*/*", "ADO P97: All repos (wildcard all segments)"),
        TestCase("ado_p97", "P97Networks/*/*", "ADO P97: Org filter (first segment)"),
        TestCase("ado_p97", "*/P97*/*", "ADO P97: Project filter (middle segment)"),
        # GitHub Tests (org/*/repo pattern - middle segment ignored)
        TestCase("github_pdi", "*/*/*", "GitHub PDI: All repos (wildcard all)"),
        TestCase(
            "github_pdi", "PDI-SOFTWARE/*/*", "GitHub PDI: Org filter (first segment)"
        ),
        TestCase("github_pdi", "*/*/*api*", "GitHub PDI: Repo filter (last segment)"),
        TestCase("github_aeyeops", "*/*/*", "GitHub AeyeOps: All repos"),
        TestCase(
            "github_aeyeops",
            "AeyeOps/*/*",
            "GitHub AeyeOps: Org filter",
            expected_org="AeyeOps",
        ),
        TestCase("github_aeyeops", "*/*/*Aeo*", "GitHub AeyeOps: Repo pattern filter"),
        TestCase("github_steveant", "*/*/*", "GitHub steveant: All repos"),
        TestCase("github_steveant", "steveant/*/*", "GitHub steveant: User filter"),
        TestCase("github_steveant", "*/*/*test*", "GitHub steveant: Repo pattern"),
        TestCase("github_gasbuddy", "*/*/*", "GitHub GasBuddy: All repos"),
        TestCase(
            "github_gasbuddy",
            "gas-buddy/*/*",
            "GitHub GasBuddy: Org filter",
            expected_org="gas-buddy",
        ),
        TestCase("github_gasbuddy", "*/*/*service*", "GitHub GasBuddy: Service repos"),
        # BitBucket Tests (workspace/*/repo pattern)
        TestCase("bitbucket_pdi", "*/*/*", "BitBucket PDI: All repos"),
        TestCase(
            "bitbucket_pdi", "pdi-software/*/*", "BitBucket PDI: Workspace filter"
        ),
        TestCase("bitbucket_pdi", "*/*/*mobile*", "BitBucket PDI: Mobile repos"),
        TestCase("bitbucket_p97", "*/*/*", "BitBucket P97: All repos"),
        TestCase("bitbucket_p97", "p97networks/*/*", "BitBucket P97: Workspace filter"),
        TestCase("bitbucket_p97", "*/*/*api*", "BitBucket P97: API repos"),
    ]


def test_multi_provider_patterns():
    """Test patterns that should work across multiple providers."""
    print("\n" + "=" * 60)
    print("🌐 MULTI-PROVIDER PATTERN TESTS")
    print("=" * 60)

    multi_patterns = [
        ("*/*/*", "All repos across all providers"),
        ("*/*/*api*", "API repos across all providers"),
        ("*/*/*service*", "Service repos across all providers"),
        ("PDI*/*/*", "PDI organizations across providers"),
        ("*/Aeyeops/*", "AeyeOps project across providers"),
    ]

    tester = ProviderFilterTester()

    for pattern, description in multi_patterns:
        print(f"\n🔄 Testing multi-provider: {description}")
        print(f"   Pattern: {pattern}")

        result = tester.run_mgit_list(pattern, provider=None)  # No specific provider

        if result["error"]:
            print(f"   ❌ Error: {result['error'][:100]}")
        else:
            repos = result["repos"]
            # Count repos by provider/org
            provider_counts = {}
            for repo in repos:
                org = repo.get("organization", "unknown")
                provider_counts[org] = provider_counts.get(org, 0) + 1

            print(f"   ✅ Found {len(repos)} total repositories")
            if provider_counts:
                print(f"   Distribution: {dict(list(provider_counts.items())[:5])}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 COMPREHENSIVE PROVIDER FILTERING TESTS")
    print("=" * 60)

    # Test individual providers
    test_cases = create_test_cases()
    tester = ProviderFilterTester()

    results = []
    for test_case in test_cases:
        result = tester.test_provider(test_case)
        results.append(result)

    # Test multi-provider patterns
    test_multi_provider_patterns()

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    # Group by provider
    by_provider = {}
    for result in results:
        provider = result.test_case.provider
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(result)

    total_tests = len(results)
    total_passed = sum(1 for r in results if r.success)

    for provider, provider_results in by_provider.items():
        passed = sum(1 for r in provider_results if r.success)
        total = len(provider_results)
        status = "✅" if passed == total else "⚠️"
        print(f"{status} {provider}: {passed}/{total} tests passed")

        # Show failures
        for r in provider_results:
            if not r.success:
                print(f"   ❌ {r.test_case.description}")
                if r.error:
                    print(f"      Error: {r.error[:100]}")

    print(
        f"\n{'✅' if total_passed == total_tests else '❌'} Overall: {total_passed}/{total_tests} tests passed"
    )

    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())

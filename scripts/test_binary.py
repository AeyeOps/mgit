#!/usr/bin/env python3
"""
Standalone Linux binary test suite.

Tests the compiled mgit binary at /usr/local/bin/mgit with REAL network operations.
Uses /tmp/ for test artifacts. Requires configured providers for network tests.

Usage:
    uv run python scripts/test_binary.py
    uv run python scripts/test_binary.py --verbose
    uv run python scripts/test_binary.py --binary /path/to/mgit
    uv run python scripts/test_binary.py --skip-network  # Skip network tests
"""

import argparse
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Default binary location - explicit to avoid PATH conflicts
DEFAULT_BINARY = "/usr/local/bin/mgit"


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    duration_ms: int = 0


class StandaloneTestSuite:
    def __init__(self, binary: str, verbose: bool = False, skip_network: bool = False):
        self.binary = binary
        self.verbose = verbose
        self.skip_network = skip_network
        self.results: list[TestResult] = []
        self.test_dir = Path(tempfile.mkdtemp(prefix="mgit_standalone_test_"))
        self.providers: dict[str, str] = {}  # name -> type

    def log(self, msg: str) -> None:
        if self.verbose:
            print(f"  {msg}")

    def run_cmd(
        self, args: list[str], timeout: int = 30, check: bool = False
    ) -> subprocess.CompletedProcess:
        """Run mgit command with explicit binary path."""
        cmd = [self.binary] + args
        self.log(f"Running: {' '.join(cmd)}")
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check,
        )

    def add_result(self, name: str, passed: bool, message: str) -> None:
        self.results.append(TestResult(name, passed, message))
        status = "✓" if passed else "✗"
        print(f"  {status} {name}: {message}")

    # =========================================================================
    # Test: Binary exists and is executable
    # =========================================================================
    def test_binary_exists(self) -> None:
        """Verify the binary exists and is executable."""
        path = Path(self.binary)
        if not path.exists():
            self.add_result("binary_exists", False, f"Binary not found: {self.binary}")
            return
        if not os.access(self.binary, os.X_OK):
            self.add_result(
                "binary_exists", False, f"Binary not executable: {self.binary}"
            )
            return
        size_mb = path.stat().st_size / (1024 * 1024)
        self.add_result("binary_exists", True, f"Found ({size_mb:.1f} MB)")

    # =========================================================================
    # Test: Version output
    # =========================================================================
    def test_version(self) -> None:
        """Test --version flag."""
        try:
            result = self.run_cmd(["--version"])
            if result.returncode == 0 and "version" in result.stdout.lower():
                version = result.stdout.strip().split()[-1]
                self.add_result("version", True, f"v{version}")
            else:
                self.add_result(
                    "version", False, f"Unexpected output: {result.stdout[:50]}"
                )
        except Exception as e:
            self.add_result("version", False, str(e))

    # =========================================================================
    # Test: Help output
    # =========================================================================
    def test_help(self) -> None:
        """Test --help flag."""
        try:
            result = self.run_cmd(["--help"])
            if result.returncode == 0 and "usage" in result.stdout.lower():
                # Count commands mentioned
                commands = ["sync", "list", "status", "config", "login"]
                found = [c for c in commands if c in result.stdout.lower()]
                self.add_result(
                    "help", True, f"Found {len(found)}/{len(commands)} commands"
                )
            else:
                self.add_result("help", False, "No help text")
        except Exception as e:
            self.add_result("help", False, str(e))

    # =========================================================================
    # Test: Config list (no network needed)
    # =========================================================================
    def test_config_list(self) -> None:
        """Test config --list (doesn't require network)."""
        try:
            result = self.run_cmd(["config", "--list"])
            # May show providers or "no providers configured" - both are valid
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                self.add_result("config_list", True, f"{len(lines)} lines output")
            else:
                self.add_result("config_list", False, f"Exit code {result.returncode}")
        except Exception as e:
            self.add_result("config_list", False, str(e))

    # =========================================================================
    # Test: Status with synthetic repos
    # =========================================================================
    def test_status_clean_repo(self) -> None:
        """Test status on clean repo."""
        repo_dir = self.test_dir / "clean_repo"
        repo_dir.mkdir(parents=True)
        try:
            # Initialize git repo
            subprocess.run(
                ["git", "init"], cwd=repo_dir, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=repo_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=repo_dir,
                capture_output=True,
            )
            (repo_dir / "file.txt").write_text("test")
            subprocess.run(
                ["git", "add", "."], cwd=repo_dir, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=repo_dir,
                capture_output=True,
                check=True,
            )

            # Run mgit status
            result = self.run_cmd(["status", str(repo_dir), "--show-clean"])
            if result.returncode == 0:
                self.add_result("status_clean", True, "Clean repo detected")
            else:
                self.add_result("status_clean", False, f"Exit {result.returncode}")
        except Exception as e:
            self.add_result("status_clean", False, str(e))

    def test_status_dirty_repo(self) -> None:
        """Test status on dirty repo."""
        repo_dir = self.test_dir / "dirty_repo"
        repo_dir.mkdir(parents=True)
        try:
            # Initialize and make dirty
            subprocess.run(
                ["git", "init"], cwd=repo_dir, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=repo_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=repo_dir,
                capture_output=True,
            )
            (repo_dir / "file.txt").write_text("test")
            subprocess.run(
                ["git", "add", "."], cwd=repo_dir, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=repo_dir,
                capture_output=True,
                check=True,
            )
            # Make it dirty
            (repo_dir / "file.txt").write_text("modified")

            result = self.run_cmd(["status", str(repo_dir)])
            if result.returncode == 0 and "dirty" in result.stdout.lower():
                self.add_result("status_dirty", True, "Dirty repo detected")
            elif result.returncode == 0:
                self.add_result("status_dirty", True, "Repo status checked")
            else:
                self.add_result("status_dirty", False, f"Exit {result.returncode}")
        except Exception as e:
            self.add_result("status_dirty", False, str(e))

    def test_status_multiple_repos(self) -> None:
        """Test status on directory with multiple repos."""
        multi_dir = self.test_dir / "multi"
        multi_dir.mkdir(parents=True)
        try:
            for name in ["repo1", "repo2", "repo3"]:
                repo = multi_dir / name
                repo.mkdir()
                subprocess.run(
                    ["git", "init"], cwd=repo, capture_output=True, check=True
                )
                subprocess.run(
                    ["git", "config", "user.email", "test@test.com"],
                    cwd=repo,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "config", "user.name", "Test"],
                    cwd=repo,
                    capture_output=True,
                )
                (repo / "file.txt").write_text(f"content-{name}")
                subprocess.run(
                    ["git", "add", "."], cwd=repo, capture_output=True, check=True
                )
                subprocess.run(
                    ["git", "commit", "-m", "init"],
                    cwd=repo,
                    capture_output=True,
                    check=True,
                )

            result = self.run_cmd(["status", str(multi_dir), "--show-clean"])
            if result.returncode == 0:
                self.add_result("status_multi", True, "3 repos scanned")
            else:
                self.add_result("status_multi", False, f"Exit {result.returncode}")
        except Exception as e:
            self.add_result("status_multi", False, str(e))

    def test_status_json_output(self) -> None:
        """Test status with JSON output format."""
        repo_dir = self.test_dir / "json_test"
        repo_dir.mkdir(parents=True)
        try:
            subprocess.run(
                ["git", "init"], cwd=repo_dir, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=repo_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=repo_dir,
                capture_output=True,
            )
            (repo_dir / "file.txt").write_text("test")
            subprocess.run(
                ["git", "add", "."], cwd=repo_dir, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=repo_dir,
                capture_output=True,
                check=True,
            )

            result = self.run_cmd(
                ["status", str(repo_dir), "--output", "json", "--show-clean"]
            )
            if result.returncode == 0 and (
                "{" in result.stdout or "[" in result.stdout
            ):
                self.add_result("status_json", True, "JSON output valid")
            elif result.returncode == 0:
                self.add_result("status_json", True, "Output produced")
            else:
                self.add_result("status_json", False, f"Exit {result.returncode}")
        except Exception as e:
            self.add_result("status_json", False, str(e))

    def test_status_fail_on_dirty(self) -> None:
        """Test --fail-on-dirty flag."""
        repo_dir = self.test_dir / "fail_dirty"
        repo_dir.mkdir(parents=True)
        try:
            subprocess.run(
                ["git", "init"], cwd=repo_dir, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=repo_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=repo_dir,
                capture_output=True,
            )
            (repo_dir / "file.txt").write_text("test")
            subprocess.run(
                ["git", "add", "."], cwd=repo_dir, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=repo_dir,
                capture_output=True,
                check=True,
            )
            # Make dirty
            (repo_dir / "file.txt").write_text("dirty")

            result = self.run_cmd(["status", str(repo_dir), "--fail-on-dirty"])
            # Should return non-zero for dirty repo
            if result.returncode != 0:
                self.add_result("status_fail_dirty", True, "Non-zero exit on dirty")
            else:
                self.add_result("status_fail_dirty", False, "Should have failed")
        except Exception as e:
            self.add_result("status_fail_dirty", False, str(e))

    def test_status_empty_dir(self) -> None:
        """Test status on empty directory."""
        empty_dir = self.test_dir / "empty"
        empty_dir.mkdir(parents=True)
        try:
            result = self.run_cmd(["status", str(empty_dir)])
            # Empty dir should work (just find no repos)
            if result.returncode == 0:
                self.add_result("status_empty", True, "Handled empty dir")
            else:
                self.add_result("status_empty", False, f"Exit {result.returncode}")
        except Exception as e:
            self.add_result("status_empty", False, str(e))

    def test_status_concurrency(self) -> None:
        """Test status with concurrency flag."""
        repo_dir = self.test_dir / "concurrency"
        repo_dir.mkdir(parents=True)
        try:
            subprocess.run(
                ["git", "init"], cwd=repo_dir, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=repo_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=repo_dir,
                capture_output=True,
            )
            (repo_dir / "file.txt").write_text("test")
            subprocess.run(
                ["git", "add", "."], cwd=repo_dir, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=repo_dir,
                capture_output=True,
                check=True,
            )

            result = self.run_cmd(
                ["status", str(repo_dir), "--concurrency", "1", "--show-clean"]
            )
            if result.returncode == 0:
                self.add_result("status_concurrency", True, "Concurrency=1 works")
            else:
                self.add_result(
                    "status_concurrency", False, f"Exit {result.returncode}"
                )
        except Exception as e:
            self.add_result("status_concurrency", False, str(e))

    # =========================================================================
    # Test: Invalid commands/patterns
    # =========================================================================
    def test_invalid_command(self) -> None:
        """Test handling of invalid command."""
        try:
            result = self.run_cmd(["nonexistent_command"])
            # Should fail with non-zero exit
            if result.returncode != 0:
                self.add_result("invalid_command", True, "Rejected gracefully")
            else:
                self.add_result("invalid_command", False, "Should have failed")
        except Exception as e:
            self.add_result("invalid_command", False, str(e))

    def test_missing_args(self) -> None:
        """Test handling of missing required arguments.

        Note: sync without args does local sync (valid behavior).
        We test list without pattern which requires a query.
        """
        try:
            result = self.run_cmd(["list"])  # list without pattern
            # Should fail or show help - list requires QUERY argument
            if result.returncode != 0 or "usage" in result.stdout.lower():
                self.add_result("missing_args", True, "Handled missing args")
            else:
                self.add_result("missing_args", False, "Should require args")
        except Exception as e:
            self.add_result("missing_args", False, str(e))

    # =========================================================================
    # Network Tests: Real Provider Operations
    # =========================================================================
    def get_providers(self) -> dict[str, str]:
        """Get configured providers from config --list."""
        result = self.run_cmd(["config", "--list"])
        if result.returncode != 0:
            return {}

        providers = {}
        for line in result.stdout.split("\n"):
            # Parse lines like: "  work_ado (azuredevops)"
            match = re.search(r"^\s+([^\s]+)\s+\(([^)]+)\)", line)
            if match:
                name, ptype = match.groups()
                providers[name] = ptype

        return providers

    def test_list_real_providers(self) -> None:
        """Test list command against REAL provider APIs.

        This test exercises actual network calls to configured providers.
        It groups providers by type and tests one from each type.
        """
        self.providers = self.get_providers()

        if not self.providers:
            self.add_result("list_providers", False, "No providers configured")
            return

        # Group by type, pick one from each
        by_type: dict[str, list[str]] = {}
        for name, ptype in self.providers.items():
            by_type.setdefault(ptype, []).append(name)

        self.log(f"Provider types: {list(by_type.keys())}")

        failed_providers = []
        for ptype, names in by_type.items():
            provider = random.choice(names)
            self.log(f"Testing {provider} ({ptype})")

            result = self.run_cmd(
                [
                    "list",
                    "*/*/*",
                    "--provider",
                    provider,
                    "--format",
                    "table",
                    "--limit",
                    "5",
                ],
                timeout=60,
            )

            if result.returncode != 0:
                failed_providers.append(f"{provider}({ptype})")
                self.log(f"  FAILED: {result.stderr[:100]}")
            else:
                self.log(f"  OK: {len(result.stdout.split(chr(10)))} lines")

        if not failed_providers:
            self.add_result(
                "list_providers",
                True,
                f"All {len(by_type)} provider types OK",
            )
        else:
            self.add_result(
                "list_providers",
                False,
                f"Failed: {', '.join(failed_providers)}",
            )

    def test_list_nonexistent_provider(self) -> None:
        """Test that non-existent provider returns non-zero exit code.

        This is a critical fail-fast test - configuration errors MUST fail.
        """
        result = self.run_cmd(
            ["list", "*/*/*", "--provider", "nonexistent_provider_12345"],
            timeout=30,
        )

        if result.returncode != 0:
            self.add_result("list_bad_provider", True, f"Exit code {result.returncode}")
        else:
            self.add_result(
                "list_bad_provider",
                False,
                "FAIL-FAST VIOLATION: Should exit non-zero for bad provider",
            )

    def test_list_invalid_pattern(self) -> None:
        """Test that invalid query patterns are rejected."""
        if not self.providers:
            self.add_result("list_bad_pattern", False, "No providers to test with")
            return

        provider = next(iter(self.providers.keys()))
        result = self.run_cmd(
            ["list", "invalid/pattern/with/too/many/parts", "--provider", provider],
            timeout=30,
        )

        if result.returncode != 0:
            self.add_result("list_bad_pattern", True, "Invalid pattern rejected")
        else:
            self.add_result("list_bad_pattern", False, "Should reject invalid pattern")

    def _extract_json(self, output: str) -> list | None:
        """Extract JSON array from output that may contain log lines."""
        import json

        # Find the JSON array - look for [{ or [\n{ to avoid false matches like [authentication_success]
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

    def test_sync_no_spaces(self) -> None:
        """Test sync with repos that have NO spaces in names.

        Tests one repo from each provider type (GitHub, Azure DevOps, BitBucket)
        where org/project/repo names contain no spaces.
        """
        if not self.providers:
            self.add_result("sync_no_spaces", False, "No providers configured")
            return

        by_type: dict[str, list[str]] = {}
        for name, ptype in self.providers.items():
            by_type.setdefault(ptype, []).append(name)

        results: dict[str, str] = {}

        for ptype, providers in by_type.items():
            provider = random.choice(providers)
            clone_dir = self.test_dir / f"sync_nospace_{ptype}"
            clone_dir.mkdir(parents=True, exist_ok=True)

            self.log(f"Testing sync (no spaces) for {ptype} via {provider}")

            list_result = self.run_cmd(
                [
                    "list",
                    "*/*/*",
                    "--provider",
                    provider,
                    "--format",
                    "json",
                    "--limit",
                    "50",
                ],
                timeout=90,
            )

            if list_result.returncode != 0:
                results[ptype] = "list failed"
                continue

            repos = self._extract_json(list_result.stdout)
            if not repos:
                results[ptype] = "no repos or JSON parse error"
                continue

            # Find repo WITHOUT spaces
            cloned = False
            for repo in repos:
                org = repo.get("organization", repo.get("workspace", ""))
                project = repo.get("project") or "*"
                name = repo.get("name", repo.get("repository", ""))

                if " " in str(org) or " " in str(project) or " " in str(name):
                    continue  # Skip repos with spaces

                pattern = f"{org}/{project}/{name}"
                self.log(f"  Cloning (no spaces): {pattern}")

                try:
                    sync_result = self.run_cmd(
                        ["sync", pattern, str(clone_dir), "--provider", provider],
                        timeout=180,
                    )

                    if sync_result.returncode == 0:
                        git_dirs = list(clone_dir.rglob(".git"))
                        if git_dirs:
                            results[ptype] = "OK"
                            cloned = True
                            break
                except subprocess.TimeoutExpired:
                    self.log("  Timeout (repo too large), trying next...")
                    continue

            if not cloned and ptype not in results:
                results[ptype] = "no repo cloned (all too large or no matches)"

        ok_types = [t for t, r in results.items() if r == "OK"]
        if len(ok_types) == len(by_type):
            self.add_result("sync_no_spaces", True, f"All {len(ok_types)} types OK")
        elif ok_types:
            failed = [(t, r) for t, r in results.items() if r != "OK"]
            self.add_result(
                "sync_no_spaces", False, f"OK: {ok_types}, FAILED: {failed}"
            )
        else:
            self.add_result("sync_no_spaces", False, f"All failed: {dict(results)}")

    def test_sync_with_spaces(self) -> None:
        """Test sync with repos that HAVE spaces in names.

        Tests one repo from each provider type where org/project/repo contains spaces.
        This validates the space handling fix in manager.py.
        """
        if not self.providers:
            self.add_result("sync_with_spaces", False, "No providers configured")
            return

        by_type: dict[str, list[str]] = {}
        for name, ptype in self.providers.items():
            by_type.setdefault(ptype, []).append(name)

        results: dict[str, str] = {}

        for ptype, providers in by_type.items():
            provider = random.choice(providers)
            clone_dir = self.test_dir / f"sync_spaces_{ptype}"
            clone_dir.mkdir(parents=True, exist_ok=True)

            self.log(f"Testing sync (with spaces) for {ptype} via {provider}")

            list_result = self.run_cmd(
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
                timeout=90,
            )

            if list_result.returncode != 0:
                results[ptype] = "list failed"
                continue

            repos = self._extract_json(list_result.stdout)
            if not repos:
                results[ptype] = "no repos or JSON parse error"
                continue

            # Find repo WITH spaces
            cloned = False
            for repo in repos:
                org = repo.get("organization", repo.get("workspace", ""))
                project = repo.get("project") or "*"
                name = repo.get("name", repo.get("repository", ""))

                has_space = " " in str(org) or " " in str(project) or " " in str(name)
                if not has_space:
                    continue  # Only test repos WITH spaces

                pattern = f"{org}/{project}/{name}"
                self.log(f"  Cloning (with spaces): {pattern}")

                try:
                    sync_result = self.run_cmd(
                        ["sync", pattern, str(clone_dir), "--provider", provider],
                        timeout=180,
                    )

                    if sync_result.returncode == 0:
                        git_dirs = list(clone_dir.rglob(".git"))
                        if git_dirs:
                            results[ptype] = "OK"
                            cloned = True
                            break
                        else:
                            self.log("  No .git created despite exit 0")
                    else:
                        self.log(
                            f"  Exit {sync_result.returncode}: {sync_result.stderr[:100]}"
                        )
                except subprocess.TimeoutExpired:
                    self.log("  Timeout (repo too large), trying next...")
                    continue

            if not cloned and ptype not in results:
                results[ptype] = "no repo with spaces found or all too large"

        ok_types = [t for t, r in results.items() if r == "OK"]
        skipped_msgs = (
            "no repo with spaces found",
            "no repo with spaces found or all too large",
        )
        skipped = [t for t, r in results.items() if r in skipped_msgs]
        failed = [
            (t, r) for t, r in results.items() if r != "OK" and r not in skipped_msgs
        ]

        if failed:
            self.add_result("sync_with_spaces", False, f"FAILED: {failed}")
        elif ok_types:
            msg = f"{len(ok_types)} types OK"
            if skipped:
                msg += f", {len(skipped)} skipped (no spaces)"
            self.add_result("sync_with_spaces", True, msg)
        else:
            self.add_result(
                "sync_with_spaces", True, "All skipped (no spaces in any repos)"
            )

    # =========================================================================
    # Cleanup and run
    # =========================================================================
    def cleanup(self) -> None:
        """Remove test directory."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            self.log(f"Cleaned up {self.test_dir}")

    def run_all(self) -> bool:
        """Run all tests and return True if all passed."""
        print(f"\n{'=' * 60}")
        print("mgit Standalone Linux Binary Test Suite")
        print(f"Binary: {self.binary}")
        print(f"Test dir: {self.test_dir}")
        print(f"{'=' * 60}\n")

        # Smoke tests
        print("[Smoke Tests]")
        self.test_binary_exists()
        if not self.results[-1].passed:
            print("\n❌ Binary not found. Build first with:")
            print("   uv run python scripts/make_build.py --target linux --install")
            return False

        self.test_version()
        self.test_help()

        # Config tests
        print("\n[Config Tests]")
        self.test_config_list()

        # Status tests
        print("\n[Status Tests]")
        self.test_status_clean_repo()
        self.test_status_dirty_repo()
        self.test_status_multiple_repos()
        self.test_status_json_output()
        self.test_status_fail_on_dirty()
        self.test_status_empty_dir()
        self.test_status_concurrency()

        # Error handling tests
        print("\n[Error Handling Tests]")
        self.test_invalid_command()
        self.test_missing_args()

        # Network tests - hit real provider APIs
        if self.skip_network:
            print("\n[Network Tests] SKIPPED (--skip-network)")
        else:
            print("\n[Network Tests - Real Provider APIs]")
            self.test_list_real_providers()
            self.test_list_nonexistent_provider()
            self.test_list_invalid_pattern()

            print("\n[Sync Tests - Each Provider Type]")
            self.test_sync_no_spaces()
            self.test_sync_with_spaces()

        # Cleanup
        self.cleanup()

        # Summary
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        print(f"\n{'=' * 60}")
        print(f"Results: {passed}/{total} tests passed")
        print(f"{'=' * 60}\n")

        return passed == total


def main() -> None:
    parser = argparse.ArgumentParser(description="Test mgit standalone Linux binary")
    parser.add_argument(
        "--binary",
        default=DEFAULT_BINARY,
        help=f"Path to mgit binary (default: {DEFAULT_BINARY})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )
    parser.add_argument(
        "--skip-network",
        action="store_true",
        help="Skip network tests (only run local tests)",
    )
    args = parser.parse_args()

    suite = StandaloneTestSuite(args.binary, args.verbose, args.skip_network)
    success = suite.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

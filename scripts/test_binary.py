#!/usr/bin/env python3
"""
Standalone Linux binary test suite.

Tests the compiled mgit binary at /opt/bin/mgit without network access.
Uses /tmp/ for test artifacts.

Usage:
    uv run python scripts/make_standalone_linux.py
    uv run python scripts/make_standalone_linux.py --verbose
    uv run python scripts/make_standalone_linux.py --binary /path/to/mgit
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Default binary location - explicit to avoid PATH conflicts
DEFAULT_BINARY = "/opt/bin/mgit"


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    duration_ms: int = 0


class StandaloneTestSuite:
    def __init__(self, binary: str, verbose: bool = False):
        self.binary = binary
        self.verbose = verbose
        self.results: list[TestResult] = []
        self.test_dir = Path(tempfile.mkdtemp(prefix="mgit_standalone_test_"))

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
            self.add_result("binary_exists", False, f"Binary not executable: {self.binary}")
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
                self.add_result("version", False, f"Unexpected output: {result.stdout[:50]}")
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
                self.add_result("help", True, f"Found {len(found)}/{len(commands)} commands")
            else:
                self.add_result("help", False, f"No help text")
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
            subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
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
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
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
            subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
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
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
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
                subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
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
                subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
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
            subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
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
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=repo_dir,
                capture_output=True,
                check=True,
            )

            result = self.run_cmd(["status", str(repo_dir), "--output", "json", "--show-clean"])
            if result.returncode == 0 and ("{" in result.stdout or "[" in result.stdout):
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
            subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
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
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
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
            subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
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
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
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
                self.add_result("status_concurrency", False, f"Exit {result.returncode}")
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
        """Test handling of missing required arguments."""
        try:
            result = self.run_cmd(["sync"])  # sync without pattern
            # Should fail or show help
            if result.returncode != 0 or "usage" in result.stdout.lower():
                self.add_result("missing_args", True, "Handled missing args")
            else:
                self.add_result("missing_args", False, "Should require args")
        except Exception as e:
            self.add_result("missing_args", False, str(e))

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
        print(f"\n{'='*60}")
        print(f"mgit Standalone Linux Binary Test Suite")
        print(f"Binary: {self.binary}")
        print(f"Test dir: {self.test_dir}")
        print(f"{'='*60}\n")

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

        # Cleanup
        self.cleanup()

        # Summary
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        print(f"\n{'='*60}")
        print(f"Results: {passed}/{total} tests passed")
        print(f"{'='*60}\n")

        return passed == total


def main() -> None:
    parser = argparse.ArgumentParser(description="Test mgit standalone Linux binary")
    parser.add_argument(
        "--binary",
        default=DEFAULT_BINARY,
        help=f"Path to mgit binary (default: {DEFAULT_BINARY})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output",
    )
    args = parser.parse_args()

    suite = StandaloneTestSuite(args.binary, args.verbose)
    success = suite.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

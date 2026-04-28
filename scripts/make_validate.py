#!/usr/bin/env python3
"""Unified validation: format + lint + typecheck + security scan.

Replaces individual make_format.py, make_lint.py scripts.
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

CHECK_PATHS = ["mgit/", "scripts/", "tests/"]


def run_step(name: str, cmd: list[str]) -> bool:
    """Run a validation step and return success status."""
    print(f"[validate] {name}...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"[validate] {name} FAILED")
        return False
    print(f"[validate] {name} passed")
    return True


def run_dependency_audit() -> bool:
    """Audit the locked dependency set for known vulnerabilities."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        prefix="mgit-audit-",
        delete=False,
    ) as req_file:
        req_path = Path(req_file.name)

    try:
        if not run_step(
            "Exporting locked dependencies",
            [
                "uv",
                "export",
                "--quiet",
                "--frozen",
                "--format",
                "requirements.txt",
                "--all-groups",
                "--no-emit-project",
                "--no-hashes",
                "-o",
                str(req_path),
            ],
        ):
            return False

        return run_step(
            "Running dependency vulnerability audit",
            [
                "uv",
                "run",
                "pip-audit",
                "--progress-spinner",
                "off",
                "-r",
                str(req_path),
            ],
        )
    finally:
        req_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all validation checks")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix formatting and lint issues (runs first)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check only, no fixes (default behavior)",
    )
    args = parser.parse_args()

    failed = False

    # If --fix, run fixes FIRST before any checks
    if args.fix:
        print("[validate] Running auto-fixes...")
        # Format first
        subprocess.run(["uv", "run", "ruff", "format", *CHECK_PATHS])
        # Then lint fixes
        subprocess.run(["uv", "run", "ruff", "check", *CHECK_PATHS, "--fix"])
        print("[validate] Fixes applied, now checking...")
        print()

    # Ruff format check
    if not run_step(
        "Checking formatting",
        ["uv", "run", "ruff", "format", "--check", *CHECK_PATHS],
    ):
        failed = True

    # Ruff lint check
    if not run_step("Running linter", ["uv", "run", "ruff", "check", *CHECK_PATHS]):
        failed = True

    # ty type check
    if not run_step("Running type checker", ["uv", "run", "ty", "check"]):
        failed = True

    # Bandit security scan
    if not run_step(
        "Running source security scan",
        ["uv", "run", "bandit", "-r", *CHECK_PATHS, "-lll"],
    ):
        failed = True

    # Dependency vulnerability audit
    if not run_dependency_audit():
        failed = True

    print()
    if failed:
        print("[validate] Some checks failed")
        return 1
    print("[validate] All checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

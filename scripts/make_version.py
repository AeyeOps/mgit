#!/usr/bin/env python3
"""Bump version. Use --bump patch|minor|major.

Runs `make validate` before bumping to prevent pushing code that fails CI.
Use --skip-validate to bypass (not recommended).
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_validate() -> bool:
    """Run make validate and return True if all checks pass."""
    print("[version] Running validation checks before bump...")
    result = subprocess.run(
        ["uv", "run", "python", "scripts/make_validate.py"],
        cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        return False

    print("[version] Running unit tests...")
    result = subprocess.run(
        ["uv", "run", "pytest", "tests/unit/", "-v", "--tb=short", "--no-cov", "-q"],
        cwd=PROJECT_ROOT,
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Bump project version")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], required=True)
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip validation checks (not recommended)",
    )
    args = parser.parse_args()

    if not args.skip_validate:
        if not run_validate():
            print("[version] Validation failed — fix issues before bumping version")
            print("[version] Run 'make validate ARGS=--fix' to auto-fix, then retry")
            sys.exit(1)
        print("[version] All checks passed")
        print()

    pyproject = PROJECT_ROOT / "pyproject.toml"
    content = pyproject.read_text()

    match = re.search(r'version = "(\d+)\.(\d+)\.(\d+)"', content)
    if not match:
        raise ValueError("Version not found in pyproject.toml")

    major, minor, patch = map(int, match.groups())

    if args.bump == "major":
        major, minor, patch = major + 1, 0, 0
    elif args.bump == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1

    new_version = f"{major}.{minor}.{patch}"
    new_content = re.sub(
        r'version = "\d+\.\d+\.\d+"', f'version = "{new_version}"', content
    )
    pyproject.write_text(new_content)
    print(f"Version bumped to {new_version}")


if __name__ == "__main__":
    main()

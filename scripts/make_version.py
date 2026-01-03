#!/usr/bin/env python3
"""Bump version. Use --bump patch|minor|major."""
import argparse
import re
import subprocess
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Bump project version")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], required=True)
    args = parser.parse_args()

    pyproject = Path(__file__).parent.parent / "pyproject.toml"
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
    new_content = re.sub(r'version = "\d+\.\d+\.\d+"', f'version = "{new_version}"', content)
    pyproject.write_text(new_content)
    print(f"Version bumped to {new_version}")

if __name__ == "__main__":
    main()

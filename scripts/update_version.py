#!/usr/bin/env python3
"""
Update version using Poetry's version command
Usage: python scripts/update_version.py [major|minor|patch|x.y.z]
"""
import sys
import subprocess
import re
from pathlib import Path


def get_current_version():
    """Get current version from pyproject.toml."""
    result = subprocess.run(
        ["poetry", "version", "-s"], 
        capture_output=True, 
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get version: {result.stderr}")
    return result.stdout.strip()


def update_version(bump_type):
    """Update version using poetry."""
    # Run poetry version command
    result = subprocess.run(
        ["poetry", "version", bump_type],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to update version: {result.stderr}")
    
    # Extract new version from output
    # Output format: "Bumping version from X.Y.Z to A.B.C"
    output = result.stdout.strip()
    match = re.search(r'to (\d+\.\d+\.\d+)', output)
    if match:
        return match.group(1)
    
    # Fallback: get version directly
    return get_current_version()


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    
    bump_type = sys.argv[1]
    valid_types = ['major', 'minor', 'patch', 'premajor', 'preminor', 'prepatch', 'prerelease']
    
    # Check if it's a valid bump type or specific version
    if bump_type not in valid_types and not re.match(r'^\d+\.\d+\.\d+', bump_type):
        print(f"Error: Invalid argument '{bump_type}'")
        print(f"Use: {', '.join(valid_types)}, or specific version like 1.2.3")
        sys.exit(1)
    
    try:
        print(f"Current version: {get_current_version()}")
        
        new_version = update_version(bump_type)
        print(f"New version: {new_version}")
        
        print(f"\nVersion updated successfully!")
        print(f"Next steps:")
        print(f"  1. Update CHANGELOG.md with changes for v{new_version}")
        print(f"  2. Commit: git add -A && git commit -m 'chore: bump version to {new_version}'")
        print(f"  3. Push: git push origin main")
        print(f"\nThe auto-release workflow will trigger automatically!")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
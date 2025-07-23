#!/usr/bin/env python3
"""
Update version in pyproject.toml and mgit/constants.py
Usage: python scripts/update_version.py [major|minor|patch|x.y.z]
"""
import sys
import re
from pathlib import Path


def parse_version(version_str):
    """Parse version string into (major, minor, patch)."""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    return tuple(map(int, match.groups()))


def bump_version(current_version, bump_type):
    """Bump version based on type or return specific version."""
    # Check if it's a specific version
    if re.match(r'^\d+\.\d+\.\d+', bump_type):
        return bump_type
    
    major, minor, patch = parse_version(current_version)
    
    if bump_type == 'major':
        return f"{major + 1}.0.0"
    elif bump_type == 'minor':
        return f"{major}.{minor + 1}.0"
    elif bump_type == 'patch':
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def update_pyproject_toml(new_version):
    """Update version in pyproject.toml."""
    path = Path("pyproject.toml")
    content = path.read_text()
    
    # Update version line
    content = re.sub(
        r'^version = ".*"',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE
    )
    
    path.write_text(content)
    print(f"Updated pyproject.toml to version {new_version}")


def update_constants_py(new_version):
    """Update version in mgit/constants.py."""
    path = Path("mgit/constants.py")
    content = path.read_text()
    
    # Update VERSION line
    content = re.sub(
        r'^VERSION = ".*"',
        f'VERSION = "{new_version}"',
        content,
        flags=re.MULTILINE
    )
    
    path.write_text(content)
    print(f"Updated mgit/constants.py to version {new_version}")


def get_current_version():
    """Get current version from pyproject.toml."""
    content = Path("pyproject.toml").read_text()
    match = re.search(r'^version = "(.*)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    
    bump_type = sys.argv[1]
    if bump_type not in ['major', 'minor', 'patch'] and not re.match(r'^\d+\.\d+\.\d+', bump_type):
        print(f"Error: Invalid argument '{bump_type}'")
        print("Use: major, minor, patch, or specific version like 1.2.3")
        sys.exit(1)
    
    try:
        current_version = get_current_version()
        print(f"Current version: {current_version}")
        
        new_version = bump_version(current_version, bump_type)
        print(f"New version: {new_version}")
        
        update_pyproject_toml(new_version)
        update_constants_py(new_version)
        
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
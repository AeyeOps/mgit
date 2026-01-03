#!/usr/bin/env python3
"""Remove build artifacts."""

import shutil
from pathlib import Path

DIRS_TO_REMOVE = [
    "build",
    "dist",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
    ".coverage",
]
PATTERNS_TO_REMOVE = ["*.egg-info"]

if __name__ == "__main__":
    root = Path(__file__).parent.parent
    for name in DIRS_TO_REMOVE:
        path = root / name
        if path.exists():
            shutil.rmtree(path)
            print(f"Removed {name}/")
    for pattern in PATTERNS_TO_REMOVE:
        for path in root.glob(pattern):
            shutil.rmtree(path)
            print(f"Removed {path.name}/")
    print("Clean complete.")

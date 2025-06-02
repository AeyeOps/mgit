"""
mgit - Multi-provider Git management tool
"""

import sys
from pathlib import Path

# Read version from pyproject.toml - it's always there
if getattr(sys, "frozen", False):
    # PyInstaller bundle - pyproject.toml is in the extracted directory
    pyproject_path = Path(sys._MEIPASS) / "pyproject.toml"
else:
    # Normal execution
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

with open(pyproject_path, "r") as f:
    for line in f:
        if line.strip().startswith('version = "'):
            __version__ = line.split('"')[1]
            break

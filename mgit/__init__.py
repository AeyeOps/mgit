"""
mgit - Multi-provider Git management tool
"""

import sys
from pathlib import Path

# Read version using appropriate method based on installation type
if getattr(sys, "frozen", False):
    # PyInstaller bundle - pyproject.toml is in the extracted directory
    pyproject_path = Path(sys._MEIPASS) / "pyproject.toml"
    with open(pyproject_path, "r") as f:
        for line in f:
            if line.strip().startswith('version = "'):
                __version__ = line.split('"')[1]
                break
else:
    # Check if we're in a wheel installation or development environment
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        # Development or source installation
        with open(pyproject_path, "r") as f:
            for line in f:
                if line.strip().startswith('version = "'):
                    __version__ = line.split('"')[1]
                    break
    else:
        # Wheel installation - use importlib.metadata
        try:
            from importlib.metadata import version
            __version__ = version("mgit")
        except ImportError:
            # Fallback for Python < 3.8
            from importlib_metadata import version
            __version__ = version("mgit")

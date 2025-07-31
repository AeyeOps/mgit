"""mgit - Multi-provider Git management tool.

The ``pyproject.toml`` file is packaged so we can read the
version directly when installed as a wheel or bundled with
PyInstaller.
"""

import sys
from importlib import metadata
from pathlib import Path


def _read_version_from_pyproject(path: Path) -> str:
    """Fallback for obtaining the version from a local pyproject file."""
    try:
        with path.open("r") as f:
            for line in f:
                if line.strip().startswith('version = "'):
                    return line.split('"')[1]
    except FileNotFoundError:
        pass
    return "unknown"


def _get_version() -> str:
    """Return the package version, preferring the bundled pyproject."""
    if getattr(sys, "frozen", False):
        pyproject_path = Path(sys._MEIPASS) / "pyproject.toml"
    else:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

    version = _read_version_from_pyproject(pyproject_path)
    if version != "unknown":
        return version

    try:
        return metadata.version("mgit")
    except metadata.PackageNotFoundError:
        return "unknown"


__version__ = _get_version()

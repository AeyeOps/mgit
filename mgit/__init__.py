"""
mgit - Multi-provider Git management tool
"""

try:
    # Try to get version from installed package metadata
    from importlib.metadata import version, PackageNotFoundError
    __version__ = version("mgit")
except (ImportError, PackageNotFoundError):
    # Fallback for development or when package is not installed
    # This will be replaced during build by Poetry
    __version__ = "0.2.6"

"""Constants module for mgit."""

__version__ = "0.4.0"

# Default values used if environment variables and config file don't provide values
DEFAULT_VALUES = {
    "LOG_FILENAME": "mgit.log",
    "LOG_LEVEL": "DEBUG",
    "CON_LEVEL": "INFO",
    "DEFAULT_CONCURRENCY": "4",
    "DEFAULT_UPDATE_MODE": "skip",
}

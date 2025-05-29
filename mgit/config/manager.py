"""Configuration management for mgit."""

import os
from pathlib import Path
from typing import Optional

from dotenv import dotenv_values, load_dotenv

from mgit.constants import DEFAULT_VALUES

# Configuration loading order:
# 1. Environment variables (highest priority)
# 2. Global config file in ~/.config/mgit/config
# 3. Default values (lowest priority)

# First load environment variables
load_dotenv(
    dotenv_path=None,
    verbose=True,
    override=True,
)

# Load global config file if environment variables are not set
CONFIG_DIR = Path.home() / ".config" / "mgit"
CONFIG_FILE = CONFIG_DIR / "config"
# Ensure config directory exists before setting up file logging
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_config_value(key: str, default_value: Optional[str] = None) -> str:
    """
    Get a configuration value with the following priority:
    1. Environment variable
    2. Global config file
    3. Default value
    """
    # First check environment
    env_value = os.environ.get(key)
    if env_value:
        return env_value

    # Then check config file
    if CONFIG_FILE.exists():
        config_values = dotenv_values(dotenv_path=str(CONFIG_FILE))
        if key in config_values and config_values[key]:
            return config_values[key]

    # Finally use default
    return default_value or DEFAULT_VALUES.get(key, "")


def load_config_file() -> dict:
    """Load configuration from the global config file."""
    if CONFIG_FILE.exists():
        return dotenv_values(dotenv_path=str(CONFIG_FILE))
    return {}


def save_config_file(config_values: dict) -> None:
    """Save configuration to the global config file with secure permissions."""
    # Ensure config directory exists
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write config file
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        for k, v in config_values.items():
            f.write(f"{k}={v}\n")
    
    # Set secure permissions on config file
    os.chmod(CONFIG_FILE, 0o600)
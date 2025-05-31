"""Configuration management package for mgit.

This package provides YAML-based configuration management functionality 
for both global settings and provider-specific configurations.
"""

# YAML configuration management
from .yaml_manager import (
    get_provider_configs,
    get_provider_config,
    get_default_provider_config,
    get_default_provider_name,
    list_provider_names,
    detect_provider_type,
    get_global_config,
    get_global_setting,
    add_provider_config,
    remove_provider_config,
    set_default_provider,
    set_global_setting,
    migrate_from_dotenv,
    CONFIG_DIR,
    CONFIG_FILE,
)

__all__ = [
    # Provider config
    "get_provider_configs",
    "get_provider_config", 
    "get_default_provider_config",
    "get_default_provider_name",
    "list_provider_names",
    "detect_provider_type",
    "add_provider_config",
    "remove_provider_config",
    "set_default_provider",
    # Global config
    "get_global_config",
    "get_global_setting",
    "set_global_setting",
    # Migration
    "migrate_from_dotenv",
    # Paths
    "CONFIG_DIR",
    "CONFIG_FILE",
]
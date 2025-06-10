"""Configuration management package for mgit.

This package provides YAML-based configuration management functionality
for both global settings and provider-specific configurations.
"""

# YAML configuration management
from .yaml_manager import (
    CONFIG_DIR,
    CONFIG_FILE,
    add_provider_config,
    detect_provider_type,
    get_default_provider_config,
    get_default_provider_name,
    get_global_config,
    get_global_setting,
    get_provider_config,
    get_provider_configs,
    list_provider_names,
    remove_provider_config,
    set_default_provider,
    set_global_setting,
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
    # Paths
    "CONFIG_DIR",
    "CONFIG_FILE",
]

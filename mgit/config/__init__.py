"""Configuration management package for mgit.

This package provides configuration management functionality including
general configuration and provider-specific configuration.
"""

# General configuration management
from .manager import (
    get_config_value,
    load_config_file,
    save_config_file,
    CONFIG_DIR,
    CONFIG_FILE,
)

# Provider-specific configuration
from .providers import (
    get_provider_config,
    set_provider_config,
    validate_provider_config,
    get_provider_defaults,
    list_provider_fields,
    get_all_provider_configs,
    clear_provider_config,
    is_provider_configured,
    PROVIDER_AZUREDEVOPS,
    PROVIDER_GITHUB,
    PROVIDER_BITBUCKET,
    SUPPORTED_PROVIDERS,
)

__all__ = [
    # General config
    "get_config_value",
    "load_config_file",
    "save_config_file",
    "CONFIG_DIR",
    "CONFIG_FILE",
    # Provider config
    "get_provider_config",
    "set_provider_config",
    "validate_provider_config",
    "get_provider_defaults",
    "list_provider_fields",
    "get_all_provider_configs",
    "clear_provider_config",
    "is_provider_configured",
    # Provider constants
    "PROVIDER_AZUREDEVOPS",
    "PROVIDER_GITHUB",
    "PROVIDER_BITBUCKET",
    "SUPPORTED_PROVIDERS",
]
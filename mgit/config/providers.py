"""Provider-specific configuration management for mgit.

This module handles configuration for different git providers (Azure DevOps, GitHub, BitBucket)
with provider-specific defaults, validation, and integration with the main config system.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum

from mgit.config.manager import get_config_value, load_config_file, save_config_file, CONFIG_FILE
from mgit.providers.base import AuthMethod


class ProviderType(Enum):
    """Supported provider types."""
    AZURE_DEVOPS = "azuredevops"
    GITHUB = "github"
    BITBUCKET = "bitbucket"


# Default configurations for each provider
PROVIDER_DEFAULTS = {
    ProviderType.AZURE_DEVOPS: {
        "api_version": "7.1",
        "auth_method": AuthMethod.PAT.value,
        "concurrent_connections": "4",
        "timeout": "30",
        "retry_count": "3",
        "retry_delay": "1",
        "verify_ssl": "true",
        "default_branch": "main",
        "clone_depth": "0",  # 0 means full clone
        "fetch_tags": "true",
        "use_ssh": "false",
    },
    ProviderType.GITHUB: {
        "api_version": "2022-11-28",
        "auth_method": AuthMethod.PAT.value,
        "concurrent_connections": "10",
        "timeout": "30",
        "retry_count": "3",
        "retry_delay": "1",
        "verify_ssl": "true",
        "default_branch": "main",
        "clone_depth": "0",
        "fetch_tags": "true",
        "use_ssh": "false",
        "per_page": "100",  # GitHub-specific pagination
        "api_base_url": "https://api.github.com",
    },
    ProviderType.BITBUCKET: {
        "api_version": "2.0",
        "auth_method": AuthMethod.APP_PASSWORD.value,
        "concurrent_connections": "5",
        "timeout": "30",
        "retry_count": "3",
        "retry_delay": "1",
        "verify_ssl": "true",
        "default_branch": "main",
        "clone_depth": "0",
        "fetch_tags": "true",
        "use_ssh": "false",
        "pagelen": "100",  # BitBucket-specific pagination
        "api_base_url": "https://api.bitbucket.org",
    },
}


# Provider-specific configuration key patterns
PROVIDER_CONFIG_PATTERNS = {
    ProviderType.AZURE_DEVOPS: {
        "organization": "AZURE_DEVOPS_ORG",
        "organization_url": "AZURE_DEVOPS_ORG_URL",
        "pat": "AZURE_DEVOPS_EXT_PAT",
        "username": "AZURE_DEVOPS_USERNAME",
    },
    ProviderType.GITHUB: {
        "organization": "GITHUB_ORG",
        "pat": "GITHUB_PAT",
        "username": "GITHUB_USERNAME",
        "enterprise_url": "GITHUB_ENTERPRISE_URL",
    },
    ProviderType.BITBUCKET: {
        "workspace": "BITBUCKET_WORKSPACE",
        "username": "BITBUCKET_USERNAME",
        "app_password": "BITBUCKET_APP_PASSWORD",
        "server_url": "BITBUCKET_SERVER_URL",
    },
}


# Required fields for each provider
PROVIDER_REQUIRED_FIELDS = {
    ProviderType.AZURE_DEVOPS: ["organization_url", "pat"],
    ProviderType.GITHUB: ["pat"],  # organization is optional for GitHub
    ProviderType.BITBUCKET: ["workspace", "username", "app_password"],
}


def _get_provider_key(provider: str, key: str) -> str:
    """Generate a provider-specific configuration key.
    
    Args:
        provider: Provider name
        key: Configuration key
        
    Returns:
        Provider-specific key (e.g., AZUREDEVOPS_API_VERSION)
    """
    # Normalize provider name for key generation
    provider_upper = provider.upper().replace("-", "_")
    return f"{provider_upper}_{key.upper()}"


def get_provider_config(provider: str) -> Dict[str, Any]:
    """Get configuration for a specific provider.
    
    This merges default values with user-configured values, with the following priority:
    1. Environment variables (highest)
    2. Provider-specific config file values
    3. General config file values
    4. Provider defaults (lowest)
    
    Args:
        provider: Provider name (azuredevops, github, bitbucket)
        
    Returns:
        Dictionary of provider configuration
        
    Raises:
        ValueError: If provider is not supported
    """
    # Validate provider
    try:
        provider_type = ProviderType(provider.lower())
    except ValueError:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: {', '.join([p.value for p in ProviderType])}"
        )
    
    # Start with defaults
    config = PROVIDER_DEFAULTS[provider_type].copy()
    
    # Add provider-specific pattern keys
    pattern_config = {}
    patterns = PROVIDER_CONFIG_PATTERNS.get(provider_type, {})
    for config_key, env_key in patterns.items():
        value = get_config_value(env_key)
        if value:
            pattern_config[config_key] = value
    
    # Load provider-specific configuration from config file
    all_config = load_config_file()
    for key, value in all_config.items():
        # Check if this is a provider-specific key
        provider_prefix = f"{provider_type.value.upper()}_"
        if key.startswith(provider_prefix):
            # Extract the actual key name
            config_key = key[len(provider_prefix):].lower()
            config[config_key] = value
    
    # Override with environment variables (provider-specific)
    for key in config.keys():
        env_key = _get_provider_key(provider_type.value, key)
        env_value = os.environ.get(env_key)
        if env_value:
            config[key] = env_value
    
    # Merge pattern config (has higher priority)
    config.update(pattern_config)
    
    return config


def set_provider_config(provider: str, key: str, value: str) -> None:
    """Set a provider-specific configuration value.
    
    This saves the value to the config file with a provider-specific prefix.
    
    Args:
        provider: Provider name
        key: Configuration key
        value: Configuration value
        
    Raises:
        ValueError: If provider is not supported
    """
    # Validate provider
    try:
        provider_type = ProviderType(provider.lower())
    except ValueError:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: {', '.join([p.value for p in ProviderType])}"
        )
    
    # Load existing config
    config = load_config_file()
    
    # Set provider-specific key
    config_key = _get_provider_key(provider_type.value, key)
    config[config_key] = value
    
    # Save updated config
    save_config_file(config)


def validate_provider_config(provider: str, config: Optional[Dict[str, Any]] = None) -> List[str]:
    """Validate provider configuration.
    
    Args:
        provider: Provider name
        config: Optional configuration to validate (if None, loads current config)
        
    Returns:
        List of validation errors (empty if valid)
        
    Raises:
        ValueError: If provider is not supported
    """
    # Validate provider
    try:
        provider_type = ProviderType(provider.lower())
    except ValueError:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: {', '.join([p.value for p in ProviderType])}"
        )
    
    # Get configuration to validate
    if config is None:
        config = get_provider_config(provider)
    
    errors = []
    
    # Check required fields
    required_fields = PROVIDER_REQUIRED_FIELDS.get(provider_type, [])
    for field in required_fields:
        if field not in config or not config[field]:
            errors.append(f"Missing required field: {field}")
    
    # Provider-specific validation
    if provider_type == ProviderType.AZURE_DEVOPS:
        # Validate organization URL format
        if "organization_url" in config:
            url = config["organization_url"]
            if not url.startswith(("https://", "http://")):
                errors.append("organization_url must start with http:// or https://")
            if not ("dev.azure.com" in url or "visualstudio.com" in url):
                errors.append("organization_url must be a valid Azure DevOps URL")
    
    elif provider_type == ProviderType.GITHUB:
        # Validate API version format
        if "api_version" in config:
            api_version = config["api_version"]
            # GitHub API versions are in YYYY-MM-DD format
            import re
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", api_version):
                errors.append("GitHub api_version must be in YYYY-MM-DD format")
        
        # If enterprise URL is set, validate it
        if "enterprise_url" in config and config["enterprise_url"]:
            url = config["enterprise_url"]
            if not url.startswith(("https://", "http://")):
                errors.append("enterprise_url must start with http:// or https://")
    
    elif provider_type == ProviderType.BITBUCKET:
        # Validate workspace format (alphanumeric and hyphens)
        if "workspace" in config:
            workspace = config["workspace"]
            import re
            if not re.match(r"^[a-zA-Z0-9-]+$", workspace):
                errors.append("BitBucket workspace must contain only alphanumeric characters and hyphens")
    
    # Validate common numeric fields
    numeric_fields = ["concurrent_connections", "timeout", "retry_count", "retry_delay", "clone_depth"]
    for field in numeric_fields:
        if field in config:
            try:
                value = int(config[field])
                if value < 0:
                    errors.append(f"{field} must be non-negative")
            except (ValueError, TypeError):
                errors.append(f"{field} must be a valid integer")
    
    # Validate boolean fields
    boolean_fields = ["verify_ssl", "fetch_tags", "use_ssh"]
    for field in boolean_fields:
        if field in config:
            value = str(config[field]).lower()
            if value not in ["true", "false", "1", "0", "yes", "no"]:
                errors.append(f"{field} must be a boolean value")
    
    # Validate auth method
    if "auth_method" in config:
        valid_methods = [method.value for method in AuthMethod]
        if config["auth_method"] not in valid_methods:
            errors.append(f"auth_method must be one of: {', '.join(valid_methods)}")
    
    return errors


def get_all_provider_configs() -> Dict[str, Dict[str, Any]]:
    """Get configurations for all supported providers.
    
    Returns:
        Dictionary mapping provider names to their configurations
    """
    configs = {}
    for provider_type in ProviderType:
        configs[provider_type.value] = get_provider_config(provider_type.value)
    return configs


def list_provider_config_keys(provider: str) -> List[str]:
    """List all configuration keys for a provider.
    
    Args:
        provider: Provider name
        
    Returns:
        List of configuration keys
        
    Raises:
        ValueError: If provider is not supported
    """
    # Validate provider
    try:
        provider_type = ProviderType(provider.lower())
    except ValueError:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: {', '.join([p.value for p in ProviderType])}"
        )
    
    # Get default keys
    default_keys = list(PROVIDER_DEFAULTS[provider_type].keys())
    
    # Add pattern keys
    pattern_keys = list(PROVIDER_CONFIG_PATTERNS.get(provider_type, {}).keys())
    
    # Combine and deduplicate
    all_keys = list(set(default_keys + pattern_keys))
    all_keys.sort()
    
    return all_keys


def reset_provider_config(provider: str) -> None:
    """Reset a provider's configuration to defaults.
    
    This removes all provider-specific configuration from the config file.
    
    Args:
        provider: Provider name
        
    Raises:
        ValueError: If provider is not supported
    """
    # Validate provider
    try:
        provider_type = ProviderType(provider.lower())
    except ValueError:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: {', '.join([p.value for p in ProviderType])}"
        )
    
    # Load existing config
    config = load_config_file()
    
    # Remove all provider-specific keys
    provider_prefix = f"{provider_type.value.upper()}_"
    keys_to_remove = [key for key in config.keys() if key.startswith(provider_prefix)]
    
    for key in keys_to_remove:
        config.pop(key, None)
    
    # Also remove pattern-based keys
    patterns = PROVIDER_CONFIG_PATTERNS.get(provider_type, {})
    for env_key in patterns.values():
        config.pop(env_key, None)
    
    # Save updated config
    save_config_file(config)


def migrate_legacy_config() -> None:
    """Migrate legacy configuration to provider-specific format.
    
    This function helps migrate from old config format to new provider-specific format.
    """
    config = load_config_file()
    updates = {}
    
    # Migrate Azure DevOps settings
    if "AZURE_DEVOPS_ORG_URL" in config and "AZUREDEVOPS_ORGANIZATION_URL" not in config:
        updates["AZUREDEVOPS_ORGANIZATION_URL"] = config["AZURE_DEVOPS_ORG_URL"]
    
    if "AZURE_DEVOPS_PAT" in config and "AZUREDEVOPS_PAT" not in config:
        updates["AZUREDEVOPS_PAT"] = config["AZURE_DEVOPS_PAT"]
    
    # Apply updates if any
    if updates:
        config.update(updates)
        save_config_file(config)


def get_provider_defaults(provider: str) -> Dict[str, Any]:
    """Get default configuration values for a provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Dictionary of default values
    """
    if provider not in PROVIDER_DEFAULTS:
        raise ValueError(f"Unknown provider: {provider}")
    return PROVIDER_DEFAULTS[provider].copy()


def list_provider_fields(provider: str) -> List[str]:
    """List all configuration fields for a provider.
    
    Args:
        provider: Provider name
        
    Returns:
        List of field names
    """
    if provider not in PROVIDER_CONFIG_PATTERNS:
        raise ValueError(f"Unknown provider: {provider}")
    return list(PROVIDER_CONFIG_PATTERNS[provider].keys())


def clear_provider_config(provider: str) -> None:
    """Clear all configuration for a specific provider.
    
    Args:
        provider: Provider name
    """
    if provider not in PROVIDER_CONFIG_PATTERNS:
        raise ValueError(f"Unknown provider: {provider}")
    
    config = load_config_file()
    fields = list_provider_fields(provider)
    
    # Remove all provider fields
    for field in fields:
        config.pop(field, None)
    
    save_config_file(config)


def is_provider_configured(provider: str) -> bool:
    """Check if a provider is properly configured.
    
    Args:
        provider: Provider name
        
    Returns:
        True if provider is configured and valid
    """
    errors = validate_provider_config(provider)
    return len(errors) == 0


# Provider constants for export
PROVIDER_AZUREDEVOPS = ProviderType.AZURE_DEVOPS.value
PROVIDER_GITHUB = ProviderType.GITHUB.value
PROVIDER_BITBUCKET = ProviderType.BITBUCKET.value
SUPPORTED_PROVIDERS = [p.value for p in ProviderType]
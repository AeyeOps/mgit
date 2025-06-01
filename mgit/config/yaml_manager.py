"""Modern YAML-based configuration management for mgit.

This module provides a clean YAML-based configuration system that uses
~/.config/mgit/config.yaml as the single source of truth.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "mgit"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Ensure config directory exists
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class ConfigurationManager:
    """Modern YAML-based configuration manager."""

    def __init__(self):
        self._config_cache: Optional[Dict[str, Any]] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not CONFIG_FILE.exists():
            logger.debug(f"Config file not found: {CONFIG_FILE}")
            return {"providers": {}, "global": {}}

        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

                # Ensure required structure
                if "providers" not in config:
                    config["providers"] = {}
                if "global" not in config:
                    config["global"] = {}

                logger.debug(
                    f"Loaded config with {len(config.get('providers', {}))} providers"
                )
                return config

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {"providers": {}, "global": {}}

    def load_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load the complete configuration with caching."""
        if self._config_cache is not None and not force_reload:
            return self._config_cache

        self._config_cache = self._load_config()
        return self._config_cache

    def get_provider_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all named provider configurations."""
        config = self.load_config()
        return config.get("providers", {})

    def get_provider_config(self, name: str) -> Dict[str, Any]:
        """Get a specific named provider configuration."""
        providers = self.get_provider_configs()
        if name not in providers:
            available = list(providers.keys())
            raise ValueError(
                f"Provider configuration '{name}' not found. Available: {available}"
            )
        return providers[name]

    def get_default_provider_name(self) -> Optional[str]:
        """Get the default provider name from global config."""
        config = self.load_config()
        return config.get("global", {}).get("default_provider")

    def get_default_provider_config(self) -> Dict[str, Any]:
        """Get the default provider configuration."""
        default_name = self.get_default_provider_name()
        if not default_name:
            # Try to find any provider as fallback
            providers = self.get_provider_configs()
            if providers:
                default_name = list(providers.keys())[0]
                logger.warning(
                    f"No default provider set, using first available: {default_name}"
                )
            else:
                raise ValueError("No provider configurations found")

        return self.get_provider_config(default_name)

    def get_global_config(self) -> Dict[str, Any]:
        """Get global configuration settings."""
        config = self.load_config()
        return config.get("global", {})

    def list_provider_names(self) -> List[str]:
        """List all configured provider names."""
        return list(self.get_provider_configs().keys())

    def detect_provider_type(self, provider_name: str) -> str:
        """Detect the provider type from configuration structure."""
        config = self.get_provider_config(provider_name)

        # Detect based on configuration keys
        if "org_url" in config and "pat" in config:
            return "azuredevops"
        elif "token" in config:
            return "github"
        elif "app_password" in config and "username" in config:
            return "bitbucket"
        else:
            # Try to infer from name
            name_lower = provider_name.lower()
            if "ado" in name_lower or "azure" in name_lower or "devops" in name_lower:
                return "azuredevops"
            elif "github" in name_lower or "gh" in name_lower:
                return "github"
            elif "bitbucket" in name_lower or "bb" in name_lower:
                return "bitbucket"

            raise ValueError(
                f"Cannot detect provider type for '{provider_name}'. Configuration keys: {list(config.keys())}"
            )

    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to YAML file with secure permissions."""
        try:
            # Ensure config directory exists
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            # Write YAML config
            with CONFIG_FILE.open("w", encoding="utf-8") as f:
                yaml.dump(
                    config, f, default_flow_style=False, indent=2, sort_keys=False
                )

            # Set secure permissions
            os.chmod(CONFIG_FILE, 0o600)

            # Clear cache
            self._config_cache = None

            logger.info(f"Saved configuration to {CONFIG_FILE}")

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    def add_provider_config(self, name: str, provider_config: Dict[str, Any]) -> None:
        """Add or update a named provider configuration."""
        config = self.load_config()
        config["providers"][name] = provider_config
        self.save_config(config)

    def remove_provider_config(self, name: str) -> None:
        """Remove a named provider configuration."""
        config = self.load_config()

        if name not in config["providers"]:
            raise ValueError(f"Provider configuration '{name}' not found")

        del config["providers"][name]

        # If this was the default provider, clear the default
        if config.get("global", {}).get("default_provider") == name:
            config["global"]["default_provider"] = None

        self.save_config(config)

    def set_default_provider(self, name: str) -> None:
        """Set the default provider."""
        config = self.load_config()

        # Verify the provider exists
        if name not in config["providers"]:
            available = list(config["providers"].keys())
            raise ValueError(
                f"Provider configuration '{name}' not found. Available: {available}"
            )

        config["global"]["default_provider"] = name
        self.save_config(config)

    def set_global_setting(self, key: str, value: Any) -> None:
        """Set a global configuration setting."""
        config = self.load_config()
        config["global"][key] = value
        self.save_config(config)


# Global instance
config_manager = ConfigurationManager()


# Public API functions
def get_provider_configs() -> Dict[str, Dict[str, Any]]:
    """Get all named provider configurations."""
    return config_manager.get_provider_configs()


def get_provider_config(name: str) -> Dict[str, Any]:
    """Get a specific named provider configuration."""
    return config_manager.get_provider_config(name)


def get_default_provider_config() -> Dict[str, Any]:
    """Get the default provider configuration."""
    return config_manager.get_default_provider_config()


def get_default_provider_name() -> Optional[str]:
    """Get the default provider name."""
    return config_manager.get_default_provider_name()


def list_provider_names() -> List[str]:
    """List all configured provider names."""
    return config_manager.list_provider_names()


def detect_provider_type(provider_name: str) -> str:
    """Detect the provider type from configuration."""
    return config_manager.detect_provider_type(provider_name)


def get_global_config() -> Dict[str, Any]:
    """Get global configuration settings."""
    return config_manager.get_global_config()


def get_global_setting(key: str, default: Optional[Any] = None) -> Any:
    """Get a specific global setting with optional default.

    Args:
        key: Setting key to retrieve
        default: Default value if key not found

    Returns:
        Setting value or default
    """
    global_config = config_manager.get_global_config()
    return global_config.get(key, default)


def add_provider_config(name: str, provider_config: Dict[str, Any]) -> None:
    """Add or update a named provider configuration."""
    config_manager.add_provider_config(name, provider_config)


def remove_provider_config(name: str) -> None:
    """Remove a named provider configuration."""
    config_manager.remove_provider_config(name)


def set_default_provider(name: str) -> None:
    """Set the default provider."""
    config_manager.set_default_provider(name)


def set_global_setting(key: str, value: Any) -> None:
    """Set a global configuration setting."""
    config_manager.set_global_setting(key, value)


def migrate_from_dotenv() -> bool:
    """Migrate configuration from old dotenv format to YAML.

    Returns:
        bool: True if migration was performed, False if no migration needed
    """
    old_config_file = CONFIG_DIR / "config"  # Old dotenv file

    if not old_config_file.exists():
        return False

    logger.info("Migrating configuration from dotenv to YAML format")

    # Import dotenv_values locally to avoid dependency
    from dotenv import dotenv_values

    # Load old configuration
    old_config = dotenv_values(str(old_config_file))

    # Load current YAML config if exists
    current_config = config_manager.load_config()

    # Map old dotenv keys to new YAML structure
    migrations = {
        # Global settings
        "LOG_FILENAME": ("global", "log_filename"),
        "LOG_LEVEL": ("global", "log_level"),
        "CON_LEVEL": ("global", "console_level"),
        "DEFAULT_CONCURRENCY": ("global", "default_concurrency"),
        "DEFAULT_UPDATE_MODE": ("global", "default_update_mode"),
        # Azure DevOps settings
        "AZURE_DEVOPS_ORG_URL": ("provider", "azuredevops", "org_url"),
        "AZURE_DEVOPS_EXT_PAT": ("provider", "azuredevops", "pat"),
        # GitHub settings
        "GITHUB_ORG_URL": ("provider", "github", "org_url"),
        "GITHUB_PAT": ("provider", "github", "token"),
        # BitBucket settings
        "BITBUCKET_ORG_URL": ("provider", "bitbucket", "org_url"),
        "BITBUCKET_APP_PASSWORD": ("provider", "bitbucket", "app_password"),
        "BITBUCKET_USERNAME": ("provider", "bitbucket", "username"),
    }

    # Apply migrations
    for old_key, new_path in migrations.items():
        if old_key in old_config and old_config[old_key]:
            value = old_config[old_key]

            if new_path[0] == "global":
                # Global setting
                current_config["global"][new_path[1]] = value
            elif new_path[0] == "provider":
                # Provider configuration
                provider_type = new_path[1]
                provider_key = new_path[2]

                # Find or create provider config
                provider_name = f"{provider_type}_migrated"
                if provider_name not in current_config["providers"]:
                    current_config["providers"][provider_name] = {}

                current_config["providers"][provider_name][provider_key] = value

    # Save migrated configuration
    config_manager.save_config(current_config)

    # Rename old config file to backup
    backup_file = old_config_file.with_suffix(".backup")
    old_config_file.rename(backup_file)
    logger.info(f"Old configuration backed up to {backup_file}")

    return True

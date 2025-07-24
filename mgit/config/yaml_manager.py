"""Modern YAML-based configuration management for mgit.

This module provides a clean YAML-based configuration system that uses
~/.config/mgit/config.yaml as the single source of truth.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


# Configuration paths - XDG Base Directory standard
CONFIG_DIR = Path.home() / ".config" / "mgit"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


# Ensure config directory exists
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class ConfigurationManager:
    """Modern YAML-based configuration manager with comment preservation."""

    def __init__(self):
        self._config_cache: Optional[Dict[str, Any]] = None
        self._raw_config_cache: Optional[Any] = None  # Keep ruamel objects for saving
        # Simple ruamel.yaml setup for comment preservation
        self._yaml = YAML()
        self._yaml.preserve_quotes = True
        self._yaml.indent(mapping=2, sequence=4, offset=2)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not CONFIG_FILE.exists():
            logger.debug(f"Config file not found: {CONFIG_FILE}")
            # Create empty CommentedMap
            self._raw_config_cache = self._yaml.map()
            self._raw_config_cache["providers"] = self._yaml.map()
            self._raw_config_cache["global"] = self._yaml.map()
            return {"providers": {}, "global": {}}

        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                raw_config = self._yaml.load(f) or self._yaml.map()

                # Keep raw config for saving with comments
                self._raw_config_cache = raw_config

                # Convert to regular dicts for compatibility
                def to_dict(obj):
                    if hasattr(obj, "items"):
                        return {k: to_dict(v) for k, v in obj.items()}
                    elif hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
                        return [to_dict(item) for item in obj]
                    return obj

                config = to_dict(raw_config)

                # Ensure required structure in both versions
                if "providers" not in config:
                    config["providers"] = {}
                    self._raw_config_cache["providers"] = self._yaml.map()
                if "global" not in config:
                    config["global"] = {}
                    self._raw_config_cache["global"] = self._yaml.map()

                logger.debug(
                    f"Loaded config with {len(config.get('providers', {}))} providers"
                )
                return config

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

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
        """Detect the provider type from the URL."""
        config = self.get_provider_config(provider_name)

        # Detect from URL - the only reliable way
        if "url" not in config:
            raise ValueError(
                f"Missing 'url' field in provider '{provider_name}'. "
                f"Available fields: {list(config.keys())}"
            )

        url_lower = config["url"].lower()
        if "dev.azure.com" in url_lower or "visualstudio.com" in url_lower:
            return "azuredevops"
        elif "github.com" in url_lower:
            return "github"
        elif "bitbucket.org" in url_lower:
            return "bitbucket"
        else:
            raise ValueError(
                f"Cannot detect provider type from URL '{config['url']}' for '{provider_name}'. "
                f"URL must contain: dev.azure.com, visualstudio.com, github.com, or bitbucket.org"
            )

    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to YAML file with comment preservation."""
        try:
            # Ensure config directory exists
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            # Update the raw config to preserve comments
            if self._raw_config_cache is not None:
                # Update existing structure while preserving comments
                for section, data in config.items():
                    if section not in self._raw_config_cache:
                        self._raw_config_cache[section] = self._yaml.map()

                    # Clear and update the section
                    self._raw_config_cache[section].clear()
                    for key, value in data.items():
                        self._raw_config_cache[section][key] = value

                # Write the preserved structure
                with CONFIG_FILE.open("w", encoding="utf-8") as f:
                    self._yaml.dump(self._raw_config_cache, f)
            else:
                # Fallback to direct save
                with CONFIG_FILE.open("w", encoding="utf-8") as f:
                    self._yaml.dump(config, f)

            # Set secure permissions
            os.chmod(CONFIG_FILE, 0o600)

            # Clear cache
            self._config_cache = None
            self._raw_config_cache = None

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

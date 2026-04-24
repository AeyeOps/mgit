"""Modern YAML-based configuration management for mgit.

This module provides a clean YAML-based configuration system that uses
~/.config/mgit/config.yaml as the single source of truth.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from mgit.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


# Configuration paths - XDG Base Directory standard
CONFIG_DIR = Path.home() / ".config" / "mgit"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


# Ensure config directory exists
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


# Matches ${VAR_NAME} where VAR_NAME starts with letter/underscore.
# Bare $VAR and malformed ${... are deliberately left alone.
_ENV_PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env_placeholders(value: Any, path: str = "") -> Any:
    """Recursively expand ``${VAR}`` placeholders in string leaves from os.environ.

    Walks dicts and lists; leaves non-string scalars untouched. Supports partial
    strings and multiple placeholders per string. Raises ``ConfigurationError``
    when a referenced variable is not set, naming both the YAML dotted path and
    the missing variable.

    The helper is pure: the only side effect is raising on unresolved vars.
    """
    if isinstance(value, dict):
        return {
            k: _expand_env_placeholders(v, f"{path}.{k}" if path else str(k))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [
            _expand_env_placeholders(item, f"{path}[{i}]")
            for i, item in enumerate(value)
        ]
    if isinstance(value, str):

        def _substitute(match: re.Match[str]) -> str:
            var_name = match.group(1)
            if var_name not in os.environ:
                location = path or "<root>"
                raise ConfigurationError(
                    f"Unresolved env placeholder ${{{var_name}}} in {location}",
                    details=(
                        f"Set the environment variable {var_name}, or change the "
                        f"value in {CONFIG_FILE}."
                    ),
                )
            return os.environ[var_name]

        return _ENV_PLACEHOLDER_RE.sub(_substitute, value)
    return value


class ConfigurationManager:
    """Modern YAML-based configuration manager with comment preservation."""

    def __init__(self):
        self._config_cache: dict[str, Any] | None = None
        self._raw_config_cache: Any | None = None  # Keep ruamel objects for saving
        # Simple ruamel.yaml setup for comment preservation
        self._yaml = YAML()
        self._yaml.preserve_quotes = True
        self._yaml.indent(mapping=2, sequence=4, offset=2)

    def _load_config(self) -> dict[str, Any]:
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

                # Expand ${VAR} placeholders on the plain-dict copy only.
                # The raw CommentedMap keeps the literals so save_config is
                # round-trip-safe.
                config = _expand_env_placeholders(config)

                logger.debug(
                    f"Loaded config with {len(config.get('providers', {}))} providers"
                )
                return config

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    def load_config(self, force_reload: bool = False) -> dict[str, Any]:
        """Load the complete configuration with caching."""
        if self._config_cache is not None and not force_reload:
            return self._config_cache

        self._config_cache = self._load_config()
        return self._config_cache

    def get_provider_configs(self) -> dict[str, dict[str, Any]]:
        """Get all named provider configurations."""
        config = self.load_config()
        return config.get("providers", {})

    def get_provider_config(self, name: str) -> dict[str, Any]:
        """Get a specific named provider configuration."""
        providers = self.get_provider_configs()
        if name not in providers:
            available = list(providers.keys())
            raise ValueError(
                f"Provider configuration '{name}' not found. Available: {available}"
            )
        return providers[name]

    def get_default_provider_name(self) -> str | None:
        """Get the default provider name from global config."""
        config = self.load_config()
        return config.get("global", {}).get("default_provider")

    def get_default_provider_config(self) -> dict[str, Any]:
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

    def get_global_config(self) -> dict[str, Any]:
        """Get global configuration settings."""
        config = self.load_config()
        return config.get("global", {})

    def list_provider_names(self) -> list[str]:
        """List all configured provider names."""
        return list(self.get_provider_configs().keys())

    def detect_provider_type(self, provider_name: str) -> str:
        """Detect the provider type from the URL."""
        config = self.get_provider_config(provider_name)

        # Explicit type override (for Gitea, custom GitHub Enterprise, etc.)
        if "type" in config:
            return config["type"]

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

    def _merge_preserving_placeholders(self, raw: Any, new: Any, path: str = "") -> Any:
        """Merge ``new`` (plain Python) into ``raw`` (ruamel node) in place.

        Placeholders are a view concern, not a storage concern: ``raw`` holds
        the on-disk literals (including ``${VAR}`` placeholders) and ``new`` is
        the expanded view the caller round-tripped through in-memory edits. For
        each leaf, we keep the raw literal only if it is a placeholder that
        still expands to the caller's value; otherwise we overwrite with the
        caller's value. Unknown keys in ``raw`` are removed to mirror the
        caller's intent.

        Returns the (mutated) ``raw`` node so the scalar branch can replace
        parent-slot values; callers that already hold the container can ignore
        the return.
        """
        # Both sides are dict-shaped: walk key-by-key on ``raw`` in place so
        # comments, anchors, and key ordering survive.
        if isinstance(raw, dict) and isinstance(new, dict):
            # Drop keys the caller removed.
            for stale_key in [k for k in list(raw.keys()) if k not in new]:
                del raw[stale_key]
            for key, new_val in new.items():
                key_path = f"{path}.{key}" if path else str(key)
                if (
                    key in raw
                    and isinstance(raw[key], (dict, list))
                    and isinstance(new_val, (dict, list))
                ):
                    # Recurse into nested containers.
                    self._merge_preserving_placeholders(raw[key], new_val, key_path)
                else:
                    # Scalar-or-shape-change slot: defer to the scalar branch,
                    # which decides whether to keep the placeholder or overwrite.
                    raw[key] = self._merge_scalar_slot(raw.get(key), new_val, key_path)
            return raw

        # List-into-list: v1 replaces element-by-element replacement. Preserving
        # placeholders inside lists would require tracking identity across
        # reorderings, which has no current caller. Wholesale replace instead.
        if isinstance(raw, list) and isinstance(new, list):
            raw.clear()
            raw.extend(new)
            return raw

        # Type mismatch at this level: caller changed shape, so overwrite.
        return new

    def _merge_scalar_slot(self, raw_val: Any, new_val: Any, path: str) -> Any:
        """Decide the stored value for a single leaf slot.

        If ``raw_val`` is a ``${VAR}``-style placeholder string whose expansion
        equals ``new_val``, keep the placeholder; otherwise return ``new_val``.
        Expansion failure (``ConfigurationError`` from an unset variable) is
        treated as a non-match and overwritten.
        """
        if isinstance(raw_val, str) and _ENV_PLACEHOLDER_RE.search(raw_val):
            try:
                expanded = _expand_env_placeholders(raw_val, path)
            except ConfigurationError:
                # Placeholder points at an unset var; caller's literal wins.
                return new_val
            if expanded == new_val:
                return raw_val
        return new_val

    def save_config(self, config: dict[str, Any]) -> None:
        """Save configuration to YAML file with comment preservation."""
        try:
            # Ensure config directory exists
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            # Update the raw config to preserve comments
            if self._raw_config_cache is not None:
                # Merge caller's expanded view back onto the raw node so that
                # ${VAR} placeholders survive when their expansion still
                # matches, and are overwritten only when the caller changed
                # the underlying value.
                self._merge_preserving_placeholders(self._raw_config_cache, config)

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

    def add_provider_config(self, name: str, provider_config: dict[str, Any]) -> None:
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
def get_provider_configs() -> dict[str, dict[str, Any]]:
    """Get all named provider configurations."""
    return config_manager.get_provider_configs()


def get_provider_config(name: str) -> dict[str, Any]:
    """Get a specific named provider configuration."""
    return config_manager.get_provider_config(name)


def get_default_provider_config() -> dict[str, Any]:
    """Get the default provider configuration."""
    return config_manager.get_default_provider_config()


def get_default_provider_name() -> str | None:
    """Get the default provider name."""
    return config_manager.get_default_provider_name()


def list_provider_names() -> list[str]:
    """List all configured provider names."""
    return config_manager.list_provider_names()


def detect_provider_type(provider_name: str) -> str:
    """Detect the provider type from configuration."""
    return config_manager.detect_provider_type(provider_name)


def get_global_config() -> dict[str, Any]:
    """Get global configuration settings."""
    return config_manager.get_global_config()


def get_global_setting(key: str, default: Any | None = None) -> Any:
    """Get a specific global setting with optional default.

    Args:
        key: Setting key to retrieve
        default: Default value if key not found

    Returns:
        Setting value or default
    """
    global_config = config_manager.get_global_config()
    return global_config.get(key, default)


def add_provider_config(name: str, provider_config: dict[str, Any]) -> None:
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

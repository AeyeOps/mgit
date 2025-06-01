"""Security configuration for mgit.

This module provides security configuration management and
secure defaults for the application.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Security configuration management."""

    # Default security settings
    DEFAULT_SETTINGS = {
        # Credential security
        "mask_credentials_in_logs": True,
        "mask_credentials_in_errors": True,
        "validate_credential_format": True,
        "store_credentials_encrypted": False,  # Future feature
        # Input validation
        "strict_path_validation": True,
        "strict_url_validation": True,
        "strict_name_validation": True,
        "max_input_length": 4096,
        # API security
        "verify_ssl_certificates": True,
        "timeout_seconds": 30,
        "max_redirects": 5,
        "rate_limit_enabled": True,
        "rate_limit_requests_per_minute": 60,
        # Git security
        "verify_git_signatures": False,  # Future feature
        "shallow_clone_by_default": True,
        "clone_timeout_minutes": 30,
        # Logging security
        "log_api_calls": True,
        "log_git_operations": True,
        "log_authentication_attempts": True,
        "log_security_events": True,
        "log_level": "INFO",
        # File system security
        "restrict_clone_paths": True,
        "allowed_clone_base_paths": [],  # Empty means no restriction
        "prevent_symlink_traversal": True,
        # Error handling
        "detailed_error_messages": False,  # Prevent info disclosure
        "sanitize_error_messages": True,
        # Development/debug settings
        "debug_mode": False,
        "allow_insecure_connections": False,
    }

    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        """Initialize security configuration.

        Args:
            config_file: Optional path to security configuration file
        """
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.config_file = Path(config_file) if config_file else None

        # Load settings from various sources
        self._load_from_environment()
        if self.config_file:
            self._load_from_file()

        # Validate configuration
        self._validate_settings()

    def _load_from_environment(self):
        """Load security settings from environment variables."""
        env_prefix = "MGIT_SECURITY_"

        for key in self.settings:
            env_key = f"{env_prefix}{key.upper()}"
            env_value = os.getenv(env_key)

            if env_value is not None:
                # Convert string values to appropriate types
                if isinstance(self.settings[key], bool):
                    self.settings[key] = env_value.lower() in ("true", "1", "yes", "on")
                elif isinstance(self.settings[key], int):
                    try:
                        self.settings[key] = int(env_value)
                    except ValueError:
                        logger.warning(
                            f"Invalid integer value for {env_key}: {env_value}"
                        )
                elif isinstance(self.settings[key], list):
                    # Assume comma-separated values
                    self.settings[key] = [
                        item.strip() for item in env_value.split(",") if item.strip()
                    ]
                else:
                    self.settings[key] = env_value

    def _load_from_file(self):
        """Load security settings from configuration file."""
        if not self.config_file or not self.config_file.exists():
            return

        try:
            with open(self.config_file, "r") as f:
                file_settings = json.load(f)

            # Update settings with file values
            for key, value in file_settings.items():
                if key in self.settings:
                    self.settings[key] = value
                else:
                    logger.warning(f"Unknown security setting in config file: {key}")

        except Exception as e:
            logger.error(f"Error loading security config from {self.config_file}: {e}")

    def _validate_settings(self):
        """Validate security settings."""
        # Validate numeric settings
        if self.settings["timeout_seconds"] <= 0:
            logger.warning("Invalid timeout_seconds, using default")
            self.settings["timeout_seconds"] = self.DEFAULT_SETTINGS["timeout_seconds"]

        if self.settings["max_redirects"] < 0:
            logger.warning("Invalid max_redirects, using default")
            self.settings["max_redirects"] = self.DEFAULT_SETTINGS["max_redirects"]

        if self.settings["rate_limit_requests_per_minute"] <= 0:
            logger.warning("Invalid rate_limit_requests_per_minute, using default")
            self.settings["rate_limit_requests_per_minute"] = self.DEFAULT_SETTINGS[
                "rate_limit_requests_per_minute"
            ]

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.settings["log_level"].upper() not in valid_log_levels:
            logger.warning(
                f"Invalid log_level: {self.settings['log_level']}, using INFO"
            )
            self.settings["log_level"] = "INFO"

        # Security warnings for insecure settings
        if self.settings["allow_insecure_connections"]:
            logger.warning("SECURITY: Insecure connections are allowed!")

        if not self.settings["verify_ssl_certificates"]:
            logger.warning("SECURITY: SSL certificate verification is disabled!")

        if self.settings["debug_mode"]:
            logger.warning(
                "SECURITY: Debug mode is enabled - may expose sensitive information!"
            )

        if self.settings["detailed_error_messages"]:
            logger.warning(
                "SECURITY: Detailed error messages enabled - may expose sensitive information!"
            )

    def get(self, key: str, default: Any = None) -> Any:
        """Get security setting value.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value
        """
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set security setting value.

        Args:
            key: Setting key
            value: Setting value
        """
        if key in self.DEFAULT_SETTINGS:
            self.settings[key] = value
            self._validate_settings()
        else:
            logger.warning(f"Unknown security setting: {key}")

    def is_production_secure(self) -> bool:
        """Check if configuration is suitable for production.

        Returns:
            True if configuration meets production security standards
        """
        issues = []

        # Required security settings for production
        required_settings = {
            "mask_credentials_in_logs": True,
            "mask_credentials_in_errors": True,
            "strict_path_validation": True,
            "strict_url_validation": True,
            "verify_ssl_certificates": True,
            "sanitize_error_messages": True,
            "debug_mode": False,
            "allow_insecure_connections": False,
            "detailed_error_messages": False,
        }

        for key, required_value in required_settings.items():
            if self.settings.get(key) != required_value:
                issues.append(
                    f"{key} should be {required_value}, got {self.settings.get(key)}"
                )

        if issues:
            logger.error(f"Production security issues: {issues}")
            return False

        return True

    def get_api_security_settings(self) -> Dict[str, Any]:
        """Get API-related security settings.

        Returns:
            Dictionary of API security settings
        """
        return {
            "verify_ssl": self.settings["verify_ssl_certificates"],
            "timeout": self.settings["timeout_seconds"],
            "max_redirects": self.settings["max_redirects"],
            "allow_insecure": self.settings["allow_insecure_connections"],
        }

    def get_validation_settings(self) -> Dict[str, Any]:
        """Get input validation settings.

        Returns:
            Dictionary of validation settings
        """
        return {
            "strict_path_validation": self.settings["strict_path_validation"],
            "strict_url_validation": self.settings["strict_url_validation"],
            "strict_name_validation": self.settings["strict_name_validation"],
            "max_input_length": self.settings["max_input_length"],
        }

    def get_logging_settings(self) -> Dict[str, Any]:
        """Get logging-related security settings.

        Returns:
            Dictionary of logging settings
        """
        return {
            "mask_credentials": self.settings["mask_credentials_in_logs"],
            "log_api_calls": self.settings["log_api_calls"],
            "log_git_operations": self.settings["log_git_operations"],
            "log_auth_attempts": self.settings["log_authentication_attempts"],
            "log_security_events": self.settings["log_security_events"],
            "log_level": self.settings["log_level"],
        }

    def save_to_file(self, file_path: Optional[Union[str, Path]] = None) -> None:
        """Save current settings to file.

        Args:
            file_path: Optional path to save to (defaults to config_file)
        """
        target_file = Path(file_path) if file_path else self.config_file

        if not target_file:
            raise ValueError("No file path specified for saving configuration")

        # Ensure directory exists
        target_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(target_file, "w") as f:
                json.dump(self.settings, f, indent=2)
            logger.info(f"Security configuration saved to {target_file}")
        except Exception as e:
            logger.error(f"Error saving security configuration: {e}")
            raise


# Global security configuration instance
_security_config: Optional[SecurityConfig] = None


def get_security_settings() -> SecurityConfig:
    """Get global security configuration.

    Returns:
        SecurityConfig instance
    """
    global _security_config

    if _security_config is None:
        # Look for security config file in standard locations
        config_locations = [
            Path.home() / ".config" / "mgit" / "security.json",
            Path.cwd() / "security.json",
            Path(__file__).parent / "security.json",
        ]

        config_file = None
        for location in config_locations:
            if location.exists():
                config_file = location
                break

        _security_config = SecurityConfig(config_file)

    return _security_config


def init_security_config(
    config_file: Optional[Union[str, Path]] = None,
) -> SecurityConfig:
    """Initialize global security configuration.

    Args:
        config_file: Optional path to security configuration file

    Returns:
        SecurityConfig instance
    """
    global _security_config
    _security_config = SecurityConfig(config_file)
    return _security_config


def is_development_mode() -> bool:
    """Check if running in development mode.

    Returns:
        True if in development mode
    """
    return get_security_settings().get("debug_mode", False)


def is_production_secure() -> bool:
    """Check if current configuration is production-ready.

    Returns:
        True if configuration meets production security standards
    """
    return get_security_settings().is_production_secure()


def get_api_timeout() -> int:
    """Get API timeout setting.

    Returns:
        Timeout in seconds
    """
    return get_security_settings().get("timeout_seconds", 30)


def should_verify_ssl() -> bool:
    """Check if SSL verification is enabled.

    Returns:
        True if SSL should be verified
    """
    return get_security_settings().get("verify_ssl_certificates", True)


def should_mask_credentials() -> bool:
    """Check if credentials should be masked in logs.

    Returns:
        True if credentials should be masked
    """
    return get_security_settings().get("mask_credentials_in_logs", True)

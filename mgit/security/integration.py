"""Security integration for mgit providers.

This module provides integration points to apply security controls
to existing mgit components.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import get_security_settings, init_security_config
from .logging import SecurityLogger, setup_secure_logging
from .monitor import get_security_monitor
from .patches import apply_security_patches

logger = SecurityLogger(__name__)


class SecurityIntegration:
    """Main security integration class for mgit."""

    def __init__(self):
        """Initialize security integration."""
        self.security_config = get_security_settings()
        self.monitor = get_security_monitor()
        self.is_initialized = False

    def initialize(self, config_file: Optional[Path] = None) -> None:
        """Initialize security subsystem.

        Args:
            config_file: Optional security configuration file
        """
        if self.is_initialized:
            return

        try:
            # Initialize security configuration
            if config_file:
                init_security_config(config_file)

            # Setup secure logging
            log_settings = self.security_config.get_logging_settings()
            if log_settings["mask_credentials"]:
                setup_secure_logging(
                    log_level=log_settings["log_level"], console_level="INFO"
                )

            # Apply security patches
            apply_security_patches()

            # Log security initialization
            self.monitor.log_event(
                event_type="security_initialized",
                severity="INFO",
                source="security_integration",
                details={
                    "config_file": str(config_file) if config_file else None,
                    "production_secure": self.security_config.is_production_secure(),
                },
            )

            self.is_initialized = True
            logger.info("Security subsystem initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize security subsystem: {e}")
            raise

    def validate_production_readiness(self) -> bool:
        """Validate that security configuration is production-ready.

        Returns:
            True if configuration meets production standards
        """
        if not self.security_config.is_production_secure():
            logger.error("Security configuration not suitable for production")

            # Log specific issues
            issues = self._get_production_issues()
            for issue in issues:
                logger.warning(f"Production issue: {issue}")

            return False

        logger.info("Security configuration validated for production")
        return True

    def get_security_summary(self) -> Dict[str, Any]:
        """Get comprehensive security status summary.

        Returns:
            Security status summary
        """
        monitor_summary = self.monitor.get_security_summary()

        return {
            "security_initialized": self.is_initialized,
            "production_ready": self.security_config.is_production_secure(),
            "security_score": monitor_summary.get("security_score", 0),
            "failed_auth_attempts": monitor_summary.get("metrics", {}).get(
                "failed_auth_attempts", 0
            ),
            "validation_failures": monitor_summary.get("metrics", {}).get(
                "validation_failures", 0
            ),
            "security_events": monitor_summary.get("total_events", 0),
            "recommendations": monitor_summary.get("recommendations", []),
            "configuration": {
                "credential_masking": self.security_config.get(
                    "mask_credentials_in_logs"
                ),
                "ssl_verification": self.security_config.get("verify_ssl_certificates"),
                "strict_validation": self.security_config.get("strict_path_validation"),
                "debug_mode": self.security_config.get("debug_mode"),
            },
        }

    def _get_production_issues(self) -> List[str]:
        """Get list of production security issues.

        Returns:
            List of security issues
        """
        issues = []

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
            current_value = self.security_config.get(key)
            if current_value != required_value:
                issues.append(f"{key} should be {required_value}, got {current_value}")

        return issues


# Global security integration instance
_security_integration: Optional[SecurityIntegration] = None


def get_security_integration() -> SecurityIntegration:
    """Get global security integration instance.

    Returns:
        SecurityIntegration instance
    """
    global _security_integration
    if _security_integration is None:
        _security_integration = SecurityIntegration()
    return _security_integration


def initialize_security(config_file: Optional[Path] = None) -> None:
    """Initialize mgit security subsystem.

    Args:
        config_file: Optional security configuration file
    """
    integration = get_security_integration()
    integration.initialize(config_file)


def validate_production_security() -> bool:
    """Validate security configuration for production.

    Returns:
        True if configuration is production-ready
    """
    integration = get_security_integration()
    return integration.validate_production_readiness()


def get_security_status() -> Dict[str, Any]:
    """Get current security status.

    Returns:
        Security status summary
    """
    integration = get_security_integration()
    return integration.get_security_summary()


def secure_provider_factory(provider_class):
    """Factory function to create security-enhanced providers.

    Args:
        provider_class: Original provider class

    Returns:
        Security-enhanced provider class
    """
    from .patches import SecureProviderMixin

    class SecureProvider(provider_class, SecureProviderMixin):
        """Provider with security enhancements."""

        def __init__(self, *args, **kwargs):
            # Ensure security is initialized
            if not get_security_integration().is_initialized:
                initialize_security()

            super().__init__(*args, **kwargs)

    SecureProvider.__name__ = f"Secure{provider_class.__name__}"
    SecureProvider.__qualname__ = f"Secure{provider_class.__qualname__}"

    return SecureProvider


def create_security_cli_commands():
    """Create CLI commands for security management.

    This function creates security-related CLI commands that can be
    integrated into the main mgit CLI.
    """
    import typer

    security_app = typer.Typer(name="security", help="Security management commands")

    @security_app.command("status")
    def security_status():
        """Show security status and configuration."""
        status = get_security_status()

        print("=== mgit Security Status ===")
        print(f"Security Initialized: {status['security_initialized']}")
        print(f"Production Ready: {status['production_ready']}")
        print(f"Security Score: {status['security_score']}/100")

        print("\n=== Configuration ===")
        config = status["configuration"]
        for key, value in config.items():
            print(f"{key}: {value}")

        print("\n=== Metrics ===")
        print(f"Failed Auth Attempts: {status['failed_auth_attempts']}")
        print(f"Validation Failures: {status['validation_failures']}")
        print(f"Security Events: {status['security_events']}")

        if status["recommendations"]:
            print("\n=== Recommendations ===")
            for rec in status["recommendations"]:
                print(f"- {rec}")

    @security_app.command("validate")
    def validate_security():
        """Validate security configuration."""
        if validate_production_security():
            print("✅ Security configuration is production-ready")
            typer.Exit(0)
        else:
            print("❌ Security configuration has issues")
            typer.Exit(1)

    @security_app.command("events")
    def show_security_events(
        count: int = typer.Option(10, help="Number of events to show"),
        event_type: Optional[str] = typer.Option(None, help="Filter by event type"),
        severity: Optional[str] = typer.Option(None, help="Filter by severity"),
    ):
        """Show recent security events."""
        monitor = get_security_monitor()
        events = monitor.get_recent_events(count, event_type, severity)

        if not events:
            print("No security events found")
            return

        print(f"=== Last {len(events)} Security Events ===")
        for event in reversed(events):  # Show most recent first
            print(f"{event.timestamp} [{event.severity}] {event.event_type}")
            print(f"  Source: {event.source}")
            print(f"  Details: {event.details}")
            if event.remediation:
                print(f"  Remediation: {event.remediation}")
            print()

    @security_app.command("export")
    def export_security_events(
        output_file: str = typer.Argument(..., help="Output file path"),
        hours: int = typer.Option(24, help="Hours of events to export"),
    ):
        """Export security events to file."""
        monitor = get_security_monitor()
        output_path = Path(output_file)

        try:
            monitor.export_events(output_path, hours)
            print(f"Security events exported to {output_path}")
        except Exception as e:
            print(f"Failed to export events: {e}")
            typer.Exit(1)

    @security_app.command("init")
    def init_security_config(
        config_file: Optional[str] = typer.Option(
            None, help="Security configuration file"
        )
    ):
        """Initialize security configuration."""
        config_path = Path(config_file) if config_file else None

        try:
            initialize_security(config_path)
            print("Security subsystem initialized successfully")
        except Exception as e:
            print(f"Failed to initialize security: {e}")
            typer.Exit(1)

    return security_app


# Convenience function for main module initialization
def setup_mgit_security():
    """Setup security for mgit application.

    This function should be called early in the application startup
    to ensure security controls are in place.
    """
    try:
        # Initialize security with default configuration
        initialize_security()

        # Check if running in production mode
        integration = get_security_integration()
        if not integration.security_config.get("debug_mode", False):
            # In production, validate security configuration
            if not validate_production_security():
                logger.warning("Running with non-production security configuration")

        logger.info("mgit security setup completed")

    except Exception as e:
        logger.error(f"Failed to setup mgit security: {e}")
        # Don't fail the application, but log the error
        pass

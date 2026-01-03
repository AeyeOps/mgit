"""Security-enhanced logging for mgit.

This module provides logging with automatic credential masking and
security event tracking.
"""

import logging
import sys
from pathlib import Path
from typing import Any

from .credentials import CredentialMasker, mask_sensitive_data


class SecurityLogFilter(logging.Filter):
    """Logging filter that masks sensitive data."""

    def __init__(self):
        """Initialize security log filter."""
        super().__init__()
        self.masker = CredentialMasker()

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record and mask sensitive data.

        Args:
            record: Log record to filter

        Returns:
            True to allow the record through
        """
        # Mask sensitive data in message
        if hasattr(record, "msg") and record.msg:
            record.msg = self.masker.mask_string(str(record.msg))

        # Mask sensitive data in arguments
        if hasattr(record, "args") and record.args:
            masked_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    masked_args.append(self.masker.mask_string(arg))
                elif isinstance(arg, dict):
                    masked_args.append(self.masker.mask_dict(arg))
                else:
                    masked_args.append(arg)
            record.args = tuple(masked_args)

        return True


class SecurityLogger:
    """Enhanced logger with automatic credential masking."""

    def __init__(self, name: str, level: int = logging.INFO):
        """Initialize security logger.

        Args:
            name: Logger name
            level: Logging level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Add security filter to mask credentials
        security_filter = SecurityLogFilter()
        self.logger.addFilter(security_filter)

        # Ensure we have at least a console handler
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def debug(self, msg: str, *args, **kwargs):
        """Log debug message with credential masking."""
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """Log info message with credential masking."""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """Log warning message with credential masking."""
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """Log error message with credential masking."""
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """Log critical message with credential masking."""
        self.logger.critical(msg, *args, **kwargs)

    def log_api_call(
        self,
        method: str,
        url: str,
        status_code: int | None = None,
        response_time: float | None = None,
    ):
        """Log API call with masked URL.

        Args:
            method: HTTP method
            url: Request URL (will be masked)
            status_code: Response status code
            response_time: Response time in seconds
        """
        masker = CredentialMasker()
        masked_url = masker.mask_url(url)

        if status_code and response_time:
            self.info(
                f"API {method} {masked_url} -> {status_code} ({response_time:.2f}s)"
            )
        else:
            self.info(f"API {method} {masked_url}")

    def log_git_operation(self, operation: str, repo_url: str, result: str):
        """Log Git operation with masked repository URL.

        Args:
            operation: Git operation (clone, pull, etc.)
            repo_url: Repository URL (will be masked)
            result: Operation result
        """
        masker = CredentialMasker()
        masked_url = masker.mask_url(repo_url)
        self.info(f"Git {operation}: {masked_url} -> {result}")

    def log_authentication(self, provider: str, organization: str, success: bool):
        """Log authentication attempt.

        Args:
            provider: Provider name
            organization: Organization name
            success: Whether authentication succeeded
        """
        status = "SUCCESS" if success else "FAILED"
        self.info(f"Authentication {status}: {provider}:{organization}")

    def log_configuration_load(self, config_path: str, keys_loaded: int):
        """Log configuration loading.

        Args:
            config_path: Path to configuration file
            keys_loaded: Number of configuration keys loaded
        """
        self.info(f"Configuration loaded: {config_path} ({keys_loaded} keys)")

    def log_security_event(self, event_type: str, details: str, severity: str = "INFO"):
        """Log security-related event.

        Args:
            event_type: Type of security event
            details: Event details
            severity: Event severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        log_method = getattr(self.logger, severity.lower(), self.logger.info)
        log_method(f"SECURITY[{event_type}]: {details}")


def get_security_logger(name: str) -> SecurityLogger:
    """Get a security-enhanced logger.

    Args:
        name: Logger name

    Returns:
        SecurityLogger instance
    """
    return SecurityLogger(name)


def setup_secure_logging(
    log_file: str | Path | None = None,
    log_level: str = "INFO",
    console_level: str = "INFO",
) -> None:
    """Set up secure logging configuration.

    Args:
        log_file: Optional log file path
        log_level: File logging level
        console_level: Console logging level
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Add security filter to mask credentials
    security_filter = SecurityLogFilter()
    root_logger.addFilter(security_filter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper()))
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def mask_log_message(message: str) -> str:
    """Mask sensitive data in log message.

    Args:
        message: Log message that may contain sensitive data

    Returns:
        Message with sensitive data masked
    """
    masker = CredentialMasker()
    return masker.mask_string(message)


def log_safe(logger: logging.Logger, level: int, message: str, *args, **kwargs):
    """Log message with automatic credential masking.

    Args:
        logger: Logger instance
        level: Logging level
        message: Message to log
        *args: Message arguments
        **kwargs: Additional logging arguments
    """
    # Apply security filter if not already present
    has_security_filter = any(isinstance(f, SecurityLogFilter) for f in logger.filters)
    if not has_security_filter:
        logger.addFilter(SecurityLogFilter())

    logger.log(level, message, *args, **kwargs)


# Convenience functions for common security logging
def log_credential_exposure_attempt(logger: logging.Logger, context: str, data: str):
    """Log potential credential exposure attempt.

    Args:
        logger: Logger instance
        context: Context where exposure was detected
        data: The data that contained credentials (will be masked)
    """
    masker = CredentialMasker()
    masked_data = masker.mask_string(data)
    logger.warning(
        f"SECURITY: Potential credential exposure in {context}: {masked_data}"
    )


def log_validation_failure(
    logger: logging.Logger, input_type: str, value: str, reason: str
):
    """Log input validation failure.

    Args:
        logger: Logger instance
        input_type: Type of input that failed validation
        value: The input value (will be masked if sensitive)
        reason: Reason for validation failure
    """
    # Mask value if it might be sensitive
    if any(
        keyword in input_type.lower()
        for keyword in ["token", "password", "auth", "secret"]
    ):
        masker = CredentialMasker()
        value = masker.mask_string(value)

    logger.warning(
        f"SECURITY: Input validation failed for {input_type}: {value} - {reason}"
    )


def log_suspicious_activity(
    logger: logging.Logger, activity: str, details: dict[str, Any]
):
    """Log suspicious activity.

    Args:
        logger: Logger instance
        activity: Type of suspicious activity
        details: Activity details (will be masked)
    """
    masked_details = mask_sensitive_data(details)
    logger.warning(
        f"SECURITY: Suspicious activity detected - {activity}: {masked_details}"
    )

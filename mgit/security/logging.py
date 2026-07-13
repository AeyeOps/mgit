"""Security-enhanced logging for mgit.

This module provides logging with automatic credential masking and
security event tracking.
"""

import logging

from .credentials import CredentialMasker


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
    """Enhanced logger with automatic credential masking.

    Emission is left to the standard logging hierarchy (the ``mgit`` logger's
    handlers): attaching handlers or forcing levels here would duplicate
    output — and, with a stdout handler, corrupt ``--format json`` output.
    """

    def __init__(self, name: str):
        """Initialize security logger.

        Args:
            name: Logger name (use a ``mgit.``-prefixed name so records
                propagate to the configured mgit handlers)
        """
        self.logger = logging.getLogger(name)

        # Add the masking filter once; instances may share a logger name.
        if not any(isinstance(f, SecurityLogFilter) for f in self.logger.filters):
            self.logger.addFilter(SecurityLogFilter())

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

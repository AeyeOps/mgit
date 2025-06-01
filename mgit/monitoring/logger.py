"""Structured logging with correlation ID support.

This module provides JSON-formatted structured logging with automatic
correlation ID injection and security-aware credential masking.
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..security.credentials import CredentialMasker
from .correlation import get_correlation_context, get_correlation_id


class StructuredFormatter(logging.Formatter):
    """JSON formatter with correlation ID and structured data support."""

    def __init__(self, include_correlation: bool = True, mask_credentials: bool = True):
        """Initialize structured formatter.

        Args:
            include_correlation: Whether to include correlation ID
            mask_credentials: Whether to mask sensitive credentials
        """
        super().__init__()
        self.include_correlation = include_correlation
        self.mask_credentials = mask_credentials
        if mask_credentials:
            self.masker = CredentialMasker()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log message
        """
        # Base log data
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation context if enabled
        if self.include_correlation:
            correlation_context = get_correlation_context()
            if correlation_context:
                log_data["correlation"] = correlation_context

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": (
                    self.formatException(record.exc_info) if record.exc_info else None
                ),
            }

        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "pathname",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "module",
                "filename",
                "levelno",
                "levelname",
                "exc_info",
                "exc_text",
                "stack_info",
                "getMessage",
            ):
                extra_fields[key] = value

        if extra_fields:
            log_data["extra"] = extra_fields

        # Mask credentials if enabled
        if self.mask_credentials:
            log_data = self._mask_sensitive_data(log_data)

        return json.dumps(log_data, default=str, separators=(",", ":"))

    def _mask_sensitive_data(self, data: Any) -> Any:
        """Recursively mask sensitive data in log data.

        Args:
            data: Data to mask

        Returns:
            Data with sensitive information masked
        """
        if isinstance(data, dict):
            return {
                key: self._mask_sensitive_data(value) for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        elif isinstance(data, str):
            return self.masker.mask_string(data)
        else:
            return data


class StructuredLogger:
    """Enhanced logger with structured JSON output and correlation support."""

    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        include_correlation: bool = True,
        mask_credentials: bool = True,
    ):
        """Initialize structured logger.

        Args:
            name: Logger name
            level: Logging level
            include_correlation: Whether to include correlation ID
            mask_credentials: Whether to mask credentials
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.include_correlation = include_correlation
        self.mask_credentials = mask_credentials

        # Ensure we have structured formatter
        if not any(
            isinstance(h.formatter, StructuredFormatter) for h in self.logger.handlers
        ):
            self._setup_default_handler()

    def _setup_default_handler(self) -> None:
        """Set up default structured handler if none exists."""
        handler = logging.StreamHandler(sys.stdout)
        formatter = StructuredFormatter(
            include_correlation=self.include_correlation,
            mask_credentials=self.mask_credentials,
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _log_with_context(self, level: int, message: str, **kwargs) -> None:
        """Log message with context data.

        Args:
            level: Logging level
            message: Log message
            **kwargs: Additional context data
        """
        # Create extra dict for structured data
        extra = {}

        # Add correlation ID if available and not disabled
        if self.include_correlation:
            correlation_id = get_correlation_id()
            if correlation_id:
                extra["correlation_id"] = correlation_id

        # Add any additional context data
        if kwargs:
            extra.update(kwargs)

        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message with context.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message with context.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        self._log_with_context(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with context.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        self._log_with_context(logging.CRITICAL, message, **kwargs)

    def operation_start(self, operation: str, **kwargs) -> None:
        """Log operation start.

        Args:
            operation: Operation name
            **kwargs: Operation parameters
        """
        self.info(
            f"Operation started: {operation}",
            operation=operation,
            operation_status="started",
            start_time=time.time(),
            **kwargs,
        )

    def operation_end(
        self,
        operation: str,
        success: bool = True,
        duration: Optional[float] = None,
        **kwargs,
    ) -> None:
        """Log operation end.

        Args:
            operation: Operation name
            success: Whether operation succeeded
            duration: Operation duration in seconds
            **kwargs: Additional context
        """
        status = "completed" if success else "failed"
        log_data = {
            "operation": operation,
            "operation_status": status,
            "success": success,
            "end_time": time.time(),
        }

        if duration is not None:
            log_data["duration_seconds"] = duration

        log_data.update(kwargs)

        message = f"Operation {status}: {operation}"
        if duration is not None:
            message += f" (took {duration:.2f}s)"

        log_level = self.info if success else self.error
        log_level(message, **log_data)

    def api_call(
        self,
        method: str,
        url: str,
        status_code: Optional[int] = None,
        response_time: Optional[float] = None,
        **kwargs,
    ) -> None:
        """Log API call.

        Args:
            method: HTTP method
            url: Request URL (will be masked)
            status_code: Response status code
            response_time: Response time in seconds
            **kwargs: Additional context
        """
        log_data = {"api_method": method, "api_url": url, "api_call": True}

        if status_code is not None:
            log_data["api_status_code"] = status_code

        if response_time is not None:
            log_data["api_response_time"] = response_time

        log_data.update(kwargs)

        message = f"API {method} {url}"
        if status_code is not None:
            message += f" -> {status_code}"
        if response_time is not None:
            message += f" ({response_time:.2f}s)"

        # Choose log level based on status code
        if status_code and status_code >= 400:
            log_level = self.warning if status_code < 500 else self.error
        else:
            log_level = self.info

        log_level(message, **log_data)

    def git_operation(
        self, operation: str, repository: str, success: bool = True, **kwargs
    ) -> None:
        """Log Git operation.

        Args:
            operation: Git operation (clone, pull, push, etc.)
            repository: Repository URL or name
            success: Whether operation succeeded
            **kwargs: Additional context
        """
        log_data = {
            "git_operation": operation,
            "repository": repository,
            "success": success,
        }
        log_data.update(kwargs)

        status = "completed" if success else "failed"
        message = f"Git {operation} {status}: {repository}"

        log_level = self.info if success else self.error
        log_level(message, **log_data)

    def authentication(
        self, provider: str, organization: str, success: bool, **kwargs
    ) -> None:
        """Log authentication attempt.

        Args:
            provider: Provider name
            organization: Organization name
            success: Whether authentication succeeded
            **kwargs: Additional context
        """
        log_data = {
            "auth_provider": provider,
            "auth_organization": organization,
            "auth_success": success,
        }
        log_data.update(kwargs)

        status = "successful" if success else "failed"
        message = f"Authentication {status}: {provider}:{organization}"

        log_level = self.info if success else self.warning
        log_level(message, **log_data)

    def performance_metric(
        self, metric_name: str, value: float, unit: str = "seconds", **kwargs
    ) -> None:
        """Log performance metric.

        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit
            **kwargs: Additional context
        """
        self.info(
            f"Performance metric: {metric_name} = {value} {unit}",
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            metric_type="performance",
            **kwargs,
        )

    def security_event(
        self, event_type: str, severity: str, details: str, **kwargs
    ) -> None:
        """Log security event.

        Args:
            event_type: Type of security event
            severity: Event severity
            details: Event details
            **kwargs: Additional context
        """
        log_data = {
            "security_event_type": event_type,
            "security_severity": severity,
            "security_details": details,
        }
        log_data.update(kwargs)

        message = f"SECURITY[{event_type}]: {details}"

        # Choose log level based on severity
        severity_levels = {
            "DEBUG": self.debug,
            "INFO": self.info,
            "WARNING": self.warning,
            "ERROR": self.error,
            "CRITICAL": self.critical,
        }

        log_level = severity_levels.get(severity.upper(), self.info)
        log_level(message, **log_data)


# Global structured loggers
_structured_loggers: Dict[str, StructuredLogger] = {}


def get_structured_logger(
    name: str,
    level: int = logging.INFO,
    include_correlation: bool = True,
    mask_credentials: bool = True,
) -> StructuredLogger:
    """Get or create a structured logger.

    Args:
        name: Logger name
        level: Logging level
        include_correlation: Whether to include correlation ID
        mask_credentials: Whether to mask credentials

    Returns:
        StructuredLogger instance
    """
    key = f"{name}:{level}:{include_correlation}:{mask_credentials}"
    if key not in _structured_loggers:
        _structured_loggers[key] = StructuredLogger(
            name=name,
            level=level,
            include_correlation=include_correlation,
            mask_credentials=mask_credentials,
        )
    return _structured_loggers[key]


def setup_structured_logging(
    log_file: Optional[Union[str, Path]] = None,
    log_level: str = "INFO",
    console_level: str = "INFO",
    include_correlation: bool = True,
    mask_credentials: bool = True,
) -> None:
    """Set up structured logging configuration.

    Args:
        log_file: Optional log file path
        log_level: File logging level
        console_level: Console logging level
        include_correlation: Whether to include correlation ID
        mask_credentials: Whether to mask credentials
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler with structured formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper()))
    console_formatter = StructuredFormatter(
        include_correlation=include_correlation, mask_credentials=mask_credentials
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = StructuredFormatter(
            include_correlation=include_correlation, mask_credentials=mask_credentials
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

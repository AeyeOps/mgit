"""Correlation ID management for request tracing.

This module provides correlation ID functionality to track operations
across multiple components and log entries.
"""

import threading
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Optional


class CorrelationContext:
    """Thread-local correlation context for request tracing."""

    def __init__(self):
        """Initialize correlation context."""
        self._local = threading.local()

    def get_correlation_id(self) -> Optional[str]:
        """Get current correlation ID.

        Returns:
            Current correlation ID or None if not set
        """
        return getattr(self._local, "correlation_id", None)

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for current thread.

        Args:
            correlation_id: Correlation ID to set
        """
        self._local.correlation_id = correlation_id

    def clear_correlation_id(self) -> None:
        """Clear correlation ID for current thread."""
        if hasattr(self._local, "correlation_id"):
            delattr(self._local, "correlation_id")

    def get_context(self) -> Dict[str, Any]:
        """Get all correlation context data.

        Returns:
            Dictionary of correlation context data
        """
        context = {}
        correlation_id = self.get_correlation_id()
        if correlation_id:
            context["correlation_id"] = correlation_id

        # Add any other context data stored
        for attr_name in dir(self._local):
            if not attr_name.startswith("_") and attr_name != "correlation_id":
                context[attr_name] = getattr(self._local, attr_name)

        return context

    def set_context_data(self, key: str, value: Any) -> None:
        """Set additional context data.

        Args:
            key: Context key
            value: Context value
        """
        setattr(self._local, key, value)

    def get_context_data(self, key: str, default: Any = None) -> Any:
        """Get context data by key.

        Args:
            key: Context key
            default: Default value if key not found

        Returns:
            Context value or default
        """
        return getattr(self._local, key, default)


# Global correlation context instance
_correlation_context = CorrelationContext()


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID.

    Returns:
        Current correlation ID or None if not set
    """
    return _correlation_context.get_correlation_id()


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set correlation ID for current thread.

    Args:
        correlation_id: Correlation ID to set, generates new one if None

    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    _correlation_context.set_correlation_id(correlation_id)
    return correlation_id


def clear_correlation_id() -> None:
    """Clear correlation ID for current thread."""
    _correlation_context.clear_correlation_id()


def get_correlation_context() -> Dict[str, Any]:
    """Get current correlation context.

    Returns:
        Dictionary of correlation context data
    """
    return _correlation_context.get_context()


def set_context_data(key: str, value: Any) -> None:
    """Set additional context data.

    Args:
        key: Context key
        value: Context value
    """
    _correlation_context.set_context_data(key, value)


def get_context_data(key: str, default: Any = None) -> Any:
    """Get context data by key.

    Args:
        key: Context key
        default: Default value if key not found

    Returns:
        Context value or default
    """
    return _correlation_context.get_context_data(key, default)


@contextmanager
def correlation_context(correlation_id: Optional[str] = None, **context_data):
    """Context manager for correlation ID and additional context.

    Args:
        correlation_id: Correlation ID to set, generates new one if None
        **context_data: Additional context data to set

    Yields:
        The correlation ID
    """
    # Store previous state
    previous_correlation_id = get_correlation_id()
    previous_context = {}

    try:
        # Set new correlation ID
        actual_correlation_id = set_correlation_id(correlation_id)

        # Set additional context data and store previous values
        for key, value in context_data.items():
            previous_context[key] = get_context_data(key)
            set_context_data(key, value)

        yield actual_correlation_id

    finally:
        # Restore previous state
        if previous_correlation_id is not None:
            set_correlation_id(previous_correlation_id)
        else:
            clear_correlation_id()

        # Restore previous context data
        for key, previous_value in previous_context.items():
            if previous_value is not None:
                set_context_data(key, previous_value)
            else:
                # Clear the context data if it wasn't set before
                if hasattr(_correlation_context._local, key):
                    delattr(_correlation_context._local, key)


@contextmanager
def operation_context(operation_name: str, **context_data):
    """Context manager for operation tracking.

    Args:
        operation_name: Name of the operation
        **context_data: Additional context data

    Yields:
        The correlation ID for the operation
    """
    with correlation_context(
        operation=operation_name, **context_data
    ) as correlation_id:
        yield correlation_id


@contextmanager
def provider_context(provider_name: str, organization: str = None, **context_data):
    """Context manager for provider operations.

    Args:
        provider_name: Name of the provider (github, azure-devops, bitbucket)
        organization: Organization name
        **context_data: Additional context data

    Yields:
        The correlation ID for the provider operation
    """
    context = {"provider": provider_name}
    if organization:
        context["organization"] = organization
    context.update(context_data)

    with correlation_context(**context) as correlation_id:
        yield correlation_id


@contextmanager
def git_operation_context(operation: str, repository: str = None, **context_data):
    """Context manager for Git operations.

    Args:
        operation: Git operation (clone, pull, push, etc.)
        repository: Repository name or URL
        **context_data: Additional context data

    Yields:
        The correlation ID for the Git operation
    """
    context = {"git_operation": operation}
    if repository:
        context["repository"] = repository
    context.update(context_data)

    with correlation_context(**context) as correlation_id:
        yield correlation_id

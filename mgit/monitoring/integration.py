"""Integration utilities for mgit monitoring.

This module provides integration decorators and utilities to easily
add monitoring to existing mgit components.
"""

import functools
import time
from typing import Any, Callable, Optional, TypeVar

from .correlation import correlation_context, git_operation_context
from .logger import get_structured_logger
from .metrics import get_metrics_collector
from .performance import get_performance_monitor

T = TypeVar("T")


def monitor_mgit_operation(
    operation_name: Optional[str] = None,
    provider: Optional[str] = None,
    track_performance: bool = True,
    log_result: bool = True,
):
    """Decorator to monitor mgit operations with comprehensive tracking.

    Args:
        operation_name: Custom operation name (defaults to function name)
        provider: Provider name for the operation
        track_performance: Whether to track performance metrics
        log_result: Whether to log operation results
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        actual_operation_name = operation_name or func.__name__
        logger = get_structured_logger(f"mgit.{func.__module__}")
        metrics = get_metrics_collector()
        performance_monitor = get_performance_monitor()

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Set up correlation context
            context_data = {}
            if provider:
                context_data["provider"] = provider

            with correlation_context(operation=actual_operation_name, **context_data):
                # Start performance tracking
                operation_id = None
                if track_performance:
                    operation_id = performance_monitor.start_trace(
                        actual_operation_name,
                        tags={"provider": provider} if provider else None,
                    )

                start_time = time.time()

                try:
                    # Log operation start
                    if log_result:
                        logger.operation_start(actual_operation_name, provider=provider)

                    # Execute operation
                    result = func(*args, **kwargs)

                    # Calculate duration
                    duration = time.time() - start_time

                    # Record metrics
                    metrics.record_operation(
                        operation=actual_operation_name,
                        success=True,
                        duration=duration,
                        provider=provider,
                    )

                    # End performance tracking
                    if track_performance and operation_id:
                        performance_monitor.end_trace(operation_id, success=True)

                    # Log operation success
                    if log_result:
                        logger.operation_end(
                            actual_operation_name, success=True, duration=duration
                        )

                    return result

                except Exception as e:
                    # Calculate duration
                    duration = time.time() - start_time

                    # Record metrics
                    metrics.record_operation(
                        operation=actual_operation_name,
                        success=False,
                        duration=duration,
                        provider=provider,
                    )

                    # Record error
                    metrics.record_error(
                        error_type=type(e).__name__,
                        operation=actual_operation_name,
                        provider=provider,
                    )

                    # End performance tracking
                    if track_performance and operation_id:
                        performance_monitor.end_trace(
                            operation_id, success=False, error=str(e)
                        )

                    # Log operation failure
                    if log_result:
                        logger.operation_end(
                            actual_operation_name, success=False, duration=duration
                        )
                        logger.error(
                            f"Operation {actual_operation_name} failed: {str(e)}",
                            error=str(e),
                            error_type=type(e).__name__,
                        )

                    raise

        return wrapper

    return decorator


def monitor_async_mgit_operation(
    operation_name: Optional[str] = None,
    provider: Optional[str] = None,
    track_performance: bool = True,
    log_result: bool = True,
):
    """Async version of monitor_mgit_operation decorator.

    Args:
        operation_name: Custom operation name (defaults to function name)
        provider: Provider name for the operation
        track_performance: Whether to track performance metrics
        log_result: Whether to log operation results
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        actual_operation_name = operation_name or func.__name__
        logger = get_structured_logger(f"mgit.{func.__module__}")
        metrics = get_metrics_collector()
        performance_monitor = get_performance_monitor()

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Set up correlation context
            context_data = {}
            if provider:
                context_data["provider"] = provider

            with correlation_context(operation=actual_operation_name, **context_data):
                # Start performance tracking
                operation_id = None
                if track_performance:
                    operation_id = performance_monitor.start_trace(
                        actual_operation_name,
                        tags={"provider": provider} if provider else None,
                    )

                start_time = time.time()

                try:
                    # Log operation start
                    if log_result:
                        logger.operation_start(actual_operation_name, provider=provider)

                    # Execute operation
                    result = await func(*args, **kwargs)

                    # Calculate duration
                    duration = time.time() - start_time

                    # Record metrics
                    metrics.record_operation(
                        operation=actual_operation_name,
                        success=True,
                        duration=duration,
                        provider=provider,
                    )

                    # End performance tracking
                    if track_performance and operation_id:
                        performance_monitor.end_trace(operation_id, success=True)

                    # Log operation success
                    if log_result:
                        logger.operation_end(
                            actual_operation_name, success=True, duration=duration
                        )

                    return result

                except Exception as e:
                    # Calculate duration
                    duration = time.time() - start_time

                    # Record metrics
                    metrics.record_operation(
                        operation=actual_operation_name,
                        success=False,
                        duration=duration,
                        provider=provider,
                    )

                    # Record error
                    metrics.record_error(
                        error_type=type(e).__name__,
                        operation=actual_operation_name,
                        provider=provider,
                    )

                    # End performance tracking
                    if track_performance and operation_id:
                        performance_monitor.end_trace(
                            operation_id, success=False, error=str(e)
                        )

                    # Log operation failure
                    if log_result:
                        logger.operation_end(
                            actual_operation_name, success=False, duration=duration
                        )
                        logger.error(
                            f"Operation {actual_operation_name} failed: {str(e)}",
                            error=str(e),
                            error_type=type(e).__name__,
                        )

                    raise

        return wrapper

    return decorator


def monitor_git_operation(
    operation_type: Optional[str] = None, track_performance: bool = True
):
    """Decorator specifically for Git operations.

    Args:
        operation_type: Git operation type (clone, pull, push, etc.)
        track_performance: Whether to track performance metrics
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        actual_operation_type = operation_type or func.__name__.replace("git_", "")
        logger = get_structured_logger("mgit.git")
        metrics = get_metrics_collector()
        performance_monitor = get_performance_monitor()

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Try to extract repository from arguments
            repository = None
            if args:
                # Check if first argument looks like a repository URL or name
                if isinstance(args[0], str) and ("/" in args[0] or ".git" in args[0]):
                    repository = args[0]

            # Look for repository in kwargs
            if not repository:
                repository = (
                    kwargs.get("repository")
                    or kwargs.get("repo_url")
                    or kwargs.get("url")
                )

            with git_operation_context(actual_operation_type, repository=repository):
                # Start performance tracking
                operation_id = None
                if track_performance:
                    operation_id = performance_monitor.start_trace(
                        f"git_{actual_operation_type}",
                        tags={"repository": repository} if repository else None,
                    )

                start_time = time.time()

                try:
                    # Log operation start
                    logger.operation_start(
                        f"git_{actual_operation_type}", repository=repository
                    )

                    # Execute operation
                    result = func(*args, **kwargs)

                    # Calculate duration
                    duration = time.time() - start_time

                    # Record Git-specific metrics
                    metrics.record_git_operation(
                        operation=actual_operation_type,
                        repository=repository or "unknown",
                        success=True,
                        duration=duration,
                    )

                    # End performance tracking
                    if track_performance and operation_id:
                        performance_monitor.end_trace(operation_id, success=True)

                    # Log operation success
                    logger.git_operation(
                        actual_operation_type, repository or "unknown", success=True
                    )

                    return result

                except Exception as e:
                    # Calculate duration
                    duration = time.time() - start_time

                    # Record Git-specific metrics
                    metrics.record_git_operation(
                        operation=actual_operation_type,
                        repository=repository or "unknown",
                        success=False,
                        duration=duration,
                    )

                    # End performance tracking
                    if track_performance and operation_id:
                        performance_monitor.end_trace(
                            operation_id, success=False, error=str(e)
                        )

                    # Log operation failure
                    logger.git_operation(
                        actual_operation_type, repository or "unknown", success=False
                    )
                    logger.error(
                        f"Git {actual_operation_type} failed: {str(e)}",
                        error=str(e),
                        error_type=type(e).__name__,
                    )

                    raise

        return wrapper

    return decorator


def monitor_provider_api_call(
    provider_name: Optional[str] = None, endpoint: Optional[str] = None
):
    """Decorator for monitoring provider API calls.

    Args:
        provider_name: Name of the provider
        endpoint: API endpoint being called
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        logger = get_structured_logger("mgit.providers")
        metrics = get_metrics_collector()

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Extract provider from args/kwargs if not specified
            actual_provider = provider_name
            if not actual_provider and args and hasattr(args[0], "provider_name"):
                actual_provider = args[0].provider_name

            start_time = time.time()

            try:
                # Execute API call
                result = func(*args, **kwargs)

                # Calculate duration
                duration = time.time() - start_time

                # Record API call metrics (assuming success if no exception)
                if actual_provider:
                    metrics.record_api_call(
                        method="GET",  # Default method
                        provider=actual_provider,
                        status_code=200,  # Assume success
                        duration=duration,
                        endpoint=endpoint,
                    )

                # Log API call
                logger.api_call(
                    method="API",
                    url=endpoint or f"{actual_provider}_api",
                    status_code=200,
                    response_time=duration,
                )

                return result

            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time

                # Record API call metrics (failure)
                if actual_provider:
                    metrics.record_api_call(
                        method="GET",
                        provider=actual_provider,
                        status_code=500,  # Assume server error
                        duration=duration,
                        endpoint=endpoint,
                    )

                # Log API call failure
                logger.api_call(
                    method="API",
                    url=endpoint or f"{actual_provider}_api",
                    status_code=500,
                    response_time=duration,
                )
                logger.error(f"API call to {actual_provider} failed: {str(e)}")

                raise

        return wrapper

    return decorator


def monitor_authentication(provider_name: Optional[str] = None):
    """Decorator for monitoring authentication operations.

    Args:
        provider_name: Name of the provider
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        logger = get_structured_logger("mgit.auth")
        metrics = get_metrics_collector()

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Extract provider and organization from args/kwargs
            actual_provider = provider_name
            organization = None

            if not actual_provider and args and hasattr(args[0], "provider_name"):
                actual_provider = args[0].provider_name

            # Look for organization in kwargs
            organization = kwargs.get("organization") or kwargs.get("org")

            try:
                # Execute authentication
                result = func(*args, **kwargs)

                # Record successful authentication
                if actual_provider:
                    metrics.record_authentication(
                        provider=actual_provider,
                        organization=organization or "unknown",
                        success=True,
                    )

                # Log authentication success
                logger.authentication(
                    provider=actual_provider or "unknown",
                    organization=organization or "unknown",
                    success=True,
                )

                return result

            except Exception as e:
                # Record failed authentication
                if actual_provider:
                    metrics.record_authentication(
                        provider=actual_provider,
                        organization=organization or "unknown",
                        success=False,
                    )

                # Log authentication failure
                logger.authentication(
                    provider=actual_provider or "unknown",
                    organization=organization or "unknown",
                    success=False,
                )
                logger.error(f"Authentication failed for {actual_provider}: {str(e)}")

                raise

        return wrapper

    return decorator


class MonitoringContext:
    """Context manager for operation monitoring."""

    def __init__(
        self,
        operation_name: str,
        provider: Optional[str] = None,
        repository: Optional[str] = None,
        **metadata,
    ):
        """Initialize monitoring context.

        Args:
            operation_name: Name of the operation
            provider: Provider name
            repository: Repository name
            **metadata: Additional metadata
        """
        self.operation_name = operation_name
        self.provider = provider
        self.repository = repository
        self.metadata = metadata

        self.logger = get_structured_logger("mgit.context")
        self.metrics = get_metrics_collector()
        self.performance_monitor = get_performance_monitor()

        self.operation_id = None
        self.start_time = None

    def __enter__(self):
        """Enter monitoring context."""
        self.start_time = time.time()

        # Start performance tracking
        tags = {}
        if self.provider:
            tags["provider"] = self.provider
        if self.repository:
            tags["repository"] = self.repository

        self.operation_id = self.performance_monitor.start_trace(
            self.operation_name, tags=tags, metadata=self.metadata
        )

        # Log operation start
        self.logger.operation_start(
            self.operation_name,
            provider=self.provider,
            repository=self.repository,
            **self.metadata,
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit monitoring context."""
        duration = time.time() - self.start_time if self.start_time else 0
        success = exc_type is None

        # Record metrics
        self.metrics.record_operation(
            operation=self.operation_name,
            success=success,
            duration=duration,
            provider=self.provider,
        )

        if not success:
            self.metrics.record_error(
                error_type=exc_type.__name__ if exc_type else "unknown",
                operation=self.operation_name,
                provider=self.provider,
            )

        # End performance tracking
        if self.operation_id:
            self.performance_monitor.end_trace(
                self.operation_id,
                success=success,
                error=str(exc_val) if exc_val else None,
            )

        # Log operation end
        self.logger.operation_end(
            self.operation_name, success=success, duration=duration
        )

        if not success:
            self.logger.error(f"Operation {self.operation_name} failed: {str(exc_val)}")


def setup_monitoring_integration():
    """Set up monitoring integration for mgit.

    This function should be called during application startup to initialize
    all monitoring components.
    """
    from .logger import setup_structured_logging
    from .metrics import setup_metrics

    # Setup structured logging
    setup_structured_logging(
        log_level="INFO", include_correlation=True, mask_credentials=True
    )

    # Setup metrics collection
    setup_metrics()

    logger = get_structured_logger("mgit.monitoring")
    logger.info(
        "Monitoring integration initialized",
        components=[
            "structured_logging",
            "metrics",
            "health_checks",
            "performance_monitoring",
        ],
    )

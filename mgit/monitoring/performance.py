"""Performance monitoring and instrumentation for mgit.

This module provides performance monitoring capabilities including
operation timing, resource usage tracking, and performance analytics.
"""

import time
import threading
import asyncio
from typing import Dict, List, Optional, Any, Callable, TypeVar, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import contextmanager, asynccontextmanager
from functools import wraps
import statistics

from .logger import get_structured_logger
from .metrics import get_metrics_collector
from .correlation import get_correlation_id

T = TypeVar("T")


@dataclass
class PerformanceTrace:
    """Represents a performance trace for an operation."""

    operation_id: str
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    correlation_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)


@dataclass
class PerformanceMetrics:
    """Performance metrics for an operation or time period."""

    operation_name: str
    count: int
    total_duration: float
    min_duration: float
    max_duration: float
    avg_duration: float
    median_duration: float
    p95_duration: float
    p99_duration: float
    error_count: int
    success_rate: float


class PerformanceMonitor:
    """Performance monitoring and instrumentation system."""

    def __init__(self, max_traces: int = 10000, retention_hours: int = 24):
        """Initialize performance monitor.

        Args:
            max_traces: Maximum number of traces to keep in memory
            retention_hours: Hours to retain performance data
        """
        self.max_traces = max_traces
        self.retention_hours = retention_hours
        self.logger = get_structured_logger("performance_monitor")
        self.metrics = get_metrics_collector()

        # Thread-safe storage
        self.lock = threading.Lock()
        self._traces: Dict[str, PerformanceTrace] = {}
        self._completed_traces: List[PerformanceTrace] = []
        self._operation_metrics: Dict[str, List[float]] = {}
        self._operation_errors: Dict[str, int] = {}

        # Current operation stack (for nested operations)
        self._operation_stack = threading.local()

        # Performance baselines
        self._baselines: Dict[str, Dict[str, float]] = {}

        # Automatic cleanup
        self._last_cleanup = time.time()
        self._cleanup_interval = 3600  # 1 hour

    def start_trace(
        self,
        operation_name: str,
        operation_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start a performance trace.

        Args:
            operation_name: Name of the operation
            operation_id: Optional custom operation ID
            tags: Optional tags for the operation
            metadata: Optional metadata for the operation

        Returns:
            Operation ID for the trace
        """
        if operation_id is None:
            operation_id = f"{operation_name}_{int(time.time() * 1000000)}"

        correlation_id = get_correlation_id()

        # Get parent operation ID if nested
        parent_id = None
        if hasattr(self._operation_stack, "stack") and self._operation_stack.stack:
            parent_id = self._operation_stack.stack[-1]

        trace = PerformanceTrace(
            operation_id=operation_id,
            operation_name=operation_name,
            start_time=time.time(),
            correlation_id=correlation_id,
            tags=tags or {},
            metadata=metadata or {},
            parent_id=parent_id,
        )

        with self.lock:
            self._traces[operation_id] = trace

            # Add to parent's children
            if parent_id and parent_id in self._traces:
                self._traces[parent_id].children.append(operation_id)

        # Add to operation stack
        if not hasattr(self._operation_stack, "stack"):
            self._operation_stack.stack = []
        self._operation_stack.stack.append(operation_id)

        # Record start in metrics
        self.metrics.inc_counter(
            "mgit_performance_operations_started_total",
            labels={"operation": operation_name},
        )

        self.logger.debug(
            f"Started performance trace: {operation_name}",
            operation_id=operation_id,
            operation_name=operation_name,
            parent_id=parent_id,
        )

        return operation_id

    def end_trace(
        self,
        operation_id: str,
        success: bool = True,
        error: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        """End a performance trace.

        Args:
            operation_id: Operation ID to end
            success: Whether the operation succeeded
            error: Error message if operation failed
            additional_metadata: Additional metadata to add

        Returns:
            Operation duration in seconds, or None if trace not found
        """
        end_time = time.time()

        with self.lock:
            trace = self._traces.pop(operation_id, None)
            if not trace:
                self.logger.warning(
                    f"Trace not found: {operation_id}", operation_id=operation_id
                )
                return None

            # Complete the trace
            trace.end_time = end_time
            trace.duration = end_time - trace.start_time

            if additional_metadata:
                trace.metadata.update(additional_metadata)

            if not success and error:
                trace.metadata["error"] = error

            # Store completed trace
            self._completed_traces.append(trace)

            # Keep only recent traces
            if len(self._completed_traces) > self.max_traces:
                self._completed_traces = self._completed_traces[-self.max_traces :]

            # Update operation metrics
            if trace.operation_name not in self._operation_metrics:
                self._operation_metrics[trace.operation_name] = []
            self._operation_metrics[trace.operation_name].append(trace.duration)

            # Track errors
            if not success:
                self._operation_errors[trace.operation_name] = (
                    self._operation_errors.get(trace.operation_name, 0) + 1
                )

        # Remove from operation stack
        if (
            hasattr(self._operation_stack, "stack")
            and self._operation_stack.stack
            and self._operation_stack.stack[-1] == operation_id
        ):
            self._operation_stack.stack.pop()

        # Record metrics
        operation_name = trace.operation_name
        self.metrics.observe_histogram(
            "mgit_performance_operation_duration_seconds",
            trace.duration,
            labels={"operation": operation_name, "success": str(success)},
        )

        self.metrics.inc_counter(
            "mgit_performance_operations_completed_total",
            labels={"operation": operation_name, "success": str(success)},
        )

        if not success:
            self.metrics.inc_counter(
                "mgit_performance_operations_errors_total",
                labels={"operation": operation_name},
            )

        self.logger.info(
            f"Completed performance trace: {operation_name}",
            operation_id=operation_id,
            operation_name=operation_name,
            duration_seconds=trace.duration,
            success=success,
            error=error,
        )

        # Check for performance anomalies
        self._check_performance_anomalies(trace)

        # Cleanup if needed
        self._maybe_cleanup()

        return trace.duration

    def get_current_operation_id(self) -> Optional[str]:
        """Get the current operation ID from the stack.

        Returns:
            Current operation ID or None
        """
        if hasattr(self._operation_stack, "stack") and self._operation_stack.stack:
            return self._operation_stack.stack[-1]
        return None

    def add_trace_metadata(self, operation_id: str, metadata: Dict[str, Any]) -> None:
        """Add metadata to an active trace.

        Args:
            operation_id: Operation ID
            metadata: Metadata to add
        """
        with self.lock:
            if operation_id in self._traces:
                self._traces[operation_id].metadata.update(metadata)

    def get_operation_metrics(
        self, operation_name: str, hours: int = 24
    ) -> Optional[PerformanceMetrics]:
        """Get performance metrics for an operation.

        Args:
            operation_name: Name of the operation
            hours: Hours to look back

        Returns:
            Performance metrics or None if no data
        """
        cutoff_time = time.time() - (hours * 3600)

        with self.lock:
            # Get recent traces for the operation
            recent_traces = [
                trace
                for trace in self._completed_traces
                if (
                    trace.operation_name == operation_name
                    and trace.start_time > cutoff_time
                    and trace.duration is not None
                )
            ]

            if not recent_traces:
                return None

            durations = [trace.duration for trace in recent_traces]
            error_count = self._operation_errors.get(operation_name, 0)

            # Calculate statistics
            count = len(durations)
            total_duration = sum(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            avg_duration = statistics.mean(durations)
            median_duration = statistics.median(durations)

            # Calculate percentiles
            sorted_durations = sorted(durations)
            p95_index = int(0.95 * len(sorted_durations))
            p99_index = int(0.99 * len(sorted_durations))
            p95_duration = (
                sorted_durations[p95_index]
                if p95_index < len(sorted_durations)
                else max_duration
            )
            p99_duration = (
                sorted_durations[p99_index]
                if p99_index < len(sorted_durations)
                else max_duration
            )

            success_rate = ((count - error_count) / count) * 100 if count > 0 else 0

            return PerformanceMetrics(
                operation_name=operation_name,
                count=count,
                total_duration=total_duration,
                min_duration=min_duration,
                max_duration=max_duration,
                avg_duration=avg_duration,
                median_duration=median_duration,
                p95_duration=p95_duration,
                p99_duration=p99_duration,
                error_count=error_count,
                success_rate=success_rate,
            )

    def get_all_operations_summary(
        self, hours: int = 24
    ) -> Dict[str, PerformanceMetrics]:
        """Get performance summary for all operations.

        Args:
            hours: Hours to look back

        Returns:
            Dictionary of operation metrics
        """
        cutoff_time = time.time() - (hours * 3600)

        with self.lock:
            recent_traces = [
                trace
                for trace in self._completed_traces
                if trace.start_time > cutoff_time and trace.duration is not None
            ]

        # Group by operation name
        operations = {}
        for trace in recent_traces:
            if trace.operation_name not in operations:
                operations[trace.operation_name] = []
            operations[trace.operation_name].append(trace)

        # Calculate metrics for each operation
        summary = {}
        for operation_name, traces in operations.items():
            durations = [trace.duration for trace in traces]
            error_count = sum(1 for trace in traces if "error" in trace.metadata)

            if durations:
                count = len(durations)
                total_duration = sum(durations)
                min_duration = min(durations)
                max_duration = max(durations)
                avg_duration = statistics.mean(durations)
                median_duration = statistics.median(durations)

                sorted_durations = sorted(durations)
                p95_index = int(0.95 * len(sorted_durations))
                p99_index = int(0.99 * len(sorted_durations))
                p95_duration = (
                    sorted_durations[p95_index]
                    if p95_index < len(sorted_durations)
                    else max_duration
                )
                p99_duration = (
                    sorted_durations[p99_index]
                    if p99_index < len(sorted_durations)
                    else max_duration
                )

                success_rate = ((count - error_count) / count) * 100 if count > 0 else 0

                summary[operation_name] = PerformanceMetrics(
                    operation_name=operation_name,
                    count=count,
                    total_duration=total_duration,
                    min_duration=min_duration,
                    max_duration=max_duration,
                    avg_duration=avg_duration,
                    median_duration=median_duration,
                    p95_duration=p95_duration,
                    p99_duration=p99_duration,
                    error_count=error_count,
                    success_rate=success_rate,
                )

        return summary

    def set_performance_baseline(
        self, operation_name: str, baseline_metrics: Dict[str, float]
    ) -> None:
        """Set performance baseline for an operation.

        Args:
            operation_name: Operation name
            baseline_metrics: Baseline metrics (avg_duration, p95_duration, etc.)
        """
        with self.lock:
            self._baselines[operation_name] = baseline_metrics.copy()

        self.logger.info(
            f"Set performance baseline for {operation_name}",
            operation_name=operation_name,
            baseline_metrics=baseline_metrics,
        )

    def _check_performance_anomalies(self, trace: PerformanceTrace) -> None:
        """Check for performance anomalies in a completed trace.

        Args:
            trace: Completed performance trace
        """
        operation_name = trace.operation_name

        # Check against baseline if available
        with self.lock:
            baseline = self._baselines.get(operation_name)

        if baseline and trace.duration:
            # Check if duration exceeds baseline thresholds
            baseline_avg = baseline.get("avg_duration", 0)
            baseline_p95 = baseline.get("p95_duration", 0)

            if baseline_avg > 0 and trace.duration > baseline_avg * 3:
                self.logger.warning(
                    f"Performance anomaly: {operation_name} took {trace.duration:.2f}s (baseline avg: {baseline_avg:.2f}s)",
                    operation_id=trace.operation_id,
                    operation_name=operation_name,
                    duration=trace.duration,
                    baseline_avg=baseline_avg,
                    anomaly_type="slow_operation",
                )

                self.metrics.inc_counter(
                    "mgit_performance_anomalies_total",
                    labels={"operation": operation_name, "type": "slow_operation"},
                )

            elif baseline_p95 > 0 and trace.duration > baseline_p95 * 2:
                self.logger.warning(
                    f"Performance anomaly: {operation_name} exceeded P95 baseline",
                    operation_id=trace.operation_id,
                    operation_name=operation_name,
                    duration=trace.duration,
                    baseline_p95=baseline_p95,
                    anomaly_type="p95_exceeded",
                )

                self.metrics.inc_counter(
                    "mgit_performance_anomalies_total",
                    labels={"operation": operation_name, "type": "p95_exceeded"},
                )

    def _maybe_cleanup(self) -> None:
        """Clean up old performance data if needed."""
        current_time = time.time()

        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_data()
            self._last_cleanup = current_time

    def _cleanup_old_data(self) -> None:
        """Clean up old performance data."""
        cutoff_time = time.time() - (self.retention_hours * 3600)

        with self.lock:
            # Remove old completed traces
            self._completed_traces = [
                trace
                for trace in self._completed_traces
                if trace.start_time > cutoff_time
            ]

            # Clean up operation metrics
            for operation_name in list(self._operation_metrics.keys()):
                # Keep only recent durations (this is approximate)
                if len(self._operation_metrics[operation_name]) > 1000:
                    self._operation_metrics[operation_name] = self._operation_metrics[
                        operation_name
                    ][-500:]

        self.logger.debug(
            "Cleaned up old performance data",
            cutoff_time=cutoff_time,
            traces_count=len(self._completed_traces),
        )

    @contextmanager
    def trace_operation(
        self,
        operation_name: str,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for tracing an operation.

        Args:
            operation_name: Name of the operation
            tags: Optional tags
            metadata: Optional metadata

        Yields:
            Operation ID
        """
        operation_id = self.start_trace(operation_name, tags=tags, metadata=metadata)

        try:
            yield operation_id
            self.end_trace(operation_id, success=True)
        except Exception as e:
            self.end_trace(operation_id, success=False, error=str(e))
            raise

    @asynccontextmanager
    async def async_trace_operation(
        self,
        operation_name: str,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Async context manager for tracing an operation.

        Args:
            operation_name: Name of the operation
            tags: Optional tags
            metadata: Optional metadata

        Yields:
            Operation ID
        """
        operation_id = self.start_trace(operation_name, tags=tags, metadata=metadata)

        try:
            yield operation_id
            self.end_trace(operation_id, success=True)
        except Exception as e:
            self.end_trace(operation_id, success=False, error=str(e))
            raise


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance.

    Returns:
        PerformanceMonitor instance
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# Decorators for automatic performance monitoring


def monitor_performance(
    operation_name: Optional[str] = None, tags: Optional[Dict[str, str]] = None
):
    """Decorator to monitor function performance.

    Args:
        operation_name: Custom operation name (defaults to function name)
        tags: Optional tags for the operation
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        actual_operation_name = operation_name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            monitor = get_performance_monitor()
            with monitor.trace_operation(actual_operation_name, tags=tags):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def monitor_async_performance(
    operation_name: Optional[str] = None, tags: Optional[Dict[str, str]] = None
):
    """Decorator to monitor async function performance.

    Args:
        operation_name: Custom operation name (defaults to function name)
        tags: Optional tags for the operation
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        actual_operation_name = operation_name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            monitor = get_performance_monitor()
            async with monitor.async_trace_operation(actual_operation_name, tags=tags):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


# Convenience functions


def start_operation_timer(operation_name: str, **kwargs) -> str:
    """Start timing an operation.

    Args:
        operation_name: Name of the operation
        **kwargs: Additional arguments for start_trace

    Returns:
        Operation ID
    """
    monitor = get_performance_monitor()
    return monitor.start_trace(operation_name, **kwargs)


def end_operation_timer(operation_id: str, **kwargs) -> Optional[float]:
    """End timing an operation.

    Args:
        operation_id: Operation ID to end
        **kwargs: Additional arguments for end_trace

    Returns:
        Operation duration in seconds
    """
    monitor = get_performance_monitor()
    return monitor.end_trace(operation_id, **kwargs)

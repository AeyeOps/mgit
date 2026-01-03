"""
Pipeline monitoring and metrics for change pipeline operations.

Provides comprehensive monitoring, metrics collection, and performance
tracking for pipeline operations with integration into existing monitoring systems.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import psutil

from mgit.monitoring.monitor import MonitoringSystem

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics that can be collected."""

    COUNTER = "counter"  # Monotonically increasing value
    GAUGE = "gauge"  # Value that can go up or down
    HISTOGRAM = "histogram"  # Distribution of values
    SUMMARY = "summary"  # Similar to histogram but client-side


@dataclass
class PipelineMetric:
    """Represents a pipeline metric."""

    name: str
    value: Any
    metric_type: MetricType
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: datetime | None = None
    description: str | None = None


@dataclass
class OperationMetrics:
    """Metrics collected during a pipeline operation."""

    operation_name: str
    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: float | None = None
    success: bool = False
    error_message: str | None = None
    repositories_processed: int = 0
    files_processed: int = 0
    bytes_processed: int = 0
    compression_ratio: float | None = None
    memory_peak_mb: float | None = None
    cpu_usage_percent: float | None = None

    @property
    def is_completed(self) -> bool:
        """Check if operation has completed."""
        return self.end_time is not None

    def complete(self, success: bool = True, error_message: str | None = None):
        """Mark operation as completed."""
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.success = success
        self.error_message = error_message


class PipelineMonitor:
    """
    Comprehensive monitor for pipeline operations with metrics collection
    and performance tracking capabilities.
    """

    def __init__(self, monitoring_system: MonitoringSystem | None = None):
        """
        Initialize pipeline monitor.

        Args:
            monitoring_system: Optional external monitoring system to integrate with
        """
        self.monitoring_system = monitoring_system
        self.operation_metrics: dict[str, OperationMetrics] = {}
        self.system_metrics_enabled = True

        # Performance tracking
        self.process = psutil.Process()
        self.baseline_memory_mb = self.process.memory_info().rss / 1024 / 1024

        logger.debug("Pipeline monitor initialized")

    def start_operation(
        self, operation_name: str, operation_type: str = "unknown", **context
    ) -> str:
        """
        Start tracking a pipeline operation.

        Args:
            operation_name: Name of the operation
            operation_type: Type of operation (diff, clone, compress, etc.)
            **context: Additional context information

        Returns:
            Operation ID for tracking
        """
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"

        metrics = OperationMetrics(
            operation_name=operation_name,
            start_time=datetime.now(),
            repositories_processed=0,
            files_processed=0,
            bytes_processed=0,
        )

        self.operation_metrics[operation_id] = metrics

        # Record start metrics
        self._record_metric(
            PipelineMetric(
                name="pipeline_operation_started",
                value=1,
                metric_type=MetricType.COUNTER,
                labels={
                    "operation_name": operation_name,
                    "operation_type": operation_type,
                    "operation_id": operation_id,
                },
                description=f"Pipeline operation {operation_name} started",
            )
        )

        # Record system metrics at start
        if self.system_metrics_enabled:
            self._record_system_metrics(operation_id, "start")

        logger.info(
            f"Started monitoring operation: {operation_name} (ID: {operation_id})"
        )

        return operation_id

    def update_operation_progress(
        self,
        operation_id: str,
        repositories_processed: int | None = None,
        files_processed: int | None = None,
        bytes_processed: int | None = None,
        **additional_metrics,
    ):
        """
        Update progress metrics for a running operation.

        Args:
            operation_id: Operation ID from start_operation
            repositories_processed: Number of repositories processed
            files_processed: Number of files processed
            bytes_processed: Number of bytes processed
            **additional_metrics: Additional metrics to record
        """
        if operation_id not in self.operation_metrics:
            logger.warning(f"Unknown operation ID: {operation_id}")
            return

        metrics = self.operation_metrics[operation_id]

        if repositories_processed is not None:
            metrics.repositories_processed = repositories_processed
        if files_processed is not None:
            metrics.files_processed = files_processed
        if bytes_processed is not None:
            metrics.bytes_processed = bytes_processed

        # Record progress metrics
        self._record_metric(
            PipelineMetric(
                name="pipeline_operation_progress",
                value=metrics.repositories_processed,
                metric_type=MetricType.GAUGE,
                labels={
                    "operation_id": operation_id,
                    "operation_name": metrics.operation_name,
                    "metric_type": "repositories_processed",
                },
                description="Number of repositories processed",
            )
        )

        # Record additional metrics
        for metric_name, metric_value in additional_metrics.items():
            self._record_metric(
                PipelineMetric(
                    name=f"pipeline_operation_{metric_name}",
                    value=metric_value,
                    metric_type=MetricType.GAUGE,
                    labels={
                        "operation_id": operation_id,
                        "operation_name": metrics.operation_name,
                    },
                    description=f"Custom metric: {metric_name}",
                )
            )

    def end_operation(
        self,
        operation_id: str,
        success: bool = True,
        error_message: str | None = None,
        compression_ratio: float | None = None,
    ):
        """
        End tracking of a pipeline operation.

        Args:
            operation_id: Operation ID from start_operation
            success: Whether operation completed successfully
            error_message: Error message if operation failed
            compression_ratio: Compression ratio achieved
        """
        if operation_id not in self.operation_metrics:
            logger.warning(f"Unknown operation ID: {operation_id}")
            return

        metrics = self.operation_metrics[operation_id]
        metrics.complete(success, error_message)

        if compression_ratio is not None:
            metrics.compression_ratio = compression_ratio

        # Record final system metrics
        if self.system_metrics_enabled:
            self._record_system_metrics(operation_id, "end")

        # Record completion metrics
        self._record_metric(
            PipelineMetric(
                name="pipeline_operation_completed",
                value=1,
                metric_type=MetricType.COUNTER,
                labels={
                    "operation_id": operation_id,
                    "operation_name": metrics.operation_name,
                    "success": str(success),
                    "duration_seconds": str(metrics.duration_seconds or 0),
                },
                description=f"Pipeline operation {metrics.operation_name} completed",
            )
        )

        # Record performance metrics
        if metrics.duration_seconds:
            self._record_metric(
                PipelineMetric(
                    name="pipeline_operation_duration_seconds",
                    value=metrics.duration_seconds,
                    metric_type=MetricType.HISTOGRAM,
                    labels={
                        "operation_id": operation_id,
                        "operation_name": metrics.operation_name,
                        "success": str(success),
                    },
                    description="Duration of pipeline operation",
                )
            )

        if metrics.compression_ratio:
            self._record_metric(
                PipelineMetric(
                    name="pipeline_compression_ratio",
                    value=metrics.compression_ratio,
                    metric_type=MetricType.GAUGE,
                    labels={
                        "operation_id": operation_id,
                        "operation_name": metrics.operation_name,
                    },
                    description="Compression ratio achieved",
                )
            )

        logger.info(
            f"Completed monitoring operation: {metrics.operation_name} "
            f"(ID: {operation_id}, Success: {success}, "
            f"Duration: {metrics.duration_seconds:.2f}s)"
        )

        # Clean up completed operation
        del self.operation_metrics[operation_id]

    def record_error(
        self,
        operation_id: str | None,
        error_type: str,
        error_message: str,
        **context,
    ):
        """
        Record an error that occurred during pipeline operation.

        Args:
            operation_id: Optional operation ID if error is operation-specific
            error_type: Type/category of error
            error_message: Error message
            **context: Additional error context
        """
        labels = {
            "error_type": error_type,
            "error_message": error_message[:100],  # Truncate long messages
        }

        if operation_id:
            labels["operation_id"] = operation_id

        # Add context as labels
        for key, value in context.items():
            if isinstance(value, str):
                labels[f"context_{key}"] = value[:50]  # Truncate context values

        self._record_metric(
            PipelineMetric(
                name="pipeline_error_occurred",
                value=1,
                metric_type=MetricType.COUNTER,
                labels=labels,
                description=f"Pipeline error: {error_type}",
            )
        )

        logger.error(f"Pipeline error recorded: {error_type} - {error_message}")

    def get_operation_metrics(self, operation_id: str) -> OperationMetrics | None:
        """
        Get metrics for a specific operation.

        Args:
            operation_id: Operation ID to retrieve metrics for

        Returns:
            OperationMetrics if operation exists, None otherwise
        """
        return self.operation_metrics.get(operation_id)

    def get_all_active_operations(self) -> list[OperationMetrics]:
        """Get all currently active operations."""
        return list(self.operation_metrics.values())

    def get_performance_summary(self) -> dict[str, Any]:
        """Get overall performance summary."""
        total_operations = len(self.operation_metrics)
        completed_operations = sum(
            1 for m in self.operation_metrics.values() if m.is_completed
        )
        successful_operations = sum(
            1 for m in self.operation_metrics.values() if m.success
        )
        total_duration = sum(
            m.duration_seconds or 0
            for m in self.operation_metrics.values()
            if m.duration_seconds
        )

        return {
            "active_operations": total_operations,
            "completed_operations": completed_operations,
            "successful_operations": successful_operations,
            "total_duration_seconds": total_duration,
            "average_duration_seconds": total_duration / max(completed_operations, 1),
            "success_rate_percent": (
                successful_operations / max(completed_operations, 1)
            )
            * 100,
        }

    def _record_system_metrics(self, operation_id: str, phase: str):
        """Record system-level metrics (memory, CPU, etc.)."""
        try:
            memory_info = self.process.memory_info()
            current_memory_mb = memory_info.rss / 1024 / 1024
            memory_peak_mb = (
                getattr(memory_info, "peak_wss", memory_info.rss) / 1024 / 1024
            )

            cpu_percent = self.process.cpu_percent(interval=0.1)

            # Record memory usage
            self._record_metric(
                PipelineMetric(
                    name="pipeline_memory_usage_mb",
                    value=current_memory_mb,
                    metric_type=MetricType.GAUGE,
                    labels={
                        "operation_id": operation_id,
                        "phase": phase,
                        "metric_type": "current",
                    },
                    description="Current memory usage in MB",
                )
            )

            self._record_metric(
                PipelineMetric(
                    name="pipeline_memory_peak_mb",
                    value=memory_peak_mb,
                    metric_type=MetricType.GAUGE,
                    labels={
                        "operation_id": operation_id,
                        "phase": phase,
                        "metric_type": "peak",
                    },
                    description="Peak memory usage in MB",
                )
            )

            # Record CPU usage
            self._record_metric(
                PipelineMetric(
                    name="pipeline_cpu_usage_percent",
                    value=cpu_percent,
                    metric_type=MetricType.GAUGE,
                    labels={"operation_id": operation_id, "phase": phase},
                    description="CPU usage percentage",
                )
            )

            # Update operation metrics
            if operation_id in self.operation_metrics:
                metrics = self.operation_metrics[operation_id]
                if phase == "end" or memory_peak_mb > (metrics.memory_peak_mb or 0):
                    metrics.memory_peak_mb = memory_peak_mb
                if phase == "end":
                    metrics.cpu_usage_percent = cpu_percent

        except Exception as e:
            logger.debug(f"Failed to record system metrics: {e}")

    def _record_metric(self, metric: PipelineMetric):
        """Record a metric to the monitoring system."""
        try:
            # If we have an external monitoring system, use it
            if self.monitoring_system:
                # Convert to monitoring system format
                if hasattr(self.monitoring_system, "record_metric"):
                    self.monitoring_system.record_metric(
                        name=metric.name,
                        value=metric.value,
                        metric_type=metric.metric_type.value,
                        labels=metric.labels,
                        timestamp=metric.timestamp,
                        description=metric.description,
                    )
            else:
                # Log metrics for debugging
                logger.debug(
                    f"Metric: {metric.name}={metric.value} "
                    f"type={metric.metric_type.value} "
                    f"labels={metric.labels}"
                )

        except Exception as e:
            logger.debug(f"Failed to record metric {metric.name}: {e}")


# Convenience functions for common monitoring scenarios
def monitor_pipeline_operation(
    operation_name: str, operation_func: Callable, *args, **kwargs
) -> Any:
    """
    Convenience function to monitor a pipeline operation.

    Args:
        operation_name: Name of the operation
        operation_func: Function to execute and monitor
        *args: Positional arguments for operation_func
        **kwargs: Keyword arguments for operation_func

    Returns:
        Result of operation_func
    """
    monitor = PipelineMonitor()
    operation_id = monitor.start_operation(operation_name)

    try:
        result = operation_func(*args, **kwargs)
        monitor.end_operation(operation_id, success=True)
        return result
    except Exception as e:
        monitor.end_operation(operation_id, success=False, error_message=str(e))
        monitor.record_error(operation_id, "operation_exception", str(e))
        raise


def get_pipeline_monitor() -> PipelineMonitor:
    """Get a configured pipeline monitor instance."""
    return PipelineMonitor()

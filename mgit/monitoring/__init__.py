"""Monitoring and observability package for mgit.

This package provides comprehensive monitoring capabilities including:
- Structured logging with correlation IDs
- Prometheus-compatible metrics
- Health checks for Kubernetes
- Performance monitoring and instrumentation
"""

from .correlation import (
    CorrelationContext,
    correlation_context,
    get_correlation_id,
    git_operation_context,
    provider_context,
    set_correlation_id,
)
from .dashboard import create_alert_rules, create_grafana_dashboard
from .health import HealthChecker, get_health_checker
from .integration import (
    MonitoringContext,
    monitor_async_mgit_operation,
    monitor_authentication,
    monitor_git_operation,
    monitor_mgit_operation,
    monitor_provider_api_call,
    setup_monitoring_integration,
)
from .logger import StructuredLogger, get_structured_logger, setup_structured_logging
from .metrics import MetricsCollector, get_metrics_collector, setup_metrics
from .performance import PerformanceMonitor, get_performance_monitor

__all__ = [
    "CorrelationContext",
    "get_correlation_id",
    "set_correlation_id",
    "correlation_context",
    "provider_context",
    "git_operation_context",
    "StructuredLogger",
    "get_structured_logger",
    "setup_structured_logging",
    "MetricsCollector",
    "get_metrics_collector",
    "setup_metrics",
    "HealthChecker",
    "get_health_checker",
    "PerformanceMonitor",
    "get_performance_monitor",
    "create_grafana_dashboard",
    "create_alert_rules",
    "setup_monitoring_integration",
    "monitor_mgit_operation",
    "monitor_async_mgit_operation",
    "monitor_git_operation",
    "monitor_provider_api_call",
    "monitor_authentication",
    "MonitoringContext",
]

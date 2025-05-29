"""Monitoring and observability package for mgit.

This package provides comprehensive monitoring capabilities including:
- Structured logging with correlation IDs
- Prometheus-compatible metrics
- Health checks for Kubernetes
- Performance monitoring and instrumentation
"""

from .correlation import CorrelationContext, get_correlation_id, set_correlation_id, correlation_context, provider_context, git_operation_context
from .logger import StructuredLogger, get_structured_logger, setup_structured_logging
from .metrics import MetricsCollector, get_metrics_collector, setup_metrics
from .health import HealthChecker, get_health_checker
from .performance import PerformanceMonitor, get_performance_monitor
from .dashboard import create_grafana_dashboard, create_alert_rules
from .integration import (
    setup_monitoring_integration, 
    monitor_mgit_operation, 
    monitor_async_mgit_operation,
    monitor_git_operation,
    monitor_provider_api_call,
    monitor_authentication,
    MonitoringContext
)

__all__ = [
    'CorrelationContext',
    'get_correlation_id',
    'set_correlation_id',
    'correlation_context',
    'provider_context', 
    'git_operation_context',
    'StructuredLogger',
    'get_structured_logger',
    'setup_structured_logging',
    'MetricsCollector',
    'get_metrics_collector',
    'setup_metrics',
    'HealthChecker',
    'get_health_checker',
    'PerformanceMonitor',
    'get_performance_monitor',
    'create_grafana_dashboard',
    'create_alert_rules',
    'setup_monitoring_integration',
    'monitor_mgit_operation',
    'monitor_async_mgit_operation',
    'monitor_git_operation',
    'monitor_provider_api_call',
    'monitor_authentication',
    'MonitoringContext',
]
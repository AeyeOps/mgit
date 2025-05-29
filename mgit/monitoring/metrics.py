"""Prometheus-compatible metrics collection for mgit.

This module provides metrics collection and exposition in Prometheus format
for monitoring operation performance, success rates, and system health.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json


@dataclass
class MetricSample:
    """Represents a single metric sample."""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    help_text: str = ""
    metric_type: str = "gauge"  # gauge, counter, histogram, summary


class MetricsCollector:
    """Prometheus-compatible metrics collector."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.lock = threading.Lock()
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._counter_labels: Dict[str, Dict[str, str]] = {}
        self._gauge_labels: Dict[str, Dict[str, str]] = {}
        self._histogram_labels: Dict[str, Dict[str, str]] = {}
        self._metric_help: Dict[str, str] = {}
        self._metric_types: Dict[str, str] = {}
        
        # Operation tracking
        self._operation_start_times: Dict[str, float] = {}
        
        # Register default metrics
        self._register_default_metrics()
    
    def _register_default_metrics(self) -> None:
        """Register default mgit metrics."""
        # Operation counters
        self.register_metric("mgit_operations_total", "counter", 
                           "Total number of mgit operations")
        self.register_metric("mgit_operations_success_total", "counter",
                           "Total number of successful mgit operations")
        self.register_metric("mgit_operations_failure_total", "counter",
                           "Total number of failed mgit operations")
        
        # Git operations
        self.register_metric("mgit_git_operations_total", "counter",
                           "Total number of Git operations")
        self.register_metric("mgit_git_clone_duration_seconds", "histogram",
                           "Duration of Git clone operations")
        self.register_metric("mgit_git_pull_duration_seconds", "histogram",
                           "Duration of Git pull operations")
        
        # API metrics
        self.register_metric("mgit_api_requests_total", "counter",
                           "Total number of API requests")
        self.register_metric("mgit_api_request_duration_seconds", "histogram",
                           "Duration of API requests")
        self.register_metric("mgit_api_errors_total", "counter",
                           "Total number of API errors")
        
        # Authentication metrics
        self.register_metric("mgit_auth_attempts_total", "counter",
                           "Total number of authentication attempts")
        self.register_metric("mgit_auth_success_total", "counter",
                           "Total number of successful authentications")
        self.register_metric("mgit_auth_failures_total", "counter",
                           "Total number of failed authentications")
        
        # Provider metrics
        self.register_metric("mgit_provider_operations_total", "counter",
                           "Total operations by provider")
        self.register_metric("mgit_provider_rate_limit_hits_total", "counter",
                           "Total rate limit hits by provider")
        
        # System metrics
        self.register_metric("mgit_concurrent_operations", "gauge",
                           "Number of concurrent operations")
        self.register_metric("mgit_repositories_processed", "gauge",
                           "Total repositories processed")
        
        # Error metrics
        self.register_metric("mgit_errors_total", "counter",
                           "Total number of errors")
        self.register_metric("mgit_validation_errors_total", "counter",
                           "Total number of validation errors")
    
    def register_metric(self, name: str, metric_type: str, help_text: str) -> None:
        """Register a metric with its type and help text.
        
        Args:
            name: Metric name
            metric_type: Metric type (counter, gauge, histogram, summary)
            help_text: Help text describing the metric
        """
        with self.lock:
            self._metric_types[name] = metric_type
            self._metric_help[name] = help_text
    
    def inc_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric.
        
        Args:
            name: Counter name
            value: Increment value
            labels: Optional labels dictionary
        """
        with self.lock:
            key = self._make_key(name, labels)
            self._counters[key] += value
            if labels:
                self._counter_labels[key] = labels.copy()
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric value.
        
        Args:
            name: Gauge name
            value: Gauge value
            labels: Optional labels dictionary
        """
        with self.lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value
            if labels:
                self._gauge_labels[key] = labels.copy()
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a value in a histogram metric.
        
        Args:
            name: Histogram name
            value: Observed value
            labels: Optional labels dictionary
        """
        with self.lock:
            key = self._make_key(name, labels)
            self._histograms[key].append(value)
            if labels:
                self._histogram_labels[key] = labels.copy()
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Create a unique key for metric with labels.
        
        Args:
            name: Metric name
            labels: Optional labels dictionary
            
        Returns:
            Unique key string
        """
        if not labels:
            return name
        
        # Sort labels for consistent key generation
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def start_operation_timer(self, operation_id: str) -> None:
        """Start timing an operation.
        
        Args:
            operation_id: Unique operation identifier
        """
        with self.lock:
            self._operation_start_times[operation_id] = time.time()
    
    def end_operation_timer(self, operation_id: str, metric_name: str, 
                           labels: Optional[Dict[str, str]] = None) -> float:
        """End timing an operation and record the duration.
        
        Args:
            operation_id: Unique operation identifier
            metric_name: Name of the duration metric
            labels: Optional labels dictionary
            
        Returns:
            Operation duration in seconds
        """
        with self.lock:
            start_time = self._operation_start_times.pop(operation_id, None)
            if start_time is None:
                return 0.0
            
            duration = time.time() - start_time
            self.observe_histogram(metric_name, duration, labels)
            return duration
    
    def record_operation(self, operation: str, success: bool, duration: Optional[float] = None,
                        provider: Optional[str] = None, **extra_labels) -> None:
        """Record a completed operation with its metrics.
        
        Args:
            operation: Operation name
            success: Whether operation succeeded
            duration: Operation duration in seconds
            provider: Provider name if applicable
            **extra_labels: Additional labels
        """
        labels = {'operation': operation}
        if provider:
            labels['provider'] = provider
        labels.update(extra_labels)
        
        # Count total operations
        self.inc_counter("mgit_operations_total", labels=labels)
        
        # Count success/failure
        if success:
            self.inc_counter("mgit_operations_success_total", labels=labels)
        else:
            self.inc_counter("mgit_operations_failure_total", labels=labels)
        
        # Record duration if provided
        if duration is not None:
            duration_metric = f"mgit_{operation}_duration_seconds"
            self.observe_histogram(duration_metric, duration, labels)
    
    def record_git_operation(self, operation: str, repository: str, success: bool,
                           duration: Optional[float] = None) -> None:
        """Record a Git operation.
        
        Args:
            operation: Git operation (clone, pull, push, etc.)
            repository: Repository name or URL
            success: Whether operation succeeded
            duration: Operation duration in seconds
        """
        labels = {
            'operation': operation,
            'repository': repository
        }
        
        self.inc_counter("mgit_git_operations_total", labels=labels)
        
        if duration is not None:
            metric_name = f"mgit_git_{operation}_duration_seconds"
            self.observe_histogram(metric_name, duration, labels)
    
    def record_api_call(self, method: str, provider: str, status_code: int,
                       duration: float, endpoint: Optional[str] = None) -> None:
        """Record an API call.
        
        Args:
            method: HTTP method
            provider: Provider name
            status_code: HTTP status code
            duration: Request duration in seconds
            endpoint: API endpoint (optional)
        """
        labels = {
            'method': method,
            'provider': provider,
            'status_code': str(status_code)
        }
        if endpoint:
            labels['endpoint'] = endpoint
        
        self.inc_counter("mgit_api_requests_total", labels=labels)
        self.observe_histogram("mgit_api_request_duration_seconds", duration, labels)
        
        # Record errors
        if status_code >= 400:
            error_labels = {
                'provider': provider,
                'status_code': str(status_code)
            }
            self.inc_counter("mgit_api_errors_total", labels=error_labels)
    
    def record_authentication(self, provider: str, organization: str, success: bool) -> None:
        """Record an authentication attempt.
        
        Args:
            provider: Provider name
            organization: Organization name
            success: Whether authentication succeeded
        """
        labels = {
            'provider': provider,
            'organization': organization
        }
        
        self.inc_counter("mgit_auth_attempts_total", labels=labels)
        
        if success:
            self.inc_counter("mgit_auth_success_total", labels=labels)
        else:
            self.inc_counter("mgit_auth_failures_total", labels=labels)
    
    def record_provider_operation(self, provider: str, operation: str) -> None:
        """Record a provider operation.
        
        Args:
            provider: Provider name
            operation: Operation type
        """
        labels = {
            'provider': provider,
            'operation': operation
        }
        self.inc_counter("mgit_provider_operations_total", labels=labels)
    
    def record_rate_limit_hit(self, provider: str) -> None:
        """Record a rate limit hit.
        
        Args:
            provider: Provider name
        """
        labels = {'provider': provider}
        self.inc_counter("mgit_provider_rate_limit_hits_total", labels=labels)
    
    def record_error(self, error_type: str, operation: Optional[str] = None,
                    provider: Optional[str] = None) -> None:
        """Record an error.
        
        Args:
            error_type: Type of error
            operation: Operation where error occurred
            provider: Provider where error occurred
        """
        labels = {'error_type': error_type}
        if operation:
            labels['operation'] = operation
        if provider:
            labels['provider'] = provider
        
        self.inc_counter("mgit_errors_total", labels=labels)
    
    def update_concurrent_operations(self, count: int) -> None:
        """Update the count of concurrent operations.
        
        Args:
            count: Current number of concurrent operations
        """
        self.set_gauge("mgit_concurrent_operations", count)
    
    def update_repositories_processed(self, count: int) -> None:
        """Update the count of repositories processed.
        
        Args:
            count: Total number of repositories processed
        """
        self.set_gauge("mgit_repositories_processed", count)
    
    def get_metrics(self) -> List[MetricSample]:
        """Get all metrics as a list of samples.
        
        Returns:
            List of metric samples
        """
        samples = []
        
        with self.lock:
            # Counters
            for key, value in self._counters.items():
                name, labels = self._parse_key(key)
                samples.append(MetricSample(
                    name=name,
                    value=value,
                    labels=labels,
                    help_text=self._metric_help.get(name, ""),
                    metric_type="counter"
                ))
            
            # Gauges
            for key, value in self._gauges.items():
                name, labels = self._parse_key(key)
                samples.append(MetricSample(
                    name=name,
                    value=value,
                    labels=labels,
                    help_text=self._metric_help.get(name, ""),
                    metric_type="gauge"
                ))
            
            # Histograms (simplified - just count and sum)
            for key, values in self._histograms.items():
                name, labels = self._parse_key(key)
                if values:
                    # Create histogram buckets (simplified)
                    count_labels = labels.copy()
                    count_labels.update({"le": "+Inf"})
                    
                    samples.append(MetricSample(
                        name=f"{name}_bucket",
                        value=len(values),
                        labels=count_labels,
                        help_text=self._metric_help.get(name, ""),
                        metric_type="histogram"
                    ))
                    
                    samples.append(MetricSample(
                        name=f"{name}_count",
                        value=len(values),
                        labels=labels,
                        help_text=self._metric_help.get(name, ""),
                        metric_type="histogram"
                    ))
                    
                    samples.append(MetricSample(
                        name=f"{name}_sum",
                        value=sum(values),
                        labels=labels,
                        help_text=self._metric_help.get(name, ""),
                        metric_type="histogram"
                    ))
        
        return samples
    
    def _parse_key(self, key: str) -> Tuple[str, Dict[str, str]]:
        """Parse a metric key into name and labels.
        
        Args:
            key: Metric key
            
        Returns:
            Tuple of (name, labels)
        """
        if '{' not in key:
            return key, {}
        
        name, label_part = key.split('{', 1)
        label_part = label_part.rstrip('}')
        
        labels = {}
        if label_part:
            for pair in label_part.split(','):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    labels[k] = v
        
        return name, labels
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        samples = self.get_metrics()
        output = []
        
        # Group samples by metric name
        metrics_by_name = defaultdict(list)
        for sample in samples:
            base_name = sample.name.split('_bucket')[0].split('_count')[0].split('_sum')[0]
            metrics_by_name[base_name].append(sample)
        
        for metric_name, metric_samples in metrics_by_name.items():
            # Add help text
            if metric_samples and metric_samples[0].help_text:
                output.append(f"# HELP {metric_name} {metric_samples[0].help_text}")
            
            # Add type
            if metric_samples and metric_samples[0].metric_type:
                output.append(f"# TYPE {metric_name} {metric_samples[0].metric_type}")
            
            # Add samples
            for sample in metric_samples:
                label_str = ""
                if sample.labels:
                    label_pairs = [f'{k}="{v}"' for k, v in sorted(sample.labels.items())]
                    label_str = "{" + ",".join(label_pairs) + "}"
                
                output.append(f"{sample.name}{label_str} {sample.value}")
            
            output.append("")  # Empty line between metrics
        
        return "\n".join(output)
    
    def export_json(self) -> str:
        """Export metrics in JSON format.
        
        Returns:
            JSON-formatted metrics string
        """
        samples = self.get_metrics()
        metrics_data = []
        
        for sample in samples:
            metrics_data.append({
                'name': sample.name,
                'value': sample.value,
                'labels': sample.labels,
                'timestamp': sample.timestamp,
                'help': sample.help_text,
                'type': sample.metric_type
            })
        
        return json.dumps({
            'timestamp': time.time(),
            'metrics': metrics_data
        }, indent=2)
    
    def reset_metrics(self) -> None:
        """Reset all metrics to zero/empty."""
        with self.lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._counter_labels.clear()
            self._gauge_labels.clear()
            self._histogram_labels.clear()
            self._operation_start_times.clear()


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def setup_metrics() -> MetricsCollector:
    """Set up and return metrics collector.
    
    Returns:
        Configured MetricsCollector instance
    """
    global _metrics_collector
    _metrics_collector = MetricsCollector()
    return _metrics_collector


# Convenience functions for common metrics
def record_operation(operation: str, success: bool, duration: Optional[float] = None,
                    provider: Optional[str] = None, **extra_labels) -> None:
    """Record an operation using the global metrics collector."""
    collector = get_metrics_collector()
    collector.record_operation(operation, success, duration, provider, **extra_labels)


def record_git_operation(operation: str, repository: str, success: bool,
                        duration: Optional[float] = None) -> None:
    """Record a Git operation using the global metrics collector."""
    collector = get_metrics_collector()
    collector.record_git_operation(operation, repository, success, duration)


def record_api_call(method: str, provider: str, status_code: int,
                   duration: float, endpoint: Optional[str] = None) -> None:
    """Record an API call using the global metrics collector."""
    collector = get_metrics_collector()
    collector.record_api_call(method, provider, status_code, duration, endpoint)


def record_authentication(provider: str, organization: str, success: bool) -> None:
    """Record an authentication attempt using the global metrics collector."""
    collector = get_metrics_collector()
    collector.record_authentication(provider, organization, success)
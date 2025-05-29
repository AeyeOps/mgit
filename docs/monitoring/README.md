# mgit Monitoring and Observability

This document describes the comprehensive monitoring and observability features built into mgit for production deployment and operations.

## Overview

The mgit monitoring system provides:

- **Structured Logging** with correlation ID tracking
- **Prometheus-compatible Metrics** collection
- **Health Checks** for Kubernetes deployments  
- **Performance Monitoring** and instrumentation
- **Grafana Dashboards** and Prometheus alerts
- **HTTP Server** for metrics and health endpoints

## Quick Start

### 1. Enable Monitoring

Add monitoring to your mgit operations:

```python
from mgit.monitoring import setup_monitoring_integration

# Initialize monitoring (call once at startup)
setup_monitoring_integration()
```

### 2. Start Monitoring Server

```bash
# Start HTTP server for metrics and health checks
python -m mgit.monitoring.cli server --port 8080

# Or use simple server (no aiohttp dependency)
python -m mgit.monitoring.cli server --simple --port 8080
```

### 3. Generate Monitoring Configuration

```bash
# Generate Grafana dashboard and Prometheus config
python -m mgit.monitoring.cli generate-config --output ./monitoring

# Start monitoring stack
cd monitoring
docker-compose up -d
```

## Components

### Structured Logging

**JSON-formatted logs with correlation IDs:**

```python
from mgit.monitoring import get_structured_logger

logger = get_structured_logger("mgit.operations")

# Logs include correlation ID automatically
logger.info("Starting clone operation", repository="repo1", provider="github")
logger.operation_start("clone", repository="repo1")
logger.operation_end("clone", success=True, duration=2.5)
```

**Correlation Context:**

```python
from mgit.monitoring import correlation_context, provider_context

# Track operations across components
with correlation_context(operation="clone_all", organization="myorg"):
    with provider_context("github", "myorg"):
        # All logs in this context share correlation ID
        perform_github_operations()
```

### Metrics Collection

**Prometheus-compatible metrics:**

```python
from mgit.monitoring import get_metrics_collector

metrics = get_metrics_collector()

# Record operations
metrics.record_operation("clone", success=True, duration=2.5, provider="github")
metrics.record_git_operation("clone", "repo1", success=True, duration=2.5)
metrics.record_api_call("GET", "github", 200, 0.5, "/repos")
metrics.record_authentication("github", "myorg", success=True)

# Export metrics
prometheus_format = metrics.export_prometheus()
json_format = metrics.export_json()
```

**Available Metrics:**

- `mgit_operations_total` - Total operations by type
- `mgit_operations_success_total` - Successful operations
- `mgit_operations_failure_total` - Failed operations
- `mgit_git_operations_total` - Git operations by type
- `mgit_git_clone_duration_seconds` - Git clone durations
- `mgit_api_requests_total` - API requests by provider
- `mgit_api_request_duration_seconds` - API response times
- `mgit_auth_attempts_total` - Authentication attempts
- `mgit_health_overall` - Overall system health
- `mgit_concurrent_operations` - Current concurrent operations

### Health Checks

**Comprehensive health monitoring:**

```python
from mgit.monitoring import get_health_checker

health_checker = get_health_checker()

# Overall health status
health_status = await health_checker.get_overall_health()

# Kubernetes probes
is_ready = await health_checker.is_ready()    # Readiness probe
is_alive = await health_checker.is_alive()    # Liveness probe
```

**Health Check Categories:**

- **System Basics** - File system, Python environment
- **Git Availability** - Git command availability and version
- **Network Connectivity** - Provider endpoint reachability
- **Disk Space** - Available disk space monitoring
- **Memory Usage** - System memory utilization
- **Provider Endpoints** - API endpoint accessibility
- **Authentication Status** - Token/credential validation

### Performance Monitoring

**Operation timing and analysis:**

```python
from mgit.monitoring import get_performance_monitor

perf_monitor = get_performance_monitor()

# Manual timing
operation_id = perf_monitor.start_trace("clone_operation")
# ... perform operation ...
duration = perf_monitor.end_trace(operation_id, success=True)

# Context manager
with perf_monitor.trace_operation("clone_repos"):
    clone_repositories()

# Decorator
@monitor_performance("git_clone")
def clone_repo(url, path):
    # Automatically timed and tracked
    pass

# Performance analysis
metrics = perf_monitor.get_operation_metrics("clone_repos", hours=24)
print(f"Average duration: {metrics.avg_duration:.2f}s")
print(f"95th percentile: {metrics.p95_duration:.2f}s")
print(f"Success rate: {metrics.success_rate:.1f}%")
```

## Integration Decorators

### Operation Monitoring

```python
from mgit.monitoring.integration import monitor_mgit_operation

@monitor_mgit_operation(operation_name="clone_all", provider="github")
def clone_all_repositories(org, dest):
    # Automatically tracked with metrics, logging, and performance
    pass
```

### Git Operations

```python
from mgit.monitoring.integration import monitor_git_operation

@monitor_git_operation(operation_type="clone")
def git_clone(repo_url, destination):
    # Git-specific tracking
    pass
```

### Provider API Calls

```python
from mgit.monitoring.integration import monitor_provider_api_call

@monitor_provider_api_call(provider_name="github", endpoint="/repos")
def list_repositories(org):
    # API call tracking with timing and error rates
    pass
```

## HTTP Endpoints

When the monitoring server is running, these endpoints are available:

- `GET /metrics` - Prometheus metrics (text format)
- `GET /metrics/json` - Metrics in JSON format
- `GET /health` - Overall health status
- `GET /health/ready` - Readiness probe (Kubernetes)
- `GET /health/live` - Liveness probe (Kubernetes)  
- `GET /health/detailed` - Detailed health check results
- `GET /info` - Application information
- `GET /status` - Simple status check

## Kubernetes Integration

### Deployment Configuration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mgit
spec:
  template:
    spec:
      containers:
      - name: mgit
        image: mgit:latest
        ports:
        - containerPort: 8080
          name: monitoring
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
```

### Service and ServiceMonitor

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mgit-monitoring
  labels:
    app: mgit
spec:
  ports:
  - port: 8080
    name: monitoring
  selector:
    app: mgit
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: mgit
spec:
  selector:
    matchLabels:
      app: mgit
  endpoints:
  - port: monitoring
    path: /metrics
```

## Grafana Dashboard

The included Grafana dashboard provides:

- **Overview Panels** - Health status, operation rates, success rates
- **Operations Monitoring** - Operation types, duration trends
- **Performance Metrics** - Percentile analysis, duration histograms  
- **Provider Analytics** - API response times, rate limits, errors
- **Authentication Tracking** - Success rates, failure patterns
- **System Health** - Resource usage, health check status

Import the dashboard from `monitoring/grafana-dashboard.json`.

## Prometheus Alerts

Pre-configured alerts include:

- **MgitUnhealthy** - System health is down
- **MgitHealthDegraded** - Health percentage below 80%
- **MgitHighFailureRate** - Operation failure rate above 10%
- **MgitAPIErrors** - High API error rates
- **MgitRateLimitHit** - Rate limits being exceeded
- **MgitSlowOperations** - Operations taking too long
- **MgitAuthenticationFailures** - Authentication failures

## CLI Commands

```bash
# Start monitoring server
mgit monitoring server --host 0.0.0.0 --port 8080

# Check health status
mgit monitoring health --detailed --json

# Export metrics
mgit monitoring metrics --format prometheus --output metrics.txt

# Performance analysis
mgit monitoring performance --operation clone_repos --hours 24

# Generate monitoring configuration
mgit monitoring generate-config --output ./monitoring
```

## Configuration

### Environment Variables

- `MGIT_MONITORING_ENABLED` - Enable/disable monitoring (default: true)
- `MGIT_MONITORING_LOG_LEVEL` - Monitoring log level (default: INFO)
- `MGIT_MONITORING_HOST` - Server host (default: 0.0.0.0)
- `MGIT_MONITORING_PORT` - Server port (default: 8080)

### Structured Logging Configuration

```python
from mgit.monitoring import setup_structured_logging

setup_structured_logging(
    log_file="/var/log/mgit/app.log",
    log_level="INFO",
    console_level="INFO", 
    include_correlation=True,
    mask_credentials=True
)
```

## Best Practices

### 1. Correlation Context

Always use correlation context for operation tracking:

```python
with correlation_context(operation="bulk_clone", organization="myorg"):
    # All nested operations share correlation ID
    for repo in repositories:
        clone_repository(repo)
```

### 2. Error Handling

Combine monitoring with proper error handling:

```python
@monitor_mgit_operation("risky_operation")
def risky_operation():
    try:
        # Operation logic
        pass
    except SpecificError as e:
        # Log specific error context
        logger.error("Specific error occurred", error_details=str(e))
        raise
```

### 3. Performance Baselines

Set performance baselines for anomaly detection:

```python
perf_monitor = get_performance_monitor()
perf_monitor.set_performance_baseline("clone_operation", {
    "avg_duration": 5.0,
    "p95_duration": 15.0
})
```

### 4. Resource Monitoring

Update resource gauges regularly:

```python
metrics = get_metrics_collector()
metrics.update_concurrent_operations(current_operation_count)
metrics.update_repositories_processed(total_repos_processed)
```

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   ```bash
   # Install optional dependencies for full functionality
   pip install aiohttp prometheus_client psutil
   ```

2. **Health Check Failures**
   ```bash
   # Debug health issues
   mgit monitoring health --detailed
   ```

3. **Performance Issues**
   ```bash
   # Analyze slow operations
   mgit monitoring performance --hours 1
   ```

4. **Metrics Not Appearing**
   ```bash
   # Verify metrics endpoint
   curl http://localhost:8080/metrics
   ```

### Logs Analysis

Search structured logs by correlation ID:

```bash
# Search logs for specific operation
grep "correlation_id.*abc123" /var/log/mgit/app.log

# Search for errors in specific operation
jq 'select(.correlation.operation == "clone_all" and .level == "ERROR")' /var/log/mgit/app.log
```

## Development

### Adding Custom Metrics

```python
from mgit.monitoring import get_metrics_collector

metrics = get_metrics_collector()

# Register custom metric
metrics.register_metric("mgit_custom_operations_total", "counter", "Custom operations")

# Record custom metric
metrics.inc_counter("mgit_custom_operations_total", labels={"type": "custom"})
```

### Custom Health Checks

```python
from mgit.monitoring import get_health_checker

health_checker = get_health_checker()

async def custom_health_check():
    # Custom health check logic
    return HealthCheckResult(
        name="custom_check",
        status="healthy",
        message="Custom check passed"
    )

health_checker.register_check("custom", custom_health_check)
```

## Security Considerations

- **Credential Masking** - All logs automatically mask sensitive data
- **Network Security** - Monitor server should be on internal network
- **Access Control** - Implement authentication for production monitoring endpoints
- **Data Retention** - Configure appropriate retention policies for metrics and logs

## Performance Impact

The monitoring system is designed for minimal overhead:

- **Metrics Collection** - < 1ms per operation
- **Structured Logging** - < 0.5ms per log entry
- **Health Checks** - Cached results, configurable intervals
- **Performance Tracking** - In-memory storage with automatic cleanup

## References

- [Prometheus Metrics](https://prometheus.io/docs/concepts/metric_types/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [Kubernetes Monitoring](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Structured Logging](https://www.structlog.org/en/stable/)
# mgit Monitoring Integration Example

This document shows how the validated monitoring infrastructure would be integrated into actual mgit operations.

## 1. Main Application Integration

### mgit/__main__.py Integration

```python
#!/usr/bin/env python3

import asyncio
import typer
from pathlib import Path

# Initialize monitoring at startup
from mgit.monitoring import setup_monitoring_integration
from mgit.monitoring.server import start_simple_monitoring_server

def main():
    """Main mgit application entry point."""
    # Initialize monitoring first
    setup_monitoring_integration()
    
    # Start monitoring server if requested
    if get_config_value("MONITORING_ENABLED", "false").lower() == "true":
        monitoring_port = int(get_config_value("MONITORING_PORT", "8080"))
        server = start_simple_monitoring_server(port=monitoring_port)
        logger.info(f"Monitoring server started on port {monitoring_port}")
    
    # Continue with existing mgit logic
    app = typer.Typer()
    app.command()(clone_all)
    app.command()(pull_all)
    # ... other commands
    
    app()

if __name__ == "__main__":
    main()
```

## 2. Command Monitoring Integration

### Clone-All Command with Monitoring

```python
from mgit.monitoring import (
    monitor_mgit_operation, 
    get_structured_logger, 
    get_metrics_collector,
    correlation_context
)

@monitor_mgit_operation(
    operation_name="clone_all",
    provider="auto-detected",
    track_performance=True,
    log_result=True
)
def clone_all(
    project_name: str,
    destination_path: str,
    concurrency: int = 4,
    update_mode: str = "skip"
):
    """Clone all repositories with comprehensive monitoring."""
    
    logger = get_structured_logger("mgit.clone_all")
    metrics = get_metrics_collector()
    
    # Enhanced correlation context with operation details
    with correlation_context(
        operation="clone_all",
        project=project_name,
        concurrency=concurrency,
        update_mode=update_mode
    ):
        logger.info(
            f"Starting clone-all operation",
            project=project_name,
            destination=destination_path,
            concurrency=concurrency,
            update_mode=update_mode
        )
        
        try:
            # Detect provider and create manager
            provider_manager = ProviderManager.detect_provider(project_name)
            provider_name = provider_manager.provider_name
            
            # Get repositories with provider monitoring
            with correlation_context(operation="fetch_repositories", provider=provider_name):
                repositories = provider_manager.get_repositories(project_name)
                logger.info(f"Found {len(repositories)} repositories", count=len(repositories))
            
            # Update metrics
            metrics.set_gauge("repositories_discovered", len(repositories))
            metrics.record_provider_operation(provider_name, "list_repositories")
            
            # Clone repositories with concurrent monitoring
            cloned_count = 0
            failed_count = 0
            
            for repo in repositories:
                try:
                    # Each clone operation gets its own monitoring
                    clone_repository_with_monitoring(
                        repo, 
                        destination_path, 
                        provider_name
                    )
                    cloned_count += 1
                    
                    # Update progress metrics
                    metrics.set_gauge("repositories_cloned", cloned_count)
                    metrics.set_gauge("repositories_failed", failed_count)
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to clone {repo.name}", 
                               repository=repo.name, 
                               error=str(e))
                    
                    metrics.record_error(
                        error_type=type(e).__name__,
                        operation="clone_repository",
                        provider=provider_name
                    )
            
            # Final metrics and logging
            logger.info(
                f"Clone-all operation completed",
                total_repositories=len(repositories),
                cloned=cloned_count,
                failed=failed_count,
                success_rate=f"{(cloned_count/len(repositories)*100):.1f}%" if repositories else "N/A"
            )
            
            return {
                "total": len(repositories),
                "cloned": cloned_count,
                "failed": failed_count
            }
            
        except Exception as e:
            logger.error(f"Clone-all operation failed", error=str(e))
            metrics.record_error(
                error_type=type(e).__name__,
                operation="clone_all",
                provider=provider_name if 'provider_name' in locals() else "unknown"
            )
            raise


@monitor_git_operation(operation_type="clone", track_performance=True)
def clone_repository_with_monitoring(repository, destination_path, provider_name):
    """Clone a single repository with Git operation monitoring."""
    
    logger = get_structured_logger("mgit.git_operations")
    
    with correlation_context(
        git_operation="clone",
        repository=repository.name,
        provider=provider_name
    ):
        logger.info(f"Cloning repository", repository=repository.name, url=repository.clone_url)
        
        # Actual git clone logic here
        git_manager = GitManager()
        result = git_manager.clone(repository.clone_url, destination_path)
        
        logger.info(f"Repository cloned successfully", repository=repository.name)
        return result
```

## 3. Provider Integration with Monitoring

### GitHub Provider with API Monitoring

```python
from mgit.monitoring import monitor_provider_api_call, monitor_authentication

class GitHubProvider:
    
    @monitor_authentication(provider_name="github")
    def authenticate(self, token: str, organization: str):
        """Authenticate with GitHub with monitoring."""
        
        logger = get_structured_logger("mgit.providers.github")
        
        try:
            # Authentication logic
            self.client = Github(token)
            user = self.client.get_user()
            
            logger.authentication(
                provider="github",
                organization=organization,
                success=True
            )
            
            return True
            
        except Exception as e:
            logger.authentication(
                provider="github", 
                organization=organization,
                success=False
            )
            logger.error(f"GitHub authentication failed", error=str(e))
            raise
    
    @monitor_provider_api_call(provider_name="github", endpoint="/orgs/{org}/repos")
    def get_repositories(self, organization: str):
        """Get repositories with API call monitoring."""
        
        logger = get_structured_logger("mgit.providers.github")
        metrics = get_metrics_collector()
        
        try:
            # Time the API call
            start_time = time.time()
            
            org = self.client.get_organization(organization)
            repos = list(org.get_repos())
            
            duration = time.time() - start_time
            
            # Record detailed API metrics
            metrics.record_api_call(
                method="GET",
                provider="github",
                status_code=200,
                duration=duration,
                endpoint=f"/orgs/{organization}/repos"
            )
            
            logger.api_call(
                method="GET",
                url=f"https://api.github.com/orgs/{organization}/repos",
                status_code=200,
                response_time=duration
            )
            
            logger.info(f"Retrieved {len(repos)} repositories from GitHub", 
                       organization=organization, 
                       count=len(repos))
            
            return repos
            
        except Exception as e:
            # Record failed API call
            duration = time.time() - start_time if 'start_time' in locals() else 0
            
            metrics.record_api_call(
                method="GET",
                provider="github", 
                status_code=500,
                duration=duration,
                endpoint=f"/orgs/{organization}/repos"
            )
            
            logger.error(f"Failed to get repositories from GitHub", 
                        organization=organization,
                        error=str(e))
            raise
```

## 4. Health Checks Integration

### Custom mgit Health Checks

```python
from mgit.monitoring import get_health_checker

def setup_mgit_health_checks():
    """Set up mgit-specific health checks."""
    
    health_checker = get_health_checker()
    
    # Register custom health checks
    health_checker.register_check(
        "git_repositories_accessible",
        check_git_repositories_health,
        interval=300  # Check every 5 minutes
    )
    
    health_checker.register_check(
        "provider_tokens_valid",
        check_provider_tokens_health,
        interval=600  # Check every 10 minutes
    )

async def check_git_repositories_health():
    """Check if Git repositories are accessible."""
    
    try:
        # Test git command and basic operations
        result = subprocess.run(['git', 'version'], capture_output=True, timeout=5)
        
        if result.returncode == 0:
            return HealthCheckResult(
                name="git_repositories_accessible",
                status="healthy",
                message="Git command accessible and working",
                details={"git_version": result.stdout.decode().strip()}
            )
        else:
            return HealthCheckResult(
                name="git_repositories_accessible",
                status="unhealthy", 
                message="Git command failed",
                details={"error": result.stderr.decode()}
            )
            
    except Exception as e:
        return HealthCheckResult(
            name="git_repositories_accessible",
            status="unhealthy",
            message=f"Git health check failed: {str(e)}",
            details={"error": str(e)}
        )

async def check_provider_tokens_health():
    """Check if provider authentication tokens are valid."""
    
    results = {}
    overall_status = "healthy"
    
    # Check each configured provider
    for provider_name in ["github", "azure-devops", "bitbucket"]:
        token = get_config_value(f"{provider_name.replace('-', '_')}_token")
        
        if token:
            try:
                # Test token validity (simplified)
                provider = ProviderFactory.create_provider(provider_name)
                provider.authenticate(token, "test-org")
                results[provider_name] = "valid"
                
            except Exception as e:
                results[provider_name] = f"invalid: {str(e)}"
                overall_status = "degraded"
        else:
            results[provider_name] = "not_configured"
    
    valid_tokens = sum(1 for status in results.values() if status == "valid")
    
    return HealthCheckResult(
        name="provider_tokens_valid",
        status=overall_status,
        message=f"Provider tokens: {valid_tokens} valid, {len(results)} total",
        details=results
    )
```

## 5. Configuration Integration

### Environment Variables and Config

```bash
# .env configuration for monitoring
MONITORING_ENABLED=true
MONITORING_PORT=8080
MONITORING_LOG_LEVEL=INFO
MONITORING_HEALTH_CHECK_INTERVAL=60

# Structured logging configuration
LOG_FORMAT=json
LOG_CORRELATION_ENABLED=true
LOG_CREDENTIAL_MASKING=true

# Metrics configuration
METRICS_ENABLED=true
METRICS_PROMETHEUS_ENABLED=true
METRICS_RETENTION_HOURS=24
```

### mgit Configuration File

```yaml
# ~/.config/mgit/config
monitoring:
  enabled: true
  port: 8080
  health_checks:
    enabled: true
    interval: 60
  metrics:
    enabled: true
    prometheus: true
  logging:
    structured: true
    correlation: true
    level: INFO
    credential_masking: true

providers:
  github:
    token: ${GITHUB_TOKEN}
    monitoring:
      api_timeout: 30
      retry_attempts: 3
  
  azure-devops:
    token: ${AZURE_DEVOPS_TOKEN}
    monitoring:
      api_timeout: 45
      retry_attempts: 3
```

## 6. Production Deployment

### Kubernetes Deployment with Monitoring

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
        env:
        - name: MONITORING_ENABLED
          value: "true"
        - name: MONITORING_PORT
          value: "8080"
        
        # Health check configuration
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: mgit-monitoring
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"
spec:
  ports:
  - port: 8080
    name: monitoring
  selector:
    app: mgit
```

### Prometheus Configuration

```yaml
# prometheus.yml
scrape_configs:
- job_name: 'mgit'
  static_configs:
  - targets: ['mgit-monitoring:8080']
  scrape_interval: 30s
  metrics_path: /metrics
```

## 7. Operational Usage

### Viewing Metrics
```bash
# View live metrics
curl http://localhost:8080/metrics

# View health status
curl http://localhost:8080/health | jq

# View application info
curl http://localhost:8080/info | jq
```

### Log Analysis
```bash
# Filter logs by correlation ID
tail -f mgit.log | jq 'select(.correlation.correlation_id == "abc123")'

# Filter logs by operation
tail -f mgit.log | jq 'select(.correlation.operation == "clone_all")'

# Filter errors only
tail -f mgit.log | jq 'select(.level == "ERROR")'
```

## Summary

This integration example demonstrates how the validated monitoring infrastructure seamlessly integrates with mgit operations to provide:

- **Comprehensive Operation Tracking**: Every mgit operation is automatically monitored
- **Provider-Specific Monitoring**: API calls and authentication tracked per provider
- **Performance Insights**: Detailed timing and performance metrics
- **Health Monitoring**: Continuous health checks for all components
- **Production Readiness**: Kubernetes-compatible health probes and metrics endpoints
- **Operational Visibility**: Structured logs with correlation tracking

The monitoring system adds minimal overhead while providing maximum observability for production mgit deployments.
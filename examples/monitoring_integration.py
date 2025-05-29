#!/usr/bin/env python3
"""Example of integrating monitoring into mgit operations.

This script demonstrates how to add comprehensive monitoring to mgit
operations using the monitoring framework.
"""

import asyncio
import time
from pathlib import Path

# Import mgit monitoring components
from mgit.monitoring import (
    setup_monitoring_integration,
    get_structured_logger,
    get_metrics_collector,
    get_performance_monitor,
    get_health_checker,
    correlation_context,
    provider_context,
    git_operation_context
)
from mgit.monitoring.integration import (
    monitor_mgit_operation,
    monitor_git_operation,
    monitor_provider_api_call,
    MonitoringContext
)


# Example: Monitored Git operations
@monitor_git_operation(operation_type="clone")
def clone_repository(repo_url: str, destination: str) -> bool:
    """Example Git clone operation with monitoring."""
    logger = get_structured_logger("example.git")
    
    logger.info(f"Cloning repository {repo_url} to {destination}")
    
    # Simulate Git clone operation
    time.sleep(2)  # Simulate work
    
    # Simulate occasional failures
    import random
    if random.random() < 0.1:  # 10% failure rate
        raise Exception("Git clone failed: network timeout")
    
    logger.info("Repository cloned successfully")
    return True


@monitor_git_operation(operation_type="pull")
def pull_repository(repo_path: str) -> bool:
    """Example Git pull operation with monitoring."""
    logger = get_structured_logger("example.git")
    
    logger.info(f"Pulling updates for repository at {repo_path}")
    
    # Simulate Git pull operation
    time.sleep(1)  # Simulate work
    
    logger.info("Repository updated successfully")
    return True


# Example: Monitored provider API operations
@monitor_provider_api_call(provider_name="github", endpoint="/repos")
def list_github_repositories(organization: str) -> list:
    """Example GitHub API call with monitoring."""
    logger = get_structured_logger("example.providers.github")
    
    logger.info(f"Fetching repositories for organization: {organization}")
    
    # Simulate API call
    time.sleep(0.5)  # Simulate network delay
    
    # Simulate rate limiting occasionally
    import random
    if random.random() < 0.05:  # 5% rate limit hit
        from mgit.monitoring.metrics import get_metrics_collector
        metrics = get_metrics_collector()
        metrics.record_rate_limit_hit("github")
        raise Exception("Rate limit exceeded")
    
    # Return mock data
    return [
        {"name": "repo1", "clone_url": "https://github.com/org/repo1.git"},
        {"name": "repo2", "clone_url": "https://github.com/org/repo2.git"},
    ]


@monitor_mgit_operation(operation_name="clone_all", provider="github")
def clone_all_repositories(organization: str, destination_dir: str) -> dict:
    """Example high-level operation with monitoring."""
    logger = get_structured_logger("example.operations")
    metrics = get_metrics_collector()
    
    # Use correlation context for the entire operation
    with correlation_context(
        operation="clone_all",
        organization=organization,
        destination=destination_dir
    ):
        logger.info(f"Starting clone-all operation for {organization}")
        
        # Track concurrent operations
        metrics.set_gauge("mgit_concurrent_operations", 1)
        
        try:
            # Get repositories from provider
            with provider_context("github", organization):
                repositories = list_github_repositories(organization)
            
            results = {
                "success": [],
                "failed": [],
                "total": len(repositories)
            }
            
            # Clone each repository
            for repo in repositories:
                repo_name = repo["name"]
                repo_url = repo["clone_url"]
                repo_path = f"{destination_dir}/{repo_name}"
                
                try:
                    with git_operation_context("clone", repository=repo_url):
                        clone_repository(repo_url, repo_path)
                    results["success"].append(repo_name)
                    
                except Exception as e:
                    logger.error(f"Failed to clone {repo_name}: {str(e)}")
                    results["failed"].append({"name": repo_name, "error": str(e)})
            
            # Update metrics
            success_count = len(results["success"])
            total_count = results["total"]
            metrics.set_gauge("mgit_repositories_processed", total_count)
            
            logger.info(f"Clone-all operation completed: {success_count}/{total_count} successful")
            
            return results
            
        finally:
            # Clean up concurrent operations counter
            metrics.set_gauge("mgit_concurrent_operations", 0)


# Example: Using monitoring context manager
def sync_repositories(repo_paths: list) -> dict:
    """Example operation using monitoring context manager."""
    with MonitoringContext("sync_repositories", repository_count=len(repo_paths)) as ctx:
        logger = get_structured_logger("example.sync")
        
        results = {"synced": [], "failed": []}
        
        for repo_path in repo_paths:
            try:
                # Add metadata to the operation
                ctx.metadata["current_repo"] = repo_path
                
                pull_repository(repo_path)
                results["synced"].append(repo_path)
                
            except Exception as e:
                logger.error(f"Failed to sync {repo_path}: {str(e)}")
                results["failed"].append({"path": repo_path, "error": str(e)})
        
        return results


# Example: Health check integration
async def run_health_checks():
    """Example of running health checks."""
    logger = get_structured_logger("example.health")
    health_checker = get_health_checker()
    
    logger.info("Running health checks...")
    
    # Run overall health check
    health_status = await health_checker.get_overall_health()
    
    print(f"Overall Health: {health_status['status']}")
    print(f"Health Percentage: {health_status['summary']['health_percentage']:.1f}%")
    
    if health_status['issues']:
        print("Issues found:")
        for issue in health_status['issues']:
            print(f"  - {issue}")
    
    # Run specific checks
    is_ready = await health_checker.is_ready()
    is_alive = await health_checker.is_alive()
    
    print(f"Ready: {is_ready}")
    print(f"Alive: {is_alive}")


# Example: Performance monitoring
def analyze_performance():
    """Example of analyzing performance metrics."""
    logger = get_structured_logger("example.performance")
    performance_monitor = get_performance_monitor()
    
    logger.info("Analyzing performance metrics...")
    
    # Get performance summary
    summary = performance_monitor.get_all_operations_summary(hours=1)
    
    if summary:
        print("Performance Summary (last hour):")
        for operation, metrics in summary.items():
            print(f"  {operation}:")
            print(f"    Count: {metrics.count}")
            print(f"    Avg Duration: {metrics.avg_duration:.2f}s")
            print(f"    Success Rate: {metrics.success_rate:.1f}%")
    else:
        print("No performance data available")


# Example: Metrics export
def export_metrics():
    """Example of exporting metrics."""
    logger = get_structured_logger("example.metrics")
    metrics = get_metrics_collector()
    
    logger.info("Exporting metrics...")
    
    # Export in Prometheus format
    prometheus_metrics = metrics.export_prometheus()
    print("Prometheus Metrics Sample:")
    print(prometheus_metrics[:500] + "..." if len(prometheus_metrics) > 500 else prometheus_metrics)
    
    # Export in JSON format
    json_metrics = metrics.export_json()
    print("\nJSON Metrics available")


async def main():
    """Main example function."""
    print("=== mgit Monitoring Integration Example ===\n")
    
    # Setup monitoring integration
    print("1. Setting up monitoring integration...")
    setup_monitoring_integration()
    
    # Simulate some operations
    print("\n2. Running monitored operations...")
    
    # Clone repositories example
    try:
        results = clone_all_repositories("example-org", "/tmp/repos")
        print(f"Clone operation results: {results['total']} total, "
              f"{len(results['success'])} successful, {len(results['failed'])} failed")
    except Exception as e:
        print(f"Clone operation failed: {e}")
    
    # Sync repositories example
    repo_paths = ["/tmp/repo1", "/tmp/repo2", "/tmp/repo3"]
    sync_results = sync_repositories(repo_paths)
    print(f"Sync operation results: {len(sync_results['synced'])} synced, "
          f"{len(sync_results['failed'])} failed")
    
    # Health checks
    print("\n3. Running health checks...")
    await run_health_checks()
    
    # Performance analysis
    print("\n4. Analyzing performance...")
    analyze_performance()
    
    # Metrics export
    print("\n5. Exporting metrics...")
    export_metrics()
    
    print("\n=== Example completed ===")
    print("\nTo start monitoring server:")
    print("  python -m mgit.monitoring.cli server")
    print("\nTo view health status:")
    print("  python -m mgit.monitoring.cli health --detailed")
    print("\nTo export metrics:")
    print("  python -m mgit.monitoring.cli metrics --format json")


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Monitoring Integration Demo for mgit

This script demonstrates how monitoring is integrated with actual mgit operations.
"""

import asyncio
import sys
import time
from pathlib import Path

# Import mgit monitoring and core components
sys.path.insert(0, str(Path(__file__).parent / "mgit"))

try:
    from mgit.monitoring import (
        setup_monitoring_integration,
        get_metrics_collector,
        get_structured_logger,
        get_health_checker,
        correlation_context,
        monitor_mgit_operation,
        monitor_git_operation
    )
    from mgit.monitoring.server import start_simple_monitoring_server
    print("✅ All monitoring components imported successfully")
    MONITORING_AVAILABLE = True
except ImportError as e:
    print(f"❌ Failed to import monitoring components: {e}")
    MONITORING_AVAILABLE = False


@monitor_mgit_operation(operation_name="clone_all", provider="demo_provider")
def simulate_clone_all_operation(project_name: str, num_repos: int = 5):
    """Simulate a clone-all operation with monitoring."""
    logger = get_structured_logger("demo.clone_all")
    metrics = get_metrics_collector()
    
    logger.info(f"Starting clone-all operation for project: {project_name}")
    
    for i in range(num_repos):
        repo_name = f"{project_name}/repo-{i+1}"
        
        # Simulate git clone operation
        with simulate_git_clone(repo_name):
            # Simulate work
            time.sleep(0.1)
        
        # Update progress metrics
        metrics.set_gauge("repositories_processed", i + 1)
    
    logger.info(f"Completed clone-all operation for {num_repos} repositories")
    return {"cloned": num_repos, "project": project_name}


@monitor_git_operation(operation_type="clone")
def simulate_git_clone(repository: str):
    """Simulate a git clone operation with monitoring."""
    class GitCloneContext:
        def __init__(self, repo):
            self.repo = repo
            self.logger = get_structured_logger("demo.git")
        
        def __enter__(self):
            self.logger.info(f"Cloning repository: {self.repo}")
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                self.logger.info(f"Successfully cloned: {self.repo}")
            else:
                self.logger.error(f"Failed to clone: {self.repo}", error=str(exc_val))
    
    return GitCloneContext(repository)


async def demonstrate_monitoring_integration():
    """Demonstrate monitoring integration with mgit operations."""
    if not MONITORING_AVAILABLE:
        print("❌ Monitoring not available")
        return False
    
    print("\n🎭 Monitoring Integration Demonstration")
    print("=" * 60)
    
    # Initialize monitoring
    setup_monitoring_integration()
    metrics = get_metrics_collector()
    logger = get_structured_logger("demo")
    health_checker = get_health_checker()
    
    print("✅ Monitoring initialized")
    
    # Start monitoring server
    print("\n🚀 Starting monitoring server on http://localhost:18080")
    server = start_simple_monitoring_server(host="127.0.0.1", port=18080)
    
    print("   📊 Metrics endpoint: http://localhost:18080/metrics")
    print("   🏥 Health endpoint: http://localhost:18080/health")
    print("   💡 Info endpoint: http://localhost:18080/info")
    
    try:
        # Demonstrate operations with monitoring
        print("\n🔄 Simulating mgit operations with monitoring...")
        
        # Simulate multiple projects
        projects = ["project-alpha", "project-beta", "project-gamma"]
        
        for project in projects:
            print(f"\n   📁 Processing project: {project}")
            
            # Use correlation context for project-level operations
            with correlation_context(operation="project_processing", project=project):
                logger.info(f"Starting project processing", project=project)
                
                # Simulate clone-all operation (decorated with monitoring)
                result = simulate_clone_all_operation(project, num_repos=3)
                
                logger.info(f"Project processing complete", 
                          project=project, 
                          repos_cloned=result["cloned"])
        
        # Record some additional metrics
        print("\n   📈 Recording additional metrics...")
        metrics.record_authentication("github", "example-org", success=True)
        metrics.record_authentication("azure-devops", "example-org", success=True)
        metrics.record_api_call("GET", "github", 200, 0.5, "/user/repos")
        metrics.record_api_call("GET", "azure-devops", 200, 0.8, "/projects")
        
        # Simulate some errors
        metrics.record_error("ConnectionTimeout", operation="clone", provider="github")
        metrics.record_operation("failed_clone", success=False, duration=5.0, provider="bitbucket")
        
        print("✅ Simulated operations complete")
        
        # Show current metrics
        print("\n📊 Current Metrics Summary:")
        prometheus_output = metrics.export_prometheus()
        
        # Count metrics
        metric_lines = [line for line in prometheus_output.split('\n') if line and not line.startswith('#')]
        total_operations = len([line for line in metric_lines if 'mgit_operations_total' in line])
        total_git_ops = len([line for line in metric_lines if 'mgit_git_operations_total' in line])
        total_api_calls = len([line for line in metric_lines if 'mgit_api_requests_total' in line])
        
        print(f"   • Total metric lines: {len(metric_lines)}")
        print(f"   • Operation metrics: {total_operations}")
        print(f"   • Git operation metrics: {total_git_ops}")
        print(f"   • API call metrics: {total_api_calls}")
        
        # Show health status
        print("\n🏥 Health Status:")
        overall_health = await health_checker.get_overall_health()
        print(f"   • Overall status: {overall_health['status']}")
        print(f"   • Health percentage: {overall_health['summary']['health_percentage']:.1f}%")
        print(f"   • Healthy checks: {overall_health['summary']['healthy_checks']}/{overall_health['summary']['total_checks']}")
        
        # Show structured logs sample
        print("\n📝 Structured Logging Sample:")
        with correlation_context(operation="demo_logging", provider="demo"):
            logger.info("This is a sample structured log entry", 
                       sample_field="sample_value",
                       numeric_field=42,
                       boolean_field=True)
            logger.operation_start("sample_operation")
            logger.operation_end("sample_operation", success=True, duration=1.5)
        
        print("\n🌐 Monitoring Server Running:")
        print("   Visit the endpoints above to see live monitoring data")
        print("   • Prometheus metrics format at /metrics")
        print("   • JSON health data at /health")
        print("   • Application info at /info")
        
        # Keep server running for a moment
        print("\n⏳ Server will run for 10 seconds for testing...")
        await asyncio.sleep(10)
        
        print("\n🎯 MONITORING INTEGRATION DEMO COMPLETE")
        print("=" * 60)
        print("✅ Successfully demonstrated:")
        print("  • Operation monitoring with decorators")
        print("  • Structured logging with correlation IDs")
        print("  • Metrics collection and export")
        print("  • Health check system")
        print("  • HTTP endpoints for monitoring")
        print("  • Integration with mgit-style operations")
        
        return True
        
    finally:
        # Stop the server
        print("\n🛑 Stopping monitoring server...")
        server.stop()


async def main():
    """Main function."""
    success = await demonstrate_monitoring_integration()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
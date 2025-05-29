"""Monitoring commands for mgit CLI.

This module provides monitoring and observability commands that can be
integrated into the main mgit CLI.
"""

import asyncio
import sys
from typing import Optional
from pathlib import Path

try:
    import typer
    TYPER_AVAILABLE = True
except ImportError:
    TYPER_AVAILABLE = False

from ..monitoring.server import start_monitoring_server, start_simple_monitoring_server
from ..monitoring.health import get_health_checker
from ..monitoring.metrics import get_metrics_collector
from ..monitoring.performance import get_performance_monitor
from ..monitoring.dashboard import create_monitoring_configuration
from ..monitoring.integration import setup_monitoring_integration
from ..monitoring.logger import setup_structured_logging, get_structured_logger


def start_monitoring_server_command(
    host: str = "0.0.0.0",
    port: int = 8080,
    simple: bool = False,
    log_level: str = "INFO"
) -> None:
    """Start the monitoring server for mgit.
    
    Args:
        host: Server host address
        port: Server port number  
        simple: Use simple server (no aiohttp dependency)
        log_level: Logging level
    """
    # Setup monitoring integration
    setup_monitoring_integration()
    
    # Setup structured logging
    setup_structured_logging(log_level=log_level)
    logger = get_structured_logger("mgit.monitoring.server")
    
    logger.info(f"Starting mgit monitoring server on {host}:{port}",
                host=host, port=port, simple=simple)
    
    if simple:
        # Use simple server (no async dependencies)
        server = start_simple_monitoring_server(host, port)
        
        try:
            logger.info("Monitoring server is running. Press Ctrl+C to stop.")
            import signal
            signal.pause()
        except KeyboardInterrupt:
            logger.info("Shutting down monitoring server")
            server.stop()
    else:
        # Use async server (requires aiohttp)
        async def run_server():
            try:
                server = await start_monitoring_server(host, port)
                
                logger.info("Monitoring server is running. Press Ctrl+C to stop.")
                
                # Keep server running
                while True:
                    await asyncio.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info("Shutting down monitoring server")
                if 'server' in locals():
                    await server.stop()
        
        try:
            asyncio.run(run_server())
        except KeyboardInterrupt:
            logger.info("Server shutdown complete")


def health_check_command(
    detailed: bool = False,
    json_output: bool = False,
    exit_code: bool = True
) -> None:
    """Run health checks and display results.
    
    Args:
        detailed: Show detailed health check results
        json_output: Output results in JSON format
        exit_code: Exit with appropriate status code
    """
    async def run_health_check():
        # Setup monitoring if not already done
        setup_monitoring_integration()
        
        health_checker = get_health_checker()
        
        if detailed:
            health_data = await health_checker.get_overall_health(use_cache=False)
        else:
            # Run basic health checks
            is_ready = await health_checker.is_ready()
            is_alive = await health_checker.is_alive()
            
            health_data = {
                "ready": is_ready,
                "alive": is_alive,
                "status": "healthy" if (is_ready and is_alive) else "unhealthy"
            }
        
        if json_output:
            import json
            print(json.dumps(health_data, indent=2))
        else:
            if detailed:
                print(f"Overall Status: {health_data['status']}")
                print(f"Health Percentage: {health_data['summary']['health_percentage']:.1f}%")
                print(f"Total Checks: {health_data['summary']['total_checks']}")
                print(f"Healthy Checks: {health_data['summary']['healthy_checks']}")
                
                if health_data['issues']:
                    print(f"\nIssues:")
                    for issue in health_data['issues']:
                        print(f"  - {issue}")
                
                print(f"\nCheck Details:")
                for check_name, check_result in health_data['checks'].items():
                    status_icon = "✓" if check_result['status'] == "healthy" else "✗"
                    print(f"  {status_icon} {check_name}: {check_result['message']}")
            else:
                status_icon = "✓" if health_data['status'] == "healthy" else "✗"
                print(f"{status_icon} Health: {health_data['status']}")
                print(f"  Ready: {health_data['ready']}")
                print(f"  Alive: {health_data['alive']}")
        
        # Exit with appropriate code if requested
        if exit_code:
            exit_code_value = 0 if health_data['status'] == "healthy" else 1
            sys.exit(exit_code_value)
    
    asyncio.run(run_health_check())


def metrics_export_command(
    format_type: str = "prometheus",
    output_file: Optional[str] = None
) -> None:
    """Export metrics in specified format.
    
    Args:
        format_type: Output format (prometheus, json)
        output_file: Optional output file path
    """
    # Setup monitoring if not already done
    setup_monitoring_integration()
    
    metrics = get_metrics_collector()
    
    if format_type.lower() == "json":
        output = metrics.export_json()
    else:
        output = metrics.export_prometheus()
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(output)
        print(f"Metrics exported to {output_file}")
    else:
        print(output)


def performance_report_command(
    operation: Optional[str] = None,
    hours: int = 24,
    json_output: bool = False
) -> None:
    """Show performance metrics and statistics.
    
    Args:
        operation: Specific operation to show metrics for
        hours: Hours to look back
        json_output: Output in JSON format
    """
    # Setup monitoring if not already done
    setup_monitoring_integration()
    
    performance_monitor = get_performance_monitor()
    
    if operation:
        metrics = performance_monitor.get_operation_metrics(operation, hours)
        if not metrics:
            print(f"No performance data found for operation: {operation}")
            sys.exit(1)
        
        if json_output:
            import json
            print(json.dumps({
                "operation": operation,
                "metrics": {
                    "count": metrics.count,
                    "total_duration": metrics.total_duration,
                    "min_duration": metrics.min_duration,
                    "max_duration": metrics.max_duration,
                    "avg_duration": metrics.avg_duration,
                    "median_duration": metrics.median_duration,
                    "p95_duration": metrics.p95_duration,
                    "p99_duration": metrics.p99_duration,
                    "error_count": metrics.error_count,
                    "success_rate": metrics.success_rate
                }
            }, indent=2))
        else:
            print(f"Performance Metrics for '{operation}' (last {hours} hours):")
            print(f"  Count: {metrics.count}")
            print(f"  Success Rate: {metrics.success_rate:.1f}%")
            print(f"  Average Duration: {metrics.avg_duration:.2f}s")
            print(f"  Median Duration: {metrics.median_duration:.2f}s")
            print(f"  95th Percentile: {metrics.p95_duration:.2f}s")
            print(f"  99th Percentile: {metrics.p99_duration:.2f}s")
            print(f"  Min Duration: {metrics.min_duration:.2f}s")
            print(f"  Max Duration: {metrics.max_duration:.2f}s")
            print(f"  Error Count: {metrics.error_count}")
    else:
        summary = performance_monitor.get_all_operations_summary(hours)
        
        if json_output:
            import json
            output_data = {}
            for op_name, metrics in summary.items():
                output_data[op_name] = {
                    "count": metrics.count,
                    "avg_duration": metrics.avg_duration,
                    "p95_duration": metrics.p95_duration,
                    "success_rate": metrics.success_rate,
                    "error_count": metrics.error_count
                }
            print(json.dumps(output_data, indent=2))
        else:
            if not summary:
                print(f"No performance data found for the last {hours} hours")
                return
            
            print(f"Performance Summary (last {hours} hours):")
            print()
            
            # Sort by count descending
            sorted_ops = sorted(summary.items(), key=lambda x: x[1].count, reverse=True)
            
            for op_name, metrics in sorted_ops:
                print(f"  {op_name}:")
                print(f"    Count: {metrics.count}")
                print(f"    Success Rate: {metrics.success_rate:.1f}%")
                print(f"    Avg Duration: {metrics.avg_duration:.2f}s")
                print(f"    P95 Duration: {metrics.p95_duration:.2f}s")
                if metrics.error_count > 0:
                    print(f"    Error Count: {metrics.error_count}")
                print()


def generate_monitoring_config_command(
    output_dir: str = "./monitoring",
    datasource: str = "Prometheus",
    namespace: str = "mgit"
) -> None:
    """Generate monitoring configuration files.
    
    Args:
        output_dir: Output directory for configuration files
        datasource: Grafana datasource name  
        namespace: Namespace for alert rules
    """
    output_path = Path(output_dir)
    
    try:
        create_monitoring_configuration(
            output_dir=output_path,
            datasource_name=datasource,
            namespace=namespace
        )
        
        print(f"Monitoring configuration generated in: {output_path}")
        print("\nGenerated files:")
        print("  - grafana-dashboard.json")
        print("  - prometheus-alerts.yml")
        print("  - docker-compose.yml")
        print("  - prometheus.yml")
        print("  - README.md")
        print(f"\nTo start monitoring stack: cd {output_path} && docker-compose up -d")
        
    except Exception as e:
        print(f"Error generating configuration: {str(e)}")
        sys.exit(1)


# Typer integration if available
if TYPER_AVAILABLE:
    # Create monitoring sub-app
    monitoring_app = typer.Typer(
        name="monitoring",
        help="Monitoring and observability commands for mgit"
    )
    
    @monitoring_app.command("server")
    def server_cmd(
        host: str = typer.Option("0.0.0.0", "--host", "-h", help="Server host"),
        port: int = typer.Option(8080, "--port", "-p", help="Server port"),
        simple: bool = typer.Option(False, "--simple", help="Use simple server (no aiohttp)"),
        log_level: str = typer.Option("INFO", "--log-level", help="Log level")
    ):
        """Start the monitoring server."""
        start_monitoring_server_command(host, port, simple, log_level)
    
    @monitoring_app.command("health")
    def health_cmd(
        detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed results"),
        json_output: bool = typer.Option(False, "--json", help="Output JSON"),
        no_exit: bool = typer.Option(False, "--no-exit", help="Don't exit with status code")
    ):
        """Run health checks."""
        health_check_command(detailed, json_output, not no_exit)
    
    @monitoring_app.command("metrics")
    def metrics_cmd(
        format_type: str = typer.Option("prometheus", "--format", "-f", help="Output format (prometheus, json)"),
        output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file")
    ):
        """Export metrics."""
        metrics_export_command(format_type, output)
    
    @monitoring_app.command("performance")
    def performance_cmd(
        operation: Optional[str] = typer.Option(None, "--operation", "-op", help="Specific operation"),
        hours: int = typer.Option(24, "--hours", help="Hours to look back"),
        json_output: bool = typer.Option(False, "--json", help="Output JSON")
    ):
        """Show performance metrics."""
        performance_report_command(operation, hours, json_output)
    
    @monitoring_app.command("generate-config")
    def generate_config_cmd(
        output_dir: str = typer.Option("./monitoring", "--output", "-o", help="Output directory"),
        datasource: str = typer.Option("Prometheus", "--datasource", help="Grafana datasource"),
        namespace: str = typer.Option("mgit", "--namespace", help="Alert rules namespace")
    ):
        """Generate monitoring configuration files."""
        generate_monitoring_config_command(output_dir, datasource, namespace)
else:
    monitoring_app = None


def register_monitoring_commands(main_app):
    """Register monitoring commands with the main typer app.
    
    Args:
        main_app: Main typer application instance
    """
    if TYPER_AVAILABLE and monitoring_app:
        main_app.add_typer(monitoring_app, name="monitoring")
    else:
        # Add individual commands if typer not available
        pass
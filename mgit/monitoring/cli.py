"""Command-line interface for mgit monitoring features.

This module provides CLI commands for monitoring configuration,
metrics collection, and health checks.
"""

import asyncio
import json
import signal
import sys
from pathlib import Path
from typing import Optional

try:
    import typer

    TYPER_AVAILABLE = True
except ImportError:
    TYPER_AVAILABLE = False

from .dashboard import create_monitoring_configuration
from .health import get_health_checker
from .logger import get_structured_logger, setup_structured_logging
from .metrics import get_metrics_collector, setup_metrics
from .performance import get_performance_monitor
from .server import start_monitoring_server, start_simple_monitoring_server

# Create CLI app if typer is available
if TYPER_AVAILABLE:
    monitoring_app = typer.Typer(
        name="monitoring", help="mgit monitoring and observability commands"
    )
else:
    monitoring_app = None


def _ensure_typer():
    """Ensure typer is available."""
    if not TYPER_AVAILABLE:
        print(
            "Error: typer is required for CLI commands. Install with: pip install typer"
        )
        sys.exit(1)


def start_server_command(
    host: str = "127.0.0.1",
    port: int = 8080,
    simple: bool = False,
    log_level: str = "INFO",
) -> None:
    """Start the monitoring server.

    Args:
        host: Server host address
        port: Server port number
        simple: Use simple server (no aiohttp dependency)
        log_level: Logging level
    """
    # Setup logging
    setup_structured_logging(log_level=log_level)
    logger = get_structured_logger("monitoring_cli")

    # Setup metrics and health checks
    setup_metrics()

    logger.info(
        f"Starting monitoring server on {host}:{port}",
        host=host,
        port=port,
        simple=simple,
    )

    if simple:
        # Use simple server
        server = start_simple_monitoring_server(host, port)

        def signal_handler(signum, frame):
            logger.info("Received shutdown signal")
            server.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            logger.info("Monitoring server is running. Press Ctrl+C to stop.")
            signal.pause()
        except KeyboardInterrupt:
            logger.info("Shutting down monitoring server")
            server.stop()

    else:
        # Use async server
        async def run_server():
            server = await start_monitoring_server(host, port)

            def signal_handler():
                logger.info("Received shutdown signal")
                asyncio.create_task(server.stop())

            # Setup signal handlers
            loop = asyncio.get_event_loop()
            for sig in [signal.SIGINT, signal.SIGTERM]:
                loop.add_signal_handler(sig, signal_handler)

            logger.info("Monitoring server is running. Press Ctrl+C to stop.")

            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                await server.stop()

        try:
            asyncio.run(run_server())
        except KeyboardInterrupt:
            logger.info("Shutting down monitoring server")


def health_check_command(detailed: bool = False, json_output: bool = False) -> None:
    """Run health checks and display results.

    Args:
        detailed: Show detailed health check results
        json_output: Output results in JSON format
    """

    async def run_health_check():
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
                "status": "healthy" if (is_ready and is_alive) else "unhealthy",
            }

        if json_output:
            print(json.dumps(health_data, indent=2))
        else:
            if detailed:
                print(f"Overall Status: {health_data['status']}")
                print(
                    f"Health Percentage: {health_data['summary']['health_percentage']:.1f}%"
                )
                print(f"Total Checks: {health_data['summary']['total_checks']}")
                print(f"Healthy Checks: {health_data['summary']['healthy_checks']}")

                if health_data["issues"]:
                    print("\nIssues:")
                    for issue in health_data["issues"]:
                        print(f"  - {issue}")

                print("\nCheck Details:")
                for check_name, check_result in health_data["checks"].items():
                    status_icon = "✓" if check_result["status"] == "healthy" else "✗"
                    print(f"  {status_icon} {check_name}: {check_result['message']}")
            else:
                status_icon = "✓" if health_data["status"] == "healthy" else "✗"
                print(f"{status_icon} Health: {health_data['status']}")
                print(f"  Ready: {health_data['ready']}")
                print(f"  Alive: {health_data['alive']}")

        # Exit with appropriate code
        exit_code = 0 if health_data["status"] == "healthy" else 1
        sys.exit(exit_code)

    asyncio.run(run_health_check())


def metrics_command(
    format_type: str = "prometheus", output_file: Optional[str] = None
) -> None:
    """Export metrics in specified format.

    Args:
        format_type: Output format (prometheus, json)
        output_file: Optional output file path
    """
    metrics = get_metrics_collector()

    if format_type.lower() == "json":
        output = metrics.export_json()
    else:
        output = metrics.export_prometheus()

    if output_file:
        with open(output_file, "w") as f:
            f.write(output)
        print(f"Metrics exported to {output_file}")
    else:
        print(output)


def performance_command(
    operation: Optional[str] = None, hours: int = 24, json_output: bool = False
) -> None:
    """Show performance metrics and statistics.

    Args:
        operation: Specific operation to show metrics for
        hours: Hours to look back
        json_output: Output in JSON format
    """
    performance_monitor = get_performance_monitor()

    if operation:
        metrics = performance_monitor.get_operation_metrics(operation, hours)
        if not metrics:
            print(f"No performance data found for operation: {operation}")
            sys.exit(1)

        if json_output:
            print(
                json.dumps(
                    {
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
                            "success_rate": metrics.success_rate,
                        },
                    },
                    indent=2,
                )
            )
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
            output_data = {}
            for op_name, metrics in summary.items():
                output_data[op_name] = {
                    "count": metrics.count,
                    "avg_duration": metrics.avg_duration,
                    "p95_duration": metrics.p95_duration,
                    "success_rate": metrics.success_rate,
                    "error_count": metrics.error_count,
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


def generate_config_command(
    output_dir: str = "./monitoring",
    datasource: str = "Prometheus",
    namespace: str = "mgit",
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
            output_dir=output_path, datasource_name=datasource, namespace=namespace
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


# Register commands if typer is available
if TYPER_AVAILABLE:

    @monitoring_app.command("server")
    def server_command(
        host: str = typer.Option("127.0.0.1", "--host", "-h", help="Server host"),
        port: int = typer.Option(8080, "--port", "-p", help="Server port"),
        simple: bool = typer.Option(False, "--simple", help="Use simple server"),
        log_level: str = typer.Option("INFO", "--log-level", help="Log level"),
    ):
        """Start the monitoring server."""
        start_server_command(host, port, simple, log_level)

    @monitoring_app.command("health")
    def health_command(
        detailed: bool = typer.Option(
            False, "--detailed", "-d", help="Show detailed results"
        ),
        json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    ):
        """Run health checks."""
        health_check_command(detailed, json_output)

    @monitoring_app.command("metrics")
    def metrics_cmd(
        format_type: str = typer.Option(
            "prometheus", "--format", "-f", help="Output format"
        ),
        output_file: Optional[str] = typer.Option(
            None, "--output", "-o", help="Output file"
        ),
    ):
        """Export metrics."""
        metrics_command(format_type, output_file)

    @monitoring_app.command("performance")
    def performance_cmd(
        operation: Optional[str] = typer.Option(
            None, "--operation", "-op", help="Specific operation"
        ),
        hours: int = typer.Option(24, "--hours", help="Hours to look back"),
        json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    ):
        """Show performance metrics."""
        performance_command(operation, hours, json_output)

    @monitoring_app.command("generate-config")
    def generate_config_cmd(
        output_dir: str = typer.Option(
            "./monitoring", "--output", "-o", help="Output directory"
        ),
        datasource: str = typer.Option(
            "Prometheus", "--datasource", help="Grafana datasource"
        ),
        namespace: str = typer.Option(
            "mgit", "--namespace", help="Alert rules namespace"
        ),
    ):
        """Generate monitoring configuration."""
        generate_config_command(output_dir, datasource, namespace)


# Main function for standalone usage
def main():
    """Main entry point for monitoring CLI."""
    _ensure_typer()

    if len(sys.argv) == 1:
        # Show help if no arguments
        monitoring_app()
    else:
        monitoring_app()


if __name__ == "__main__":
    main()

"""HTTP server for exposing metrics and health endpoints.

This module provides a lightweight HTTP server for exposing
Prometheus metrics and health check endpoints.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime
import threading
import time

try:
    from aiohttp import web, WSMsgType
    from aiohttp.web import Request, Response, json_response

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Always import fallback components for SimpleMonitoringServer
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from .metrics import get_metrics_collector
from .health import get_health_checker
from .logger import get_structured_logger


class MonitoringServer:
    """HTTP server for monitoring endpoints."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        """Initialize monitoring server.

        Args:
            host: Server host
            port: Server port
        """
        self.host = host
        self.port = port
        self.logger = get_structured_logger("monitoring_server")
        self.metrics = get_metrics_collector()
        self.health_checker = get_health_checker()

        self._server: Optional[Any] = None
        self._runner: Optional[Any] = None
        self._site: Optional[Any] = None
        self._running = False

        # Track request metrics
        self._request_count = 0
        self._start_time = time.time()

    async def start(self) -> None:
        """Start the monitoring server."""
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError(
                "aiohttp is required for the monitoring server. Install with: pip install aiohttp"
            )

        if self._running:
            return

        # Create application and routes
        app = web.Application()

        # Metrics endpoints
        app.router.add_get("/metrics", self._metrics_handler)
        app.router.add_get("/metrics/json", self._metrics_json_handler)

        # Health check endpoints
        app.router.add_get("/health", self._health_handler)
        app.router.add_get("/health/ready", self._readiness_handler)
        app.router.add_get("/health/live", self._liveness_handler)
        app.router.add_get("/health/detailed", self._detailed_health_handler)

        # Info endpoints
        app.router.add_get("/info", self._info_handler)
        app.router.add_get("/status", self._status_handler)

        # Root endpoint
        app.router.add_get("/", self._root_handler)

        # Add middleware for request logging and metrics
        app.middlewares.append(self._request_middleware)

        # Create runner and start server
        self._runner = web.AppRunner(app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()

        self._running = True

        self.logger.info(
            f"Monitoring server started on {self.host}:{self.port}",
            host=self.host,
            port=self.port,
            endpoints=[
                "/metrics",
                "/metrics/json",
                "/health",
                "/health/ready",
                "/health/live",
                "/health/detailed",
                "/info",
                "/status",
            ],
        )

    async def stop(self) -> None:
        """Stop the monitoring server."""
        if not self._running:
            return

        if self._site:
            await self._site.stop()
            self._site = None

        if self._runner:
            await self._runner.cleanup()
            self._runner = None

        self._running = False

        self.logger.info("Monitoring server stopped")

    async def _request_middleware(
        self, request: Request, handler: Callable
    ) -> Response:
        """Middleware for request logging and metrics."""
        start_time = time.time()
        self._request_count += 1

        # Extract request info
        method = request.method
        path = request.path
        user_agent = request.headers.get("User-Agent", "")

        try:
            response = await handler(request)
            status_code = response.status
            success = status_code < 400

        except Exception as e:
            self.logger.error(
                f"Request handler error: {str(e)}",
                method=method,
                path=path,
                error=str(e),
            )
            status_code = 500
            success = False
            response = web.json_response({"error": "Internal server error"}, status=500)

        # Calculate duration
        duration = time.time() - start_time

        # Record metrics
        self.metrics.record_api_call(
            method=method,
            provider="monitoring_server",
            status_code=status_code,
            duration=duration,
            endpoint=path,
        )

        # Log request
        self.logger.info(
            f"{method} {path} -> {status_code}",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration * 1000,
            user_agent=user_agent,
            success=success,
        )

        return response

    async def _metrics_handler(self, request: Request) -> Response:
        """Handle /metrics endpoint (Prometheus format)."""
        try:
            metrics_text = self.metrics.export_prometheus()
            return Response(
                text=metrics_text,
                content_type="text/plain; version=0.0.4; charset=utf-8",
            )
        except Exception as e:
            self.logger.error(f"Error exporting metrics: {str(e)}")
            return web.json_response({"error": "Failed to export metrics"}, status=500)

    async def _metrics_json_handler(self, request: Request) -> Response:
        """Handle /metrics/json endpoint (JSON format)."""
        try:
            metrics_json = self.metrics.export_json()
            return Response(text=metrics_json, content_type="application/json")
        except Exception as e:
            self.logger.error(f"Error exporting metrics JSON: {str(e)}")
            return web.json_response({"error": "Failed to export metrics"}, status=500)

    async def _health_handler(self, request: Request) -> Response:
        """Handle /health endpoint."""
        try:
            health_data = await self.health_checker.get_overall_health()
            status_code = 200 if health_data["status"] == "healthy" else 503

            return web.json_response(health_data, status=status_code)

        except Exception as e:
            self.logger.error(f"Error getting health status: {str(e)}")
            return web.json_response(
                {
                    "status": "error",
                    "message": f"Health check failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                },
                status=500,
            )

    async def _readiness_handler(self, request: Request) -> Response:
        """Handle /health/ready endpoint (Kubernetes readiness probe)."""
        try:
            is_ready = await self.health_checker.is_ready()

            if is_ready:
                return web.json_response(
                    {"status": "ready", "timestamp": datetime.now().isoformat()},
                    status=200,
                )
            else:
                return web.json_response(
                    {"status": "not_ready", "timestamp": datetime.now().isoformat()},
                    status=503,
                )

        except Exception as e:
            self.logger.error(f"Error checking readiness: {str(e)}")
            return web.json_response(
                {
                    "status": "error",
                    "message": f"Readiness check failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                },
                status=500,
            )

    async def _liveness_handler(self, request: Request) -> Response:
        """Handle /health/live endpoint (Kubernetes liveness probe)."""
        try:
            is_alive = await self.health_checker.is_alive()

            if is_alive:
                return web.json_response(
                    {"status": "alive", "timestamp": datetime.now().isoformat()},
                    status=200,
                )
            else:
                return web.json_response(
                    {"status": "not_alive", "timestamp": datetime.now().isoformat()},
                    status=503,
                )

        except Exception as e:
            self.logger.error(f"Error checking liveness: {str(e)}")
            return web.json_response(
                {
                    "status": "error",
                    "message": f"Liveness check failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                },
                status=500,
            )

    async def _detailed_health_handler(self, request: Request) -> Response:
        """Handle /health/detailed endpoint."""
        try:
            health_data = await self.health_checker.get_overall_health(use_cache=False)
            status_code = 200  # Always return 200 for detailed view

            return web.json_response(health_data, status=status_code)

        except Exception as e:
            self.logger.error(f"Error getting detailed health: {str(e)}")
            return web.json_response(
                {
                    "status": "error",
                    "message": f"Detailed health check failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                },
                status=500,
            )

    async def _info_handler(self, request: Request) -> Response:
        """Handle /info endpoint."""
        try:
            from ..constants import __version__

            uptime = time.time() - self._start_time

            info_data = {
                "application": "mgit",
                "version": __version__,
                "uptime_seconds": uptime,
                "start_time": datetime.fromtimestamp(self._start_time).isoformat(),
                "current_time": datetime.now().isoformat(),
                "request_count": self._request_count,
                "monitoring": {
                    "metrics_enabled": True,
                    "health_checks_enabled": True,
                    "structured_logging": True,
                    "performance_monitoring": True,
                },
                "endpoints": {
                    "metrics": "/metrics",
                    "metrics_json": "/metrics/json",
                    "health": "/health",
                    "readiness": "/health/ready",
                    "liveness": "/health/live",
                    "detailed_health": "/health/detailed",
                    "status": "/status",
                    "info": "/info",
                },
            }

            return web.json_response(info_data)

        except Exception as e:
            self.logger.error(f"Error getting info: {str(e)}")
            return web.json_response(
                {"error": "Failed to get application info"}, status=500
            )

    async def _status_handler(self, request: Request) -> Response:
        """Handle /status endpoint (simple status check)."""
        try:
            is_healthy = (await self.health_checker.get_overall_health())[
                "status"
            ] == "healthy"

            status_data = {
                "status": "ok" if is_healthy else "degraded",
                "healthy": is_healthy,
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": time.time() - self._start_time,
            }

            return web.json_response(status_data)

        except Exception as e:
            self.logger.error(f"Error getting status: {str(e)}")
            return web.json_response(
                {
                    "status": "error",
                    "healthy": False,
                    "message": f"Status check failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                },
                status=500,
            )

    async def _root_handler(self, request: Request) -> Response:
        """Handle / endpoint (welcome page)."""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>mgit Monitoring</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .endpoint { margin: 10px 0; }
        .endpoint a { text-decoration: none; color: #0066cc; }
        .endpoint a:hover { text-decoration: underline; }
        .description { color: #666; font-size: 0.9em; margin-left: 20px; }
    </style>
</head>
<body>
    <h1>mgit Monitoring</h1>
    <p>Multi-Git Tool monitoring and observability endpoints.</p>
    
    <h2>Available Endpoints</h2>
    
    <div class="endpoint">
        <a href="/metrics">/metrics</a>
        <div class="description">Prometheus metrics (text format)</div>
    </div>
    
    <div class="endpoint">
        <a href="/metrics/json">/metrics/json</a>
        <div class="description">Metrics in JSON format</div>
    </div>
    
    <div class="endpoint">
        <a href="/health">/health</a>
        <div class="description">Overall health status</div>
    </div>
    
    <div class="endpoint">
        <a href="/health/ready">/health/ready</a>
        <div class="description">Readiness probe (Kubernetes)</div>
    </div>
    
    <div class="endpoint">
        <a href="/health/live">/health/live</a>
        <div class="description">Liveness probe (Kubernetes)</div>
    </div>
    
    <div class="endpoint">
        <a href="/health/detailed">/health/detailed</a>
        <div class="description">Detailed health check results</div>
    </div>
    
    <div class="endpoint">
        <a href="/info">/info</a>
        <div class="description">Application information</div>
    </div>
    
    <div class="endpoint">
        <a href="/status">/status</a>
        <div class="description">Simple status check</div>
    </div>
    
    <h2>Usage</h2>
    <p>Configure your monitoring system to scrape <code>/metrics</code> for Prometheus metrics.</p>
    <p>Use <code>/health/ready</code> and <code>/health/live</code> for Kubernetes probes.</p>
</body>
</html>
        """

        return Response(text=html_content, content_type="text/html")


# Simple fallback server for environments without aiohttp
class SimpleMonitoringServer:
    """Simple HTTP server fallback when aiohttp is not available."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        """Initialize simple monitoring server.

        Args:
            host: Server host
            port: Server port
        """
        self.host = host
        self.port = port
        self.logger = get_structured_logger("simple_monitoring_server")
        self.metrics = get_metrics_collector()
        self.health_checker = get_health_checker()

        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        """Start the simple monitoring server."""
        if self._running:
            return

        # Create request handler
        metrics = self.metrics
        health_checker = self.health_checker
        logger = self.logger

        class MonitoringRequestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                try:
                    parsed_url = urlparse(self.path)
                    path = parsed_url.path

                    if path == "/metrics":
                        self._handle_metrics()
                    elif path == "/health":
                        self._handle_health()
                    elif path == "/health/ready":
                        self._handle_readiness()
                    elif path == "/health/live":
                        self._handle_liveness()
                    elif path == "/info":
                        self._handle_info()
                    else:
                        self._handle_not_found()

                except Exception as e:
                    logger.error(f"Request handler error: {str(e)}")
                    self._send_error(500, "Internal server error")

            def _handle_metrics(self):
                try:
                    metrics_text = metrics.export_prometheus()
                    self._send_response(200, metrics_text, "text/plain")
                except Exception as e:
                    self._send_error(500, f"Failed to export metrics: {str(e)}")

            def _handle_health(self):
                try:
                    # Simplified synchronous health check
                    health_data = {
                        "status": "healthy",
                        "timestamp": datetime.now().isoformat(),
                    }
                    self._send_json_response(200, health_data)
                except Exception as e:
                    self._send_error(500, f"Health check failed: {str(e)}")

            def _handle_readiness(self):
                self._send_json_response(
                    200, {"status": "ready", "timestamp": datetime.now().isoformat()}
                )

            def _handle_liveness(self):
                self._send_json_response(
                    200, {"status": "alive", "timestamp": datetime.now().isoformat()}
                )

            def _handle_info(self):
                try:
                    from ..constants import __version__

                    info_data = {
                        "application": "mgit",
                        "version": __version__,
                        "timestamp": datetime.now().isoformat(),
                        "monitoring": "simple_server",
                    }
                    self._send_json_response(200, info_data)
                except Exception as e:
                    self._send_error(500, f"Failed to get info: {str(e)}")

            def _handle_not_found(self):
                self._send_error(404, "Not found")

            def _send_response(self, status_code, content, content_type):
                self.send_response(status_code)
                self.send_header("Content-type", content_type)
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))

            def _send_json_response(self, status_code, data):
                content = json.dumps(data)
                self._send_response(status_code, content, "application/json")

            def _send_error(self, status_code, message):
                self._send_json_response(status_code, {"error": message})

            def log_message(self, format, *args):
                # Suppress default logging
                pass

        # Create and start server
        self._server = HTTPServer((self.host, self.port), MonitoringRequestHandler)
        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.daemon = True
        self._thread.start()

        self._running = True

        self.logger.info(f"Simple monitoring server started on {self.host}:{self.port}")

    def stop(self) -> None:
        """Stop the simple monitoring server."""
        if not self._running:
            return

        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

        self._running = False

        self.logger.info("Simple monitoring server stopped")


# Global monitoring server instance
_monitoring_server: Optional[MonitoringServer] = None


def get_monitoring_server(host: str = "0.0.0.0", port: int = 8080) -> MonitoringServer:
    """Get global monitoring server instance.

    Args:
        host: Server host
        port: Server port

    Returns:
        MonitoringServer instance
    """
    global _monitoring_server
    if _monitoring_server is None:
        _monitoring_server = MonitoringServer(host, port)
    return _monitoring_server


async def start_monitoring_server(
    host: str = "0.0.0.0", port: int = 8080
) -> MonitoringServer:
    """Start the monitoring server.

    Args:
        host: Server host
        port: Server port

    Returns:
        Started MonitoringServer instance
    """
    server = get_monitoring_server(host, port)
    await server.start()
    return server


def start_simple_monitoring_server(
    host: str = "0.0.0.0", port: int = 8080
) -> SimpleMonitoringServer:
    """Start the simple monitoring server (fallback).

    Args:
        host: Server host
        port: Server port

    Returns:
        Started SimpleMonitoringServer instance
    """
    server = SimpleMonitoringServer(host, port)
    server.start()
    return server

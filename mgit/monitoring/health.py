"""Health check system for mgit.

This module provides comprehensive health checks including dependency
checks, readiness and liveness probes for Kubernetes deployments.
"""

import time
import asyncio
import subprocess
import socket
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import tempfile
import os

from .logger import get_structured_logger
from .metrics import get_metrics_collector


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: str  # "healthy", "unhealthy", "unknown"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class HealthChecker:
    """Comprehensive health check system."""
    
    def __init__(self):
        """Initialize health checker."""
        self.logger = get_structured_logger("health_checker")
        self.metrics = get_metrics_collector()
        
        # Health check registry
        self._checks: Dict[str, Callable[[], Awaitable[HealthCheckResult]]] = {}
        self._check_intervals: Dict[str, int] = {}  # seconds
        self._last_results: Dict[str, HealthCheckResult] = {}
        
        # Register default health checks
        self._register_default_checks()
        
        # Overall health cache
        self._overall_health_cache: Optional[Dict[str, Any]] = None
        self._cache_expiry: Optional[datetime] = None
        self._cache_ttl = 30  # seconds
    
    def _register_default_checks(self) -> None:
        """Register default health checks."""
        self.register_check("system_basics", self._check_system_basics, interval=60)
        self.register_check("git_availability", self._check_git_availability, interval=60)
        self.register_check("network_connectivity", self._check_network_connectivity, interval=30)
        self.register_check("disk_space", self._check_disk_space, interval=60)
        self.register_check("memory_usage", self._check_memory_usage, interval=30)
        self.register_check("provider_endpoints", self._check_provider_endpoints, interval=120)
        self.register_check("authentication_status", self._check_authentication_status, interval=300)
    
    def register_check(self, name: str, check_func: Callable[[], Awaitable[HealthCheckResult]], 
                      interval: int = 60) -> None:
        """Register a health check.
        
        Args:
            name: Health check name
            check_func: Async function that performs the check
            interval: Check interval in seconds
        """
        self._checks[name] = check_func
        self._check_intervals[name] = interval
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check.
        
        Args:
            name: Name of the health check to run
            
        Returns:
            Health check result
        """
        if name not in self._checks:
            return HealthCheckResult(
                name=name,
                status="unknown",
                message=f"Health check '{name}' not found"
            )
        
        start_time = time.time()
        
        try:
            result = await self._checks[name]()
            result.duration_ms = (time.time() - start_time) * 1000
            
            # Cache result
            self._last_results[name] = result
            
            # Record metrics
            self.metrics.set_gauge(
                "mgit_health_check_status",
                1.0 if result.status == "healthy" else 0.0,
                labels={"check": name}
            )
            self.metrics.observe_histogram(
                "mgit_health_check_duration_seconds",
                result.duration_ms / 1000,
                labels={"check": name}
            )
            
            self.logger.info(f"Health check '{name}' completed",
                           check_name=name,
                           status=result.status,
                           duration_ms=result.duration_ms)
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                name=name,
                status="unhealthy",
                message=f"Health check failed: {str(e)}",
                duration_ms=duration_ms,
                details={"error": str(e), "error_type": type(e).__name__}
            )
            
            self._last_results[name] = result
            
            # Record metrics
            self.metrics.set_gauge(
                "mgit_health_check_status",
                0.0,
                labels={"check": name}
            )
            
            self.logger.error(f"Health check '{name}' failed",
                            check_name=name,
                            error=str(e),
                            duration_ms=duration_ms)
            
            return result
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks.
        
        Returns:
            Dictionary of health check results
        """
        tasks = []
        for name in self._checks:
            tasks.append(self.run_check(name))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        check_results = {}
        for i, (name, result) in enumerate(zip(self._checks.keys(), results)):
            if isinstance(result, Exception):
                check_results[name] = HealthCheckResult(
                    name=name,
                    status="unhealthy",
                    message=f"Health check failed: {str(result)}",
                    details={"error": str(result), "error_type": type(result).__name__}
                )
            else:
                check_results[name] = result
        
        return check_results
    
    async def get_overall_health(self, use_cache: bool = True) -> Dict[str, Any]:
        """Get overall system health status.
        
        Args:
            use_cache: Whether to use cached result if available
            
        Returns:
            Overall health status dictionary
        """
        # Check cache
        if (use_cache and self._overall_health_cache and self._cache_expiry and 
            datetime.now() < self._cache_expiry):
            return self._overall_health_cache
        
        results = await self.run_all_checks()
        
        # Calculate overall status
        healthy_count = sum(1 for r in results.values() if r.status == "healthy")
        total_count = len(results)
        unhealthy_checks = [name for name, r in results.items() if r.status != "healthy"]
        
        if healthy_count == total_count:
            overall_status = "healthy"
        elif healthy_count > total_count / 2:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        health_data = {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_checks": total_count,
                "healthy_checks": healthy_count,
                "unhealthy_checks": total_count - healthy_count,
                "health_percentage": (healthy_count / total_count * 100) if total_count > 0 else 0
            },
            "checks": {name: {
                "status": result.status,
                "message": result.message,
                "duration_ms": result.duration_ms,
                "timestamp": result.timestamp.isoformat(),
                "details": result.details
            } for name, result in results.items()},
            "issues": unhealthy_checks
        }
        
        # Cache result
        self._overall_health_cache = health_data
        self._cache_expiry = datetime.now() + timedelta(seconds=self._cache_ttl)
        
        # Record overall health metric
        self.metrics.set_gauge("mgit_health_overall", 
                              1.0 if overall_status == "healthy" else 0.0)
        self.metrics.set_gauge("mgit_health_percentage", 
                              health_data["summary"]["health_percentage"])
        
        return health_data
    
    async def is_ready(self) -> bool:
        """Check if the system is ready to serve requests (readiness probe).
        
        Returns:
            True if system is ready
        """
        # For readiness, we only check critical dependencies
        critical_checks = ["git_availability", "system_basics"]
        
        for check_name in critical_checks:
            result = await self.run_check(check_name)
            if result.status != "healthy":
                self.logger.warning(f"Readiness check failed: {check_name}",
                                  check_name=check_name,
                                  status=result.status,
                                  message=result.message)
                return False
        
        return True
    
    async def is_alive(self) -> bool:
        """Check if the system is alive (liveness probe).
        
        Returns:
            True if system is alive
        """
        # For liveness, we do a minimal check
        try:
            result = await self._check_system_basics()
            return result.status == "healthy"
        except Exception as e:
            self.logger.error("Liveness check failed", error=str(e))
            return False
    
    # Individual health check implementations
    
    async def _check_system_basics(self) -> HealthCheckResult:
        """Check basic system functionality."""
        try:
            # Check if we can create temporary files
            with tempfile.NamedTemporaryFile() as f:
                f.write(b"health check")
                f.flush()
            
            # Check current working directory
            cwd = os.getcwd()
            
            # Check environment
            python_version = f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
            
            return HealthCheckResult(
                name="system_basics",
                status="healthy",
                message="System basics are functioning correctly",
                details={
                    "python_version": python_version,
                    "working_directory": cwd,
                    "temp_dir_writable": True
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="system_basics",
                status="unhealthy",
                message=f"System basics check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _check_git_availability(self) -> HealthCheckResult:
        """Check if Git is available and working."""
        try:
            # Check if git command is available
            result = subprocess.run(['git', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                git_version = result.stdout.strip()
                return HealthCheckResult(
                    name="git_availability",
                    status="healthy",
                    message="Git is available and working",
                    details={"git_version": git_version}
                )
            else:
                return HealthCheckResult(
                    name="git_availability",
                    status="unhealthy",
                    message="Git command failed",
                    details={"stderr": result.stderr, "returncode": result.returncode}
                )
                
        except subprocess.TimeoutExpired:
            return HealthCheckResult(
                name="git_availability",
                status="unhealthy",
                message="Git command timed out"
            )
        except FileNotFoundError:
            return HealthCheckResult(
                name="git_availability",
                status="unhealthy",
                message="Git command not found"
            )
        except Exception as e:
            return HealthCheckResult(
                name="git_availability",
                status="unhealthy",
                message=f"Git availability check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _check_network_connectivity(self) -> HealthCheckResult:
        """Check basic network connectivity."""
        test_hosts = [
            ("github.com", 443),
            ("dev.azure.com", 443),
            ("api.bitbucket.org", 443)
        ]
        
        results = {}
        overall_status = "healthy"
        
        for host, port in test_hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    results[host] = "reachable"
                else:
                    results[host] = "unreachable"
                    overall_status = "degraded"
                    
            except Exception as e:
                results[host] = f"error: {str(e)}"
                overall_status = "degraded"
        
        reachable_count = sum(1 for status in results.values() if status == "reachable")
        
        if reachable_count == 0:
            overall_status = "unhealthy"
        
        return HealthCheckResult(
            name="network_connectivity",
            status=overall_status,
            message=f"Network connectivity: {reachable_count}/{len(test_hosts)} hosts reachable",
            details=results
        )
    
    async def _check_disk_space(self) -> HealthCheckResult:
        """Check available disk space."""
        try:
            import shutil
            
            # Check current directory
            total, used, free = shutil.disk_usage('.')
            
            # Convert to GB
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            
            usage_percent = (used / total) * 100
            
            # Determine status based on available space
            if free_gb < 1.0:  # Less than 1GB free
                status = "unhealthy"
                message = f"Critical: Only {free_gb:.1f}GB disk space remaining"
            elif usage_percent > 90:
                status = "unhealthy"
                message = f"Critical: Disk usage at {usage_percent:.1f}%"
            elif usage_percent > 80:
                status = "degraded"
                message = f"Warning: Disk usage at {usage_percent:.1f}%"
            else:
                status = "healthy"
                message = f"Disk space healthy: {free_gb:.1f}GB free ({usage_percent:.1f}% used)"
            
            return HealthCheckResult(
                name="disk_space",
                status=status,
                message=message,
                details={
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "usage_percent": round(usage_percent, 2)
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="disk_space",
                status="unknown",
                message=f"Could not check disk space: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _check_memory_usage(self) -> HealthCheckResult:
        """Check memory usage."""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            
            # Convert to GB
            total_gb = memory.total / (1024**3)
            available_gb = memory.available / (1024**3)
            used_gb = (memory.total - memory.available) / (1024**3)
            
            usage_percent = memory.percent
            
            # Determine status
            if usage_percent > 95:
                status = "unhealthy"
                message = f"Critical: Memory usage at {usage_percent:.1f}%"
            elif usage_percent > 85:
                status = "degraded"
                message = f"Warning: Memory usage at {usage_percent:.1f}%"
            else:
                status = "healthy"
                message = f"Memory usage healthy: {usage_percent:.1f}% used"
            
            return HealthCheckResult(
                name="memory_usage",
                status=status,
                message=message,
                details={
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "available_gb": round(available_gb, 2),
                    "usage_percent": round(usage_percent, 2)
                }
            )
            
        except ImportError:
            return HealthCheckResult(
                name="memory_usage",
                status="unknown",
                message="psutil not available for memory monitoring",
                details={"error": "psutil not installed"}
            )
        except Exception as e:
            return HealthCheckResult(
                name="memory_usage",
                status="unknown",
                message=f"Could not check memory usage: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _check_provider_endpoints(self) -> HealthCheckResult:
        """Check if provider API endpoints are accessible."""
        # This is a basic connectivity check - not authenticated
        endpoints = {
            "github": "https://api.github.com",
            "azure-devops": "https://dev.azure.com",
            "bitbucket": "https://api.bitbucket.org"
        }
        
        results = {}
        overall_status = "healthy"
        
        for provider, url in endpoints.items():
            try:
                import urllib.request
                
                request = urllib.request.Request(url)
                request.add_header('User-Agent', 'mgit-health-check')
                
                with urllib.request.urlopen(request, timeout=10) as response:
                    status_code = response.getcode()
                    if status_code < 400:
                        results[provider] = "accessible"
                    else:
                        results[provider] = f"http_{status_code}"
                        overall_status = "degraded"
                        
            except Exception as e:
                results[provider] = f"error: {str(e)}"
                overall_status = "degraded"
        
        accessible_count = sum(1 for status in results.values() if status == "accessible")
        
        if accessible_count == 0:
            overall_status = "unhealthy"
        
        return HealthCheckResult(
            name="provider_endpoints",
            status=overall_status,
            message=f"Provider endpoints: {accessible_count}/{len(endpoints)} accessible",
            details=results
        )
    
    async def _check_authentication_status(self) -> HealthCheckResult:
        """Check authentication status for configured providers."""
        # This would check if we have valid tokens/credentials
        # For now, it's a placeholder that checks if config exists
        
        try:
            from ..config.manager import get_config_value
            
            providers_configured = 0
            providers_checked = 0
            auth_details = {}
            
            for provider in ["github", "azure-devops", "bitbucket"]:
                token_key = f"{provider.replace('-', '_')}_token"
                token = get_config_value(token_key)
                
                if token:
                    providers_configured += 1
                    providers_checked += 1
                    auth_details[provider] = "token_configured"
                else:
                    auth_details[provider] = "no_token"
            
            if providers_configured == 0:
                status = "degraded"
                message = "No authentication tokens configured"
            else:
                status = "healthy"
                message = f"Authentication configured for {providers_configured} providers"
            
            return HealthCheckResult(
                name="authentication_status",
                status=status,
                message=message,
                details={
                    "providers_configured": providers_configured,
                    "provider_details": auth_details
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="authentication_status",
                status="unknown",
                message=f"Could not check authentication status: {str(e)}",
                details={"error": str(e)}
            )


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get global health checker instance.
    
    Returns:
        HealthChecker instance
    """
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


# Convenience functions for Kubernetes probes
async def readiness_probe() -> bool:
    """Kubernetes readiness probe.
    
    Returns:
        True if system is ready
    """
    checker = get_health_checker()
    return await checker.is_ready()


async def liveness_probe() -> bool:
    """Kubernetes liveness probe.
    
    Returns:
        True if system is alive
    """
    checker = get_health_checker()
    return await checker.is_alive()


async def health_check_endpoint() -> Dict[str, Any]:
    """Health check endpoint for monitoring systems.
    
    Returns:
        Complete health status
    """
    checker = get_health_checker()
    return await checker.get_overall_health()
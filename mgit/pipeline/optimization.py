"""
Performance optimization utilities for change pipeline operations.

Provides intelligent optimization, resource management, and performance
enhancement capabilities for large-scale repository processing operations.
"""

import asyncio
import concurrent.futures
import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mgit.pipeline.monitoring import PipelineMonitor, monitor_pipeline_operation

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """Optimization strategies for pipeline operations."""

    BALANCED = "balanced"  # Balance performance and resource usage
    PERFORMANCE = "performance"  # Maximize performance, higher resource usage
    EFFICIENCY = "efficiency"  # Minimize resource usage, acceptable performance
    THROUGHPUT = "throughput"  # Maximize throughput for batch operations
    LATENCY = "latency"  # Minimize latency for interactive operations


@dataclass
class ResourceLimits:
    """Resource limits for pipeline operations."""

    max_concurrent_operations: int = 10
    max_memory_mb: int = 1024  # 1GB
    max_cpu_percent: int = 80
    operation_timeout_seconds: int = 300  # 5 minutes
    semaphore_timeout_seconds: int = 60


@dataclass
class PerformanceProfile:
    """Performance profile for optimization."""

    strategy: OptimizationStrategy
    resource_limits: ResourceLimits
    batch_size: int = 100
    prefetch_enabled: bool = True
    caching_enabled: bool = True
    compression_enabled: bool = True
    monitoring_enabled: bool = True


@dataclass
class OptimizationResult:
    """Result of optimization operation."""

    strategy_applied: OptimizationStrategy
    performance_improvement_percent: float
    resource_usage_reduction_percent: float
    optimizations_applied: list[str]
    recommendations: list[str]
    metrics: dict[str, Any] = field(default_factory=dict)


class PipelineOptimizer:
    """
    Intelligent optimizer for pipeline operations with automatic performance
    tuning and resource management capabilities.
    """

    # Predefined performance profiles
    PROFILES = {
        OptimizationStrategy.BALANCED: PerformanceProfile(
            strategy=OptimizationStrategy.BALANCED,
            resource_limits=ResourceLimits(
                max_concurrent_operations=5,
                max_memory_mb=512,
                max_cpu_percent=70,
                operation_timeout_seconds=180,
            ),
            batch_size=50,
            prefetch_enabled=True,
            caching_enabled=True,
            compression_enabled=True,
        ),
        OptimizationStrategy.PERFORMANCE: PerformanceProfile(
            strategy=OptimizationStrategy.PERFORMANCE,
            resource_limits=ResourceLimits(
                max_concurrent_operations=20,
                max_memory_mb=2048,
                max_cpu_percent=90,
                operation_timeout_seconds=600,
            ),
            batch_size=200,
            prefetch_enabled=True,
            caching_enabled=False,  # Skip caching for max performance
            compression_enabled=False,  # Skip compression for speed
        ),
        OptimizationStrategy.EFFICIENCY: PerformanceProfile(
            strategy=OptimizationStrategy.EFFICIENCY,
            resource_limits=ResourceLimits(
                max_concurrent_operations=2,
                max_memory_mb=256,
                max_cpu_percent=50,
                operation_timeout_seconds=120,
            ),
            batch_size=10,
            prefetch_enabled=False,
            caching_enabled=True,
            compression_enabled=True,
        ),
        OptimizationStrategy.THROUGHPUT: PerformanceProfile(
            strategy=OptimizationStrategy.THROUGHPUT,
            resource_limits=ResourceLimits(
                max_concurrent_operations=50,
                max_memory_mb=4096,
                max_cpu_percent=95,
                operation_timeout_seconds=1800,
            ),
            batch_size=500,
            prefetch_enabled=True,
            caching_enabled=True,
            compression_enabled=True,
        ),
        OptimizationStrategy.LATENCY: PerformanceProfile(
            strategy=OptimizationStrategy.LATENCY,
            resource_limits=ResourceLimits(
                max_concurrent_operations=1,
                max_memory_mb=128,
                max_cpu_percent=60,
                operation_timeout_seconds=30,
            ),
            batch_size=1,
            prefetch_enabled=False,
            caching_enabled=True,
            compression_enabled=True,
        ),
    }

    def __init__(self, strategy: OptimizationStrategy = OptimizationStrategy.BALANCED):
        """
        Initialize pipeline optimizer.

        Args:
            strategy: Default optimization strategy
        """
        self.default_strategy = strategy
        self.active_operations: dict[str, asyncio.Task] = {}
        self.resource_semaphore = asyncio.Semaphore(
            self.PROFILES[strategy].resource_limits.max_concurrent_operations
        )
        self.monitor = PipelineMonitor()

        # Optimization statistics
        self.stats = {
            "operations_optimized": 0,
            "performance_improvements": [],
            "resource_savings": [],
            "optimization_failures": 0,
        }

        logger.debug(f"Pipeline optimizer initialized with {strategy.value} strategy")

    def optimize_operation(
        self,
        operation_func: Callable,
        operation_name: str,
        items: list[Any],
        strategy: OptimizationStrategy | None = None,
        **operation_kwargs,
    ) -> Any:
        """
        Execute operation with automatic optimization.

        Args:
            operation_func: Operation function to optimize
            operation_name: Name of the operation
            items: Items to process
            strategy: Optional optimization strategy override
            **operation_kwargs: Additional arguments for operation

        Returns:
            Result of optimized operation
        """
        strategy = strategy or self.default_strategy
        profile = self.PROFILES[strategy]

        logger.info(
            f"Optimizing operation '{operation_name}' with {strategy.value} strategy"
        )

        # Analyze workload characteristics
        workload_analysis = self._analyze_workload(items)

        # Adapt profile based on workload
        adapted_profile = self._adapt_profile_for_workload(profile, workload_analysis)

        # Execute with optimization
        return self._execute_with_optimization(
            operation_func, operation_name, items, adapted_profile, **operation_kwargs
        )

    async def optimize_async_operation(
        self,
        operation_func: Callable,
        operation_name: str,
        items: list[Any],
        strategy: OptimizationStrategy | None = None,
        **operation_kwargs,
    ) -> Any:
        """
        Execute async operation with automatic optimization.

        Args:
            operation_func: Async operation function to optimize
            operation_name: Name of the operation
            items: Items to process
            strategy: Optional optimization strategy override
            **operation_kwargs: Additional arguments for operation

        Returns:
            Result of optimized operation
        """
        strategy = strategy or self.default_strategy
        profile = self.PROFILES[strategy]

        logger.info(
            f"Optimizing async operation '{operation_name}' with {strategy.value} strategy"
        )

        # Analyze workload characteristics
        workload_analysis = self._analyze_workload(items)

        # Adapt profile based on workload
        adapted_profile = self._adapt_profile_for_workload(profile, workload_analysis)

        # Execute with optimization
        return await self._execute_async_with_optimization(
            operation_func, operation_name, items, adapted_profile, **operation_kwargs
        )

    @asynccontextmanager
    async def optimized_resource_context(
        self, operation_name: str, strategy: OptimizationStrategy | None = None
    ):
        """
        Context manager for optimized resource usage.

        Args:
            operation_name: Name of the operation
            strategy: Optional optimization strategy
        """
        strategy = strategy or self.default_strategy
        profile = self.PROFILES[strategy]

        operation_id = f"{operation_name}_resource_context_{int(time.time() * 1000)}"

        try:
            # Acquire resources
            await self._acquire_resources(operation_id, profile.resource_limits)

            # Set up monitoring
            if profile.monitoring_enabled:
                monitor_operation_id = self.monitor.start_operation(
                    operation_name=f"{operation_name}_optimized",
                    operation_type="resource_context",
                )

            logger.debug(f"Entered optimized resource context for {operation_name}")
            yield

        finally:
            # Release resources
            await self._release_resources(operation_id)

            # End monitoring
            if profile.monitoring_enabled:
                self.monitor.end_operation(monitor_operation_id, success=True)

            logger.debug(f"Exited optimized resource context for {operation_name}")

    def get_optimization_recommendations(
        self,
        operation_name: str,
        current_performance: dict[str, Any],
        target_improvement: float = 0.2,
    ) -> list[str]:
        """
        Get optimization recommendations based on current performance.

        Args:
            operation_name: Name of the operation
            current_performance: Current performance metrics
            target_improvement: Target improvement percentage

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        # Analyze performance bottlenecks
        duration = current_performance.get("duration_seconds", 0)
        memory_usage = current_performance.get("memory_mb", 0)
        cpu_usage = current_performance.get("cpu_percent", 0)
        throughput = current_performance.get("items_per_second", 0)

        if duration > 60:  # Long-running operation
            recommendations.append(
                "Consider using THROUGHPUT optimization strategy for batch operations"
            )
            recommendations.append("Enable compression to reduce I/O overhead")

        if memory_usage > 1000:  # High memory usage
            recommendations.append(
                "Switch to EFFICIENCY strategy to reduce memory footprint"
            )
            recommendations.append("Enable streaming processing for large datasets")

        if cpu_usage > 80:  # High CPU usage
            recommendations.append(
                "Consider BALANCED strategy to prevent CPU saturation"
            )
            recommendations.append("Enable prefetching to improve CPU utilization")

        if throughput < 10:  # Low throughput
            recommendations.append("Use PERFORMANCE strategy for maximum throughput")
            recommendations.append("Increase batch size and concurrency limits")

        if len(recommendations) == 0:
            recommendations.append("Current performance is optimal for the workload")

        return recommendations

    def analyze_performance_bottlenecks(
        self, operation_metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze performance bottlenecks in operation metrics.

        Args:
            operation_metrics: Operation performance metrics

        Returns:
            Analysis of performance bottlenecks
        """
        analysis = {
            "bottlenecks": [],
            "optimization_opportunities": [],
            "resource_efficiency": "unknown",
            "scalability_concerns": [],
        }

        # Analyze timing
        if operation_metrics.get("duration_seconds", 0) > 300:  # 5+ minutes
            analysis["bottlenecks"].append("long_running_operation")
            analysis["optimization_opportunities"].append("consider_parallelization")

        # Analyze memory usage
        memory_mb = operation_metrics.get("memory_mb", 0)
        if memory_mb > 2000:  # 2GB+
            analysis["bottlenecks"].append("high_memory_usage")
            analysis["optimization_opportunities"].append("implement_streaming")
        elif memory_mb < 100:  # Very low memory
            analysis["resource_efficiency"] = "memory_efficient"

        # Analyze CPU usage
        cpu_percent = operation_metrics.get("cpu_percent", 0)
        if cpu_percent > 90:
            analysis["bottlenecks"].append("cpu_saturated")
            analysis["optimization_opportunities"].append("reduce_concurrency")
        elif cpu_percent < 20:
            analysis["resource_efficiency"] = "cpu_efficient"

        # Analyze throughput
        throughput = operation_metrics.get("items_per_second", 0)
        if throughput > 100:
            analysis["scalability_concerns"].append("high_throughput_achieved")
        elif throughput < 1:
            analysis["bottlenecks"].append("low_throughput")
            analysis["optimization_opportunities"].append("increase_batch_size")

        return analysis

    def _analyze_workload(self, items: list[Any]) -> dict[str, Any]:
        """Analyze workload characteristics."""
        analysis = {
            "item_count": len(items),
            "estimated_complexity": "unknown",
            "memory_requirements": "unknown",
            "parallelization_potential": "unknown",
        }

        if len(items) > 1000:
            analysis["estimated_complexity"] = "high_volume"
            analysis["parallelization_potential"] = "high"
        elif len(items) > 100:
            analysis["estimated_complexity"] = "medium_volume"
            analysis["parallelization_potential"] = "medium"
        else:
            analysis["estimated_complexity"] = "low_volume"
            analysis["parallelization_potential"] = "low"

        return analysis

    def _adapt_profile_for_workload(
        self, profile: PerformanceProfile, workload_analysis: dict[str, Any]
    ) -> PerformanceProfile:
        """Adapt performance profile based on workload analysis."""
        adapted = profile

        # Adjust concurrency based on workload
        item_count = workload_analysis.get("item_count", 0)
        if item_count > 1000 and profile.resource_limits.max_concurrent_operations < 10:
            adapted.resource_limits.max_concurrent_operations = min(
                20, item_count // 50
            )
        elif item_count < 50 and profile.resource_limits.max_concurrent_operations > 5:
            adapted.resource_limits.max_concurrent_operations = max(1, item_count // 10)

        # Adjust batch size based on workload
        if item_count > 1000 and profile.batch_size < 100:
            adapted.batch_size = min(500, item_count // 10)

        return adapted

    def _execute_with_optimization(
        self,
        operation_func: Callable,
        operation_name: str,
        items: list[Any],
        profile: PerformanceProfile,
        **operation_kwargs,
    ) -> Any:
        """Execute operation with optimization applied."""
        # Use thread pool for CPU-bound operations
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=profile.resource_limits.max_concurrent_operations
        ) as executor:
            # Create optimized batches
            batches = self._create_optimized_batches(items, profile.batch_size)

            # Execute batches with monitoring
            return monitor_pipeline_operation(
                operation_name,
                self._execute_batches,
                operation_func,
                batches,
                executor,
                profile,
                **operation_kwargs,
            )

    async def _execute_async_with_optimization(
        self,
        operation_func: Callable,
        operation_name: str,
        items: list[Any],
        profile: PerformanceProfile,
        **operation_kwargs,
    ) -> Any:
        """Execute async operation with optimization applied."""
        # Create optimized batches
        batches = self._create_optimized_batches(items, profile.batch_size)

        # Execute with resource management
        async with self.optimized_resource_context(operation_name, profile.strategy):
            # Process batches concurrently
            semaphore = asyncio.Semaphore(
                profile.resource_limits.max_concurrent_operations
            )

            async def process_batch(batch: list[Any]) -> list[Any]:
                async with semaphore:
                    return await operation_func(batch, **operation_kwargs)

            # Execute all batches
            tasks = [process_batch(batch) for batch in batches]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Flatten results
            results = []
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch processing failed: {result}")
                    continue
                results.extend(result)

            return results

    def _execute_batches(
        self,
        operation_func: Callable,
        batches: list[list[Any]],
        executor: concurrent.futures.Executor,
        profile: PerformanceProfile,
        **operation_kwargs,
    ) -> list[Any]:
        """Execute batches using thread pool."""
        futures = []

        # Submit all batches
        for batch in batches:
            future = executor.submit(operation_func, batch, **operation_kwargs)
            futures.append(future)

        # Collect results
        results = []
        for future in concurrent.futures.as_completed(futures):
            try:
                batch_result = future.result(
                    timeout=profile.resource_limits.operation_timeout_seconds
                )
                results.extend(batch_result)
            except Exception as e:
                logger.error(f"Batch execution failed: {e}")

        return results

    def _create_optimized_batches(
        self, items: list[Any], batch_size: int
    ) -> list[list[Any]]:
        """Create optimized batches for processing."""
        if batch_size <= 0:
            return [items]

        batches = []
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            batches.append(batch)

        return batches

    async def _acquire_resources(self, operation_id: str, limits: ResourceLimits):
        """Acquire resources for operation."""
        try:
            await asyncio.wait_for(
                self.resource_semaphore.acquire(),
                timeout=limits.semaphore_timeout_seconds,
            )
            logger.debug(f"Acquired resources for operation {operation_id}")
        except TimeoutError:
            raise RuntimeError(
                f"Timeout acquiring resources for operation {operation_id}"
            )

    async def _release_resources(self, operation_id: str):
        """Release resources for operation."""
        self.resource_semaphore.release()
        logger.debug(f"Released resources for operation {operation_id}")

    def get_optimization_statistics(self) -> dict[str, Any]:
        """Get optimization statistics."""
        total_operations = self.stats["operations_optimized"]
        avg_improvement = (
            sum(self.stats["performance_improvements"])
            / len(self.stats["performance_improvements"])
            if self.stats["performance_improvements"]
            else 0
        )
        avg_savings = (
            sum(self.stats["resource_savings"]) / len(self.stats["resource_savings"])
            if self.stats["resource_savings"]
            else 0
        )

        return {
            **self.stats,
            "average_performance_improvement_percent": round(avg_improvement, 1),
            "average_resource_savings_percent": round(avg_savings, 1),
            "optimization_success_rate_percent": (
                (total_operations - self.stats["optimization_failures"])
                / max(total_operations, 1)
                * 100
            ),
        }


# Convenience functions for common optimization scenarios
def optimize_pipeline_operation(
    operation_func: Callable,
    items: list[Any],
    strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
    **kwargs,
) -> Any:
    """
    Convenience function to optimize a pipeline operation.

    Args:
        operation_func: Operation function to optimize
        items: Items to process
        strategy: Optimization strategy to use
        **kwargs: Additional arguments for operation

    Returns:
        Optimized operation result
    """
    optimizer = PipelineOptimizer(strategy)
    return optimizer.optimize_operation(
        operation_func, "optimized_operation", items, **kwargs
    )


async def optimize_async_pipeline_operation(
    operation_func: Callable,
    items: list[Any],
    strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
    **kwargs,
) -> Any:
    """
    Convenience function to optimize an async pipeline operation.

    Args:
        operation_func: Async operation function to optimize
        items: Items to process
        strategy: Optimization strategy to use
        **kwargs: Additional arguments for operation

    Returns:
        Optimized operation result
    """
    optimizer = PipelineOptimizer(strategy)
    return await optimizer.optimize_async_operation(
        operation_func, "optimized_async_operation", items, **kwargs
    )


def get_pipeline_optimizer(
    strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
) -> PipelineOptimizer:
    """Get a configured pipeline optimizer instance."""
    return PipelineOptimizer(strategy)

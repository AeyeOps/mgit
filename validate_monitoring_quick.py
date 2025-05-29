#!/usr/bin/env python3
"""
Quick Monitoring System Validation

This script performs a rapid validation of mgit monitoring capabilities.
Suitable for CI/CD pipelines and deployment verification.
"""

import asyncio
import sys
import time
from pathlib import Path

# Import mgit monitoring components
sys.path.insert(0, str(Path(__file__).parent / "mgit"))

def test_imports():
    """Test if all monitoring components can be imported."""
    try:
        from mgit.monitoring import (
            setup_monitoring_integration,
            get_metrics_collector,
            get_structured_logger,
            get_health_checker,
            correlation_context,
            monitor_mgit_operation
        )
        return True, "All monitoring components imported successfully"
    except ImportError as e:
        return False, f"Import failed: {e}"

def test_initialization():
    """Test monitoring system initialization."""
    try:
        from mgit.monitoring import setup_monitoring_integration
        setup_monitoring_integration()
        return True, "Monitoring system initialized successfully"
    except Exception as e:
        return False, f"Initialization failed: {e}"

def test_metrics():
    """Test basic metrics functionality."""
    try:
        from mgit.monitoring import get_metrics_collector
        metrics = get_metrics_collector()
        
        # Test basic metric operations
        metrics.inc_counter("test_counter", 1.0, {"test": "quick"})
        metrics.set_gauge("test_gauge", 100.0)
        metrics.record_operation("test_op", True, 1.0, "test")
        
        # Test export
        prometheus_output = metrics.export_prometheus()
        json_output = metrics.export_json()
        
        # Verify content
        assert "test_counter" in prometheus_output
        assert len(json_output) > 100
        
        return True, "Metrics collection and export working"
    except Exception as e:
        return False, f"Metrics test failed: {e}"

def test_logging():
    """Test structured logging functionality."""
    try:
        from mgit.monitoring import get_structured_logger, correlation_context
        logger = get_structured_logger("quick_test")
        
        # Test basic logging
        logger.info("Quick test message", test_field="value")
        
        # Test correlation context
        with correlation_context(operation="quick_test"):
            logger.info("Correlation test message")
        
        return True, "Structured logging working"
    except Exception as e:
        return False, f"Logging test failed: {e}"

async def test_health_checks():
    """Test health check functionality."""
    try:
        from mgit.monitoring import get_health_checker
        health_checker = get_health_checker()
        
        # Test basic health checks
        system_health = await health_checker.run_check("system_basics")
        git_health = await health_checker.run_check("git_availability")
        
        # Test probes
        is_ready = await health_checker.is_ready()
        is_alive = await health_checker.is_alive()
        
        # Verify results
        assert system_health.status in ["healthy", "unhealthy", "unknown"]
        assert git_health.status in ["healthy", "unhealthy", "unknown"]
        assert isinstance(is_ready, bool)
        assert isinstance(is_alive, bool)
        
        return True, f"Health checks working (ready: {is_ready}, alive: {is_alive})"
    except Exception as e:
        return False, f"Health check test failed: {e}"

def test_integration():
    """Test monitoring integration decorators."""
    try:
        from mgit.monitoring import monitor_mgit_operation
        
        @monitor_mgit_operation(operation_name="quick_test", provider="test")
        def test_operation():
            time.sleep(0.01)
            return "success"
        
        result = test_operation()
        assert result == "success"
        
        return True, "Integration decorators working"
    except Exception as e:
        return False, f"Integration test failed: {e}"

async def run_quick_validation():
    """Run all quick validation tests."""
    print("🔍 mgit Monitoring Quick Validation")
    print("=" * 40)
    
    tests = [
        ("Imports", test_imports),
        ("Initialization", test_initialization),
        ("Metrics", test_metrics),
        ("Logging", test_logging),
        ("Health Checks", test_health_checks),
        ("Integration", test_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📊 Testing {test_name}...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                success, message = await test_func()
            else:
                success, message = test_func()
            
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {message}")
            results.append(success)
            
        except Exception as e:
            print(f"❌ {test_name}: Exception - {str(e)}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total) * 100
    
    print(f"\n🎯 Quick Validation Complete")
    print("=" * 40)
    print(f"Tests Passed: {passed}/{total} ({success_rate:.1f}%)")
    
    if passed == total:
        print("✅ All monitoring components operational")
        return True
    else:
        print("❌ Some monitoring components failed validation")
        return False

async def main():
    """Main function."""
    try:
        success = await run_quick_validation()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted")
        return 130
    except Exception as e:
        print(f"\n💥 Validation failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
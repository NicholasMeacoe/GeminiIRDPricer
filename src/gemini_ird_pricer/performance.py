"""Performance monitoring and optimization utilities."""
from __future__ import annotations
import time
import logging
import functools
from typing import Any, Callable, Dict, Optional
from contextlib import contextmanager


logger = logging.getLogger(__name__)


def performance_monitor(operation_name: str, log_threshold_ms: float = 100.0):
    """Decorator to monitor function performance."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                if duration_ms > log_threshold_ms:
                    logger.warning(
                        f"slow_operation",
                        extra={
                            "operation": operation_name,
                            "duration_ms": round(duration_ms, 2),
                            "function": func.__name__,
                            "threshold_ms": log_threshold_ms,
                        }
                    )
                else:
                    logger.debug(
                        f"operation_completed",
                        extra={
                            "operation": operation_name,
                            "duration_ms": round(duration_ms, 2),
                            "function": func.__name__,
                        }
                    )
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"operation_failed",
                    extra={
                        "operation": operation_name,
                        "duration_ms": round(duration_ms, 2),
                        "function": func.__name__,
                        "error": str(e),
                    }
                )
                raise
        return wrapper
    return decorator


@contextmanager
def timer(operation_name: str):
    """Context manager for timing operations."""
    start_time = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"timed_operation",
            extra={
                "operation": operation_name,
                "duration_ms": round(duration_ms, 2),
            }
        )


class PerformanceTracker:
    """Track performance metrics across requests."""
    
    def __init__(self):
        self.metrics: Dict[str, list] = {}
    
    def record(self, operation: str, duration_ms: float) -> None:
        """Record a performance metric."""
        if operation not in self.metrics:
            self.metrics[operation] = []
        
        self.metrics[operation].append(duration_ms)
        
        # Keep only last 1000 measurements
        if len(self.metrics[operation]) > 1000:
            self.metrics[operation] = self.metrics[operation][-1000:]
    
    def get_stats(self, operation: str) -> Optional[Dict[str, float]]:
        """Get statistics for an operation."""
        if operation not in self.metrics or not self.metrics[operation]:
            return None
        
        values = self.metrics[operation]
        return {
            "count": len(values),
            "avg_ms": sum(values) / len(values),
            "min_ms": min(values),
            "max_ms": max(values),
            "p95_ms": sorted(values)[int(len(values) * 0.95)] if len(values) > 20 else max(values),
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all operations."""
        return {op: self.get_stats(op) for op in self.metrics if self.get_stats(op)}


# Global performance tracker instance
performance_tracker = PerformanceTracker()

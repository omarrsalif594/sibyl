"""
Lightweight observability utilities for Sibyl techniques.

Exports structured logging and resource monitoring helpers that can be used
directly by techniques without pulling in the heavier platform observability
stack.
"""

from typing import Any

from .logging import StructuredLogger
from .resources import MetricsCollector, ResourceMonitor, ResourceSnapshot


def execute_with_observability(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Execute a function with observability (stub implementation).

    Args:
        func: Function to execute
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result of func execution
    """
    return func(*args, **kwargs)


async def execute_with_observability_async(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Execute an async function with observability (stub implementation).

    Args:
        func: Async function to execute
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result of func execution
    """
    return await func(*args, **kwargs)


__all__ = [
    "MetricsCollector",
    "ResourceMonitor",
    "ResourceSnapshot",
    "StructuredLogger",
    "execute_with_observability",
    "execute_with_observability_async",
]

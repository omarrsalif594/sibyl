"""
Internal module for async/sync execution bridging and event loop handling.

This module is not part of the public API - do not import directly.
Use sibyl.framework.tools.tool_base instead.
"""

import asyncio
import concurrent.futures
import inspect
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def run_coroutine_sync(coro: Awaitable[T]) -> T:
    """
    Run a coroutine synchronously, handling both running and non-running event loops.

    Args:
        coro: Coroutine to execute

    Returns:
        Result of the coroutine

    Raises:
        Exception: Any exception raised by the coroutine
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create new thread with new event loop
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            # Run in current loop
            return loop.run_until_complete(coro)
    except Exception as e:
        logger.exception("Failed to run coroutine synchronously: %s", e)
        raise


async def run_callable_async(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Run a callable (sync or async) as an async operation.

    If the callable is already async, await it directly.
    If it's sync, run it in a thread pool to avoid blocking.

    Args:
        func: Function to execute (sync or async)
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result of the function
    """
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    # Run sync function in thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


async def safe_await_if_needed(result: Any) -> Any:
    """
    Await a result if it's a coroutine, otherwise return as-is.

    Args:
        result: Value that may or may not be a coroutine

    Returns:
        Awaited result if coroutine, original value otherwise
    """
    if inspect.iscoroutine(result):
        return await result
    return result


def measure_execution_time(start_time: datetime) -> float:
    """
    Calculate execution time in milliseconds from start time.

    Args:
        start_time: Start time of execution

    Returns:
        Execution time in milliseconds
    """
    return (datetime.now() - start_time).total_seconds() * 1000

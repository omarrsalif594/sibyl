"""Hook decorator for automatic hook execution.

This module provides the @with_hooks decorator that automatically
executes registered hooks around function calls.

Example:
    from sibyl.mcp_server.infrastructure.hooks import with_hooks

    @with_hooks("compile_model")
    async def compile_model(model_name: str) -> dict:
        # ... implementation ...
        return result

    # Hooks will automatically execute:
    # 1. before hooks (with context)
    # 2. compile_model function
    # 3. after hooks (with result) OR on_error hooks (if exception)
"""

import functools
import logging
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from sibyl.core.protocols.infrastructure.hooks import HookContext
from sibyl.techniques.infrastructure.hooks.registry import get_hook_registry

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def with_hooks(
    operation_name: str | None = None,
    session_id_param: str | None = None,
    metadata_params: list[str] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to execute hooks around a function.

    This decorator:
    1. Creates a HookContext from function arguments
    2. Executes before hooks in priority order
    3. Calls the wrapped function
    4. Executes after hooks (on success) or on_error hooks (on failure)
    5. Returns the result

    Args:
        operation_name: Name for the operation (defaults to function name)
        session_id_param: Name of parameter containing session_id
        metadata_params: List of parameter names to include in metadata

    Returns:
        Decorated function

    Example:
        @with_hooks("compile_model", session_id_param="session_id")
        async def compile_model(model_name: str, session_id: str = None) -> dict:
            return {"sql": "SELECT 1"}
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        # Use function name if operation_name not provided
        op_name = operation_name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            registry = get_hook_registry()

            # Build HookContext
            context = _build_context(op_name, args, kwargs, session_id_param, metadata_params, func)

            try:
                # Execute before hooks
                context = await registry.execute_before(context)

                # Execute the wrapped function
                result = await func(*args, **kwargs)

                # Execute after hooks
                return await registry.execute_after(context, result)

            except Exception as e:
                # Execute on_error hooks
                error = await registry.execute_on_error(context, e)

                # Re-raise the error (unless suppressed by a hook)
                if error is not None:
                    raise error from e

                # Error was suppressed - return None
                # (This should be very rare and used with caution)
                return None

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # For synchronous functions, just call them directly
            # (Hooks require async, so we skip hook execution for sync functions)
            logger.warning(
                f"Synchronous function {func.__name__} decorated with @with_hooks. "
                "Hooks will be skipped. Use async functions for hook support."
            )
            return func(*args, **kwargs)

        # Return appropriate wrapper based on whether function is async
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _build_context(
    operation_name: str,
    args: tuple,
    kwargs: dict[str, Any],
    session_id_param: str | None,
    metadata_params: list[str] | None,
    func: Callable,
) -> HookContext:
    """Build HookContext from function call.

    Args:
        operation_name: Name of the operation
        args: Positional arguments
        kwargs: Keyword arguments
        session_id_param: Parameter name for session_id
        metadata_params: Parameter names to include in metadata
        func: The wrapped function

    Returns:
        HookContext instance
    """
    # Extract session_id if specified
    session_id = None
    if session_id_param and session_id_param in kwargs:
        session_id = kwargs[session_id_param]

    # Extract metadata from specified parameters
    metadata = {}
    if metadata_params:
        # Get function signature to map args to param names
        import inspect

        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())

        # Map positional args to param names
        for i, arg_value in enumerate(args):
            if i < len(param_names):
                param_name = param_names[i]
                if param_name in metadata_params:
                    metadata[param_name] = arg_value

        # Add specified kwargs to metadata
        for param_name in metadata_params:
            if param_name in kwargs:
                metadata[param_name] = kwargs[param_name]

    return HookContext(
        operation_name=operation_name,
        args=args,
        kwargs=kwargs,
        metadata=metadata,
        session_id=session_id,
    )


def with_hooks_and_session(
    operation_name: str | None = None,
    metadata_params: list[str] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator combining @with_hooks and @with_session_tracking.

    This is a convenience decorator that:
    1. Tracks the operation in session
    2. Executes hooks around the operation

    Args:
        operation_name: Name for the operation (defaults to function name)
        metadata_params: List of parameter names to include in metadata

    Returns:
        Decorated function

    Example:
        @with_hooks_and_session("compile_model", metadata_params=["model_name"])
        async def compile_model(model_name: str, session_id: str) -> dict:
            return {"sql": "SELECT 1"}

    Note:
        This decorator assumes @with_session_tracking decorator exists.
        The session_id is automatically extracted from session tracking.
    """
    # Try to import session tracking decorator
    try:
        from sibyl.mcp_server.infrastructure.session.decorator import (
            with_session_tracking,
        )

        def decorator(func: Callable[P, R]) -> Callable[P, R]:
            # Apply session tracking first (inner), then hooks (outer)
            func_with_session = with_session_tracking(func)
            return with_hooks(
                operation_name=operation_name,
                session_id_param="session_id",
                metadata_params=metadata_params,
            )(func_with_session)

        return decorator

    except ImportError:
        logger.warning(
            "@with_hooks_and_session decorator requires session tracking module. "
            "Falling back to @with_hooks only."
        )
        # Fall back to just @with_hooks
        return with_hooks(operation_name=operation_name, metadata_params=metadata_params)

"""Hook protocol for extensibility system.

This module defines the protocol for creating hooks that can intercept
operations before, after, or on error. Hooks enable extensibility without
modifying core business logic.

Protocol-based hook system for operation interception and extension.

Key features:
- Protocol-based design (dependency inversion)
- Before/after/on_error lifecycle
- Context propagation
- Async support
- Priority-based execution order

Example:
    from sibyl.core.protocols.infrastructure.hooks import ToolHook
    from sibyl.core.contracts.hooks import HookContext

    class LoggingHook(ToolHook):
        async def before(self, context: HookContext) -> HookContext:
            logger.info(f"Starting {context.operation_name}")
            return context

        async def after(self, context: HookContext, result: Any) -> Any:
            logger.info(f"Finished {context.operation_name}")
            return result

Note:
    HookContext and HookResult have been moved to sibyl.core.contracts.hooks.
    This module now contains only the protocol definition (interface).
"""

import logging
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    # Import for type checking only to avoid circular imports
    from sibyl.core.contracts.hooks import HookContext
else:
    # At runtime, use forward reference
    HookContext = "HookContext"

logger = logging.getLogger(__name__)


@runtime_checkable
class ToolHook(Protocol):
    """Protocol for operation hooks.

    Hooks can intercept operations at three points:
    - before: Before operation execution
    - after: After successful execution
    - on_error: When operation raises an exception

    Hooks should be stateless or thread-safe.
    """

    name: str
    priority: int = 0  # Higher priority hooks execute first
    enabled: bool = True

    async def before(self, context: "HookContext") -> "HookContext":
        """Called before operation execution.

        Can modify context or perform side effects (logging, metrics, etc.).

        Args:
            context: Operation context

        Returns:
            Modified or original context

        Raises:
            Exception: If hook fails critically (stops operation)
        """
        return context

    async def after(self, context: "HookContext", result: Any) -> Any:
        """Called after successful operation execution.

        Can modify result or perform side effects.

        Args:
            context: Operation context
            result: Operation result

        Returns:
            Modified or original result

        Raises:
            Exception: If hook fails critically
        """
        return result

    async def on_error(self, context: "HookContext", error: Exception) -> Exception | None:
        """Called when operation raises an exception.

        Can handle error, log it, or transform it.

        Args:
            context: Operation context
            error: Exception that was raised

        Returns:
            - Original exception (to re-raise)
            - Modified exception (to raise instead)
            - None (to suppress exception - use with caution!)
        """
        return error


__all__ = ["HookContext", "ToolHook"]

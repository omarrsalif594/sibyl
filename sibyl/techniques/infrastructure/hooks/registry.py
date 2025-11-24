"""Hook registry for managing and executing hooks.

This module provides a centralized registry for hooks, allowing:
- Registration of hooks by name
- Priority-based execution order
- Enable/disable hooks dynamically
- Hook execution with error handling
- Observability and metrics

Example:
    from sibyl.mcp_server.infrastructure.hooks import (
        HookRegistry,
        HookContext,
        get_hook_registry,
    )

    # Get global registry
    registry = get_hook_registry()

    # Register hooks
    registry.register(MetricsHook())
    registry.register(CacheHook())

    # Execute hooks
    context = HookContext(operation_name="compile_model")
    context = await registry.execute_before(context)
    # ... do operation ...
    result = await registry.execute_after(context, result)
"""

import logging
import time
from typing import Any

from sibyl.core.contracts.hooks import HookContext, HookResult
from sibyl.core.protocols.infrastructure.hooks import ToolHook

logger = logging.getLogger(__name__)


class HookRegistry:
    """Registry for managing operation hooks.

    Provides centralized hook management with:
    - Registration by name
    - Priority-based execution order
    - Dynamic enable/disable
    - Error handling and observability
    """

    def __init__(self) -> None:
        """Initialize empty hook registry."""
        self._hooks: dict[str, ToolHook] = {}
        self._hook_results: list[HookResult] = []

    def register(self, hook: ToolHook, replace: bool = False) -> None:
        """Register a hook.

        Args:
            hook: Hook instance to register
            replace: If True, replace existing hook with same name

        Raises:
            ValueError: If hook with same name exists and replace=False
        """
        if hook.name in self._hooks and not replace:
            msg = f"Hook '{hook.name}' already registered. Use replace=True to replace."
            raise ValueError(msg)

        self._hooks[hook.name] = hook
        logger.info(
            "Registered hook: %s (priority=%s, enabled=%s)", hook.name, hook.priority, hook.enabled
        )

    def unregister(self, hook_name: str) -> bool:
        """Unregister a hook by name.

        Args:
            hook_name: Name of hook to remove

        Returns:
            True if hook was removed, False if not found
        """
        if hook_name in self._hooks:
            del self._hooks[hook_name]
            logger.info("Unregistered hook: %s", hook_name)
            return True
        return False

    def get_hook(self, hook_name: str) -> ToolHook | None:
        """Get a hook by name.

        Args:
            hook_name: Name of hook to retrieve

        Returns:
            Hook instance or None if not found
        """
        return self._hooks.get(hook_name)

    def list_hooks(self) -> list[tuple[str, int, bool]]:
        """List all registered hooks.

        Returns:
            List of (name, priority, enabled) tuples, sorted by priority descending
        """
        hooks_info = [(name, hook.priority, hook.enabled) for name, hook in self._hooks.items()]
        # Sort by priority (highest first)
        return sorted(hooks_info, key=lambda x: x[1], reverse=True)

    def enable_hook(self, hook_name: str) -> None:
        """Enable a hook.

        Args:
            hook_name: Name of hook to enable
        """
        if hook_name in self._hooks:
            self._hooks[hook_name].enabled = True
            logger.info("Enabled hook: %s", hook_name)

    def disable_hook(self, hook_name: str) -> None:
        """Disable a hook.

        Args:
            hook_name: Name of hook to disable
        """
        if hook_name in self._hooks:
            self._hooks[hook_name].enabled = False
            logger.info("Disabled hook: %s", hook_name)

    def clear_results(self) -> None:
        """Clear hook execution results."""
        self._hook_results.clear()

    def get_results(self) -> list[HookResult]:
        """Get hook execution results.

        Returns:
            List of HookResult objects from recent executions
        """
        return self._hook_results.copy()

    async def execute_before(self, context: HookContext) -> HookContext:
        """Execute all before hooks in priority order.

        Args:
            context: Operation context

        Returns:
            Modified context (possibly transformed by hooks)

        Note:
            If a hook fails, the error is logged but execution continues
            with remaining hooks. Hook failures don't stop the operation.
        """
        sorted_hooks = self._get_enabled_hooks_sorted()

        for hook in sorted_hooks:
            start_time = time.time()
            try:
                context = await hook.before(context)
                duration_ms = (time.time() - start_time) * 1000

                result = HookResult(
                    hook_name=hook.name,
                    phase="before",
                    success=True,
                    duration_ms=duration_ms,
                )
                self._hook_results.append(result)

                logger.debug("Hook %s.before() completed in %sms", hook.name, duration_ms)
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                result = HookResult(
                    hook_name=hook.name,
                    phase="before",
                    success=False,
                    error=e,
                    duration_ms=duration_ms,
                )
                self._hook_results.append(result)

                logger.error(
                    f"Hook {hook.name}.before() failed: {e}",
                    exc_info=True,
                )

        return context

    async def execute_after(self, context: HookContext, result: Any) -> Any:
        """Execute all after hooks in priority order.

        Args:
            context: Operation context
            result: Operation result

        Returns:
            Modified result (possibly transformed by hooks)

        Note:
            If a hook fails, the error is logged but execution continues
            with remaining hooks. The original result is preserved.
        """
        sorted_hooks = self._get_enabled_hooks_sorted()

        for hook in sorted_hooks:
            start_time = time.time()
            try:
                result = await hook.after(context, result)
                duration_ms = (time.time() - start_time) * 1000

                hook_result = HookResult(
                    hook_name=hook.name,
                    phase="after",
                    success=True,
                    duration_ms=duration_ms,
                )
                self._hook_results.append(hook_result)

                logger.debug("Hook %s.after() completed in %sms", hook.name, duration_ms)
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                hook_result = HookResult(
                    hook_name=hook.name,
                    phase="after",
                    success=False,
                    error=e,
                    duration_ms=duration_ms,
                )
                self._hook_results.append(hook_result)

                logger.error(
                    f"Hook {hook.name}.after() failed: {e}",
                    exc_info=True,
                )

        return result

    async def execute_on_error(self, context: HookContext, error: Exception) -> Exception:
        """Execute all on_error hooks in priority order.

        Args:
            context: Operation context
            error: Exception that was raised

        Returns:
            Exception to re-raise (possibly modified by hooks)

        Note:
            Hooks can suppress errors by returning None, but this should
            be used with extreme caution. Most hooks should return the
            original or a modified exception.
        """
        sorted_hooks = self._get_enabled_hooks_sorted()
        current_error = error

        for hook in sorted_hooks:
            start_time = time.time()
            try:
                result_error = await hook.on_error(context, current_error)
                duration_ms = (time.time() - start_time) * 1000

                # Hook can suppress error by returning None
                if result_error is None:
                    logger.warning(
                        "Hook %s.on_error() suppressed exception: %s", hook.name, current_error
                    )
                    # Clear the error
                    current_error = None
                else:
                    current_error = result_error

                hook_result = HookResult(
                    hook_name=hook.name,
                    phase="on_error",
                    success=True,
                    duration_ms=duration_ms,
                )
                self._hook_results.append(hook_result)

                logger.debug("Hook %s.on_error() completed in %sms", hook.name, duration_ms)
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                hook_result = HookResult(
                    hook_name=hook.name,
                    phase="on_error",
                    success=False,
                    error=e,
                    duration_ms=duration_ms,
                )
                self._hook_results.append(hook_result)

                logger.error(
                    f"Hook {hook.name}.on_error() failed: {e}",
                    exc_info=True,
                )

        return current_error

    def _get_enabled_hooks_sorted(self) -> list[ToolHook]:
        """Get enabled hooks sorted by priority (highest first).

        Returns:
            List of enabled hooks in execution order
        """
        enabled_hooks = [hook for hook in self._hooks.values() if hook.enabled]
        return sorted(enabled_hooks, key=lambda h: h.priority, reverse=True)


# Global hook registry instance
_global_registry: HookRegistry | None = None


def get_hook_registry() -> HookRegistry:
    """Get the global hook registry instance.

    Returns:
        Global HookRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = HookRegistry()
    return _global_registry


def reset_hook_registry() -> None:
    """Reset the global hook registry.

    Useful for testing to start with a clean state.
    """
    global _global_registry
    _global_registry = HookRegistry()

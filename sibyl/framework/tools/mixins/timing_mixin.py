"""
TimingMixin - Automatic execution timing for tools.

Adds execution_time_ms to output automatically.
"""

import time
from typing import Any


class TimingMixin:
    """
    Mixin that adds automatic timing to tool execution.

    Usage:
        class MyTool(TimingMixin, SimpleTool):
            def _execute_impl(self, ctx, input_data):
                # Your logic here (no timing boilerplate needed)
                return {"result": "data"}

    The mixin will:
    - Measure execution time
    - Add 'execution_time_ms' to output
    - Call _execute_impl() for actual logic
    """

    def execute(self, ctx: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute with automatic timing.

        Subclasses should implement _execute_impl() instead of execute().
        """
        start = time.time()

        # Call implementation
        result = self._execute_impl(ctx, input_data)

        # Add timing
        duration_ms = (time.time() - start) * 1000

        # Ensure result is a dict
        if not isinstance(result, dict):
            msg = f"Tool {self.__class__.__name__} returned non-dict: {type(result)}"
            raise TypeError(msg)

        result["execution_time_ms"] = duration_ms
        return result

    def _execute_impl(self, ctx: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Implement tool logic here (without timing boilerplate).

        Subclasses must override this method.
        """
        msg = f"{self.__class__.__name__} must implement _execute_impl()"
        raise NotImplementedError(msg)

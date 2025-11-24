"""
LoggingMixin - Automatic logging for tool execution.

Logs tool start/finish with correlation IDs.
"""

import logging
from typing import Any


class LoggingMixin:
    """
    Mixin that adds automatic logging to tool execution.

    Usage:
        class MyTool(LoggingMixin, ErrorHandlingMixin, TimingMixin, SimpleTool):
            def _execute_impl(self, ctx, input_data):
                # Execution start/finish logged automatically
                return {"result": "data"}

    The mixin will:
    - Log tool start with correlation_id
    - Log tool finish with execution time
    - Log input/output if debug enabled
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self, ctx: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute with automatic logging.

        Calls super().execute() and adds logging.
        """
        correlation_id = getattr(ctx, "correlation_id", "unknown")
        tool_name = (
            getattr(self, "metadata", self.__class__).name
            if hasattr(getattr(self, "metadata", None), "name")
            else self.__class__.__name__
        )

        # Log start
        self.logger.info("Tool '%s' starting (correlation_id=%s)", tool_name, correlation_id)
        self.logger.debug("Input: %s", input_data)

        # Execute
        result = super().execute(ctx, input_data)

        # Log finish
        execution_time = result.get("execution_time_ms", "?")
        self.logger.info("Tool '%s' completed in %sms", tool_name, execution_time)
        self.logger.debug("Output: %s", result)

        return result

"""
ErrorHandlingMixin - Consistent error handling for tools.

Wraps execution in try/catch and converts exceptions to proper error responses.
"""

import logging
from typing import Any

from sibyl.framework.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from sibyl.framework.errors import (
    TimeoutError as ToolTimeoutError,
)

logger = logging.getLogger(__name__)


class ErrorHandlingMixin:
    """
    Mixin that adds consistent error handling to tool execution.

    Usage:
        class MyTool(ErrorHandlingMixin, TimingMixin, SimpleTool):
            def _execute_impl(self, ctx, input_data):
                # Your logic - errors are caught automatically
                return {"result": "data"}

    The mixin will:
    - Catch all exceptions
    - Convert to appropriate error types
    - Log errors
    - Return error dict (never raises)
    """

    def execute(self, ctx: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute with automatic error handling.

        Calls super().execute() and wraps in try/catch.
        """
        try:
            # Call next in MRO chain (usually TimingMixin or _execute_impl)
            return super().execute(ctx, input_data)

        except (ValidationError, NotFoundError, ToolTimeoutError, ConflictError) as e:
            # Known tool errors - log and return error dict
            logger.warning("Tool error in %s: %s", self.__class__.__name__, e)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

        except Exception as e:
            # Unexpected error - log with traceback and return internal error
            logger.exception("Unexpected error in %s: %s", self.__class__.__name__, e)
            return {
                "success": False,
                "error": f"Internal error: {e!s}",
                "error_type": "InternalError",
            }

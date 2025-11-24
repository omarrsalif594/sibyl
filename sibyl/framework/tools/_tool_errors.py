"""
Internal module for tool error handling and result creation.

This module is not part of the public API - do not import directly.
Use sibyl.framework.tools.tool_base instead.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def create_error_result(
    error: Exception,
    tool_name: str,
    execution_time_ms: float | None = None,
    additional_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a standardized error result dictionary.

    Args:
        error: Exception that occurred
        tool_name: Name of the tool that failed
        execution_time_ms: Optional execution time in milliseconds
        additional_metadata: Additional metadata to include

    Returns:
        Dictionary with error result structure
    """
    metadata = {"error_type": type(error).__name__}
    if additional_metadata:
        metadata.update(additional_metadata)

    result = {
        "success": False,
        "error": str(error),
        "tool_name": tool_name,
        "metadata": metadata,
    }

    if execution_time_ms is not None:
        result["execution_time_ms"] = execution_time_ms

    return result


def log_execution_start(tool_name: str) -> None:
    """
    Log the start of tool execution.

    Args:
        tool_name: Name of the tool being executed
    """
    logger.info("Executing tool (async): %s", tool_name)


def log_execution_complete(tool_name: str, execution_time_ms: float) -> None:
    """
    Log successful completion of tool execution.

    Args:
        tool_name: Name of the tool
        execution_time_ms: Execution time in milliseconds
    """
    logger.info("Tool '%s' completed in %sms", tool_name, execution_time_ms)


def log_execution_error(tool_name: str, error: Exception) -> None:
    """
    Log tool execution error.

    Args:
        tool_name: Name of the tool that failed
        error: Exception that occurred
    """
    logger.exception("Tool '%s' failed: %s", tool_name, error)


def log_validation_failure(tool_name: str, error_msg: str) -> None:
    """
    Log input validation failure.

    Args:
        tool_name: Name of the tool
        error_msg: Validation error message
    """
    logger.warning("Tool '%s' input validation failed: %s", tool_name, error_msg)

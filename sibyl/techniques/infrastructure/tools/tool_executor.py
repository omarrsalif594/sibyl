"""
Tool executor with runtime validation and timeout enforcement.

This module provides a wrapper around tool execution that:
1. Validates input against tool's input_schema
2. Enforces max_execution_time_ms timeout
3. Validates output against tool's output_schema
4. Maps exceptions to standardized error taxonomy
5. Tracks execution metadata (time, cache hits, etc.)
"""

import asyncio
import logging
import time
from typing import Any

try:
    from jsonschema import ValidationError as JSONSchemaValidationError
    from jsonschema import validate
except ImportError:
    msg = "jsonschema is required for tool execution. Install with: pip install jsonschema"
    raise ImportError(msg) from None

from sibyl.framework.errors import (
    InternalError,
    MCPError,
    ToolInputError,
    ToolOutputError,
    ToolTimeoutError,
)

from .tool_interface import Tool, ToolContext, ToolExecutionResult

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Executes tools with validation, timeouts, and error handling.
    """

    def __init__(self, enable_validation: bool = True, enable_timeouts: bool = True) -> None:
        """
        Initialize tool executor.

        Args:
            enable_validation: Enable schema validation (default: True)
            enable_timeouts: Enable timeout enforcement (default: True)
        """
        self.enable_validation = enable_validation
        self.enable_timeouts = enable_timeouts

    async def execute_async(
        self, tool: Tool, ctx: ToolContext, input_data: dict[str, Any]
    ) -> ToolExecutionResult:
        """
        Execute tool asynchronously with validation and timeout.

        Args:
            tool: Tool instance to execute
            ctx: ToolContext with dependencies
            input_data: Input data dict

        Returns:
            ToolExecutionResult with output or error
        """
        start_time = time.time()
        metadata = tool.metadata

        logger.info(
            f"Executing tool: {metadata.name}@{metadata.version} "
            f"(correlation_id={ctx.correlation_id})"
        )

        try:
            # Step 1: Validate input
            if self.enable_validation:
                self._validate_input(tool, input_data)

            # Step 2: Execute with timeout
            if self.enable_timeouts:
                timeout_s = max(1, metadata.max_execution_time_ms / 1000.0)
                output = await asyncio.wait_for(
                    self._execute_tool(tool, ctx, input_data), timeout=timeout_s
                )
            else:
                output = await self._execute_tool(tool, ctx, input_data)

            # Step 3: Validate output
            if self.enable_validation:
                self._validate_output(tool, output)

            # Success
            execution_time_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Tool success: {metadata.name}@{metadata.version} "
                f"(time={execution_time_ms:.2f}ms, correlation_id={ctx.correlation_id})"
            )

            return ToolExecutionResult(
                tool_name=metadata.name,
                tool_version=metadata.version,
                correlation_id=ctx.correlation_id,
                success=True,
                output=output,
                execution_time_ms=execution_time_ms,
            )

        except TimeoutError:
            # Timeout exceeded
            execution_time_ms = (time.time() - start_time) * 1000
            error = ToolTimeoutError(metadata.name, metadata.max_execution_time_ms)

            logger.warning(
                f"Tool timeout: {metadata.name}@{metadata.version} "
                f"(time={execution_time_ms:.2f}ms, max={metadata.max_execution_time_ms}ms, "
                f"correlation_id={ctx.correlation_id})"
            )

            return ToolExecutionResult(
                tool_name=metadata.name,
                tool_version=metadata.version,
                correlation_id=ctx.correlation_id,
                success=False,
                error=error.to_dict(),
                execution_time_ms=execution_time_ms,
            )

        except MCPError as e:
            # Known error type
            execution_time_ms = (time.time() - start_time) * 1000

            logger.warning(
                f"Tool error: {metadata.name}@{metadata.version} "
                f"(error={e.code}, time={execution_time_ms:.2f}ms, "
                f"correlation_id={ctx.correlation_id})",
                exc_info=True,
            )

            return ToolExecutionResult(
                tool_name=metadata.name,
                tool_version=metadata.version,
                correlation_id=ctx.correlation_id,
                success=False,
                error=e.to_dict(),
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            # Unexpected error
            execution_time_ms = (time.time() - start_time) * 1000
            internal_error = InternalError(f"Tool execution failed: {e!s}", cause=e)

            logger.error(
                f"Tool internal error: {metadata.name}@{metadata.version} "
                f"(time={execution_time_ms:.2f}ms, correlation_id={ctx.correlation_id})",
                exc_info=True,
            )

            return ToolExecutionResult(
                tool_name=metadata.name,
                tool_version=metadata.version,
                correlation_id=ctx.correlation_id,
                success=False,
                error=internal_error.to_dict(),
                execution_time_ms=execution_time_ms,
            )

    def execute(
        self, tool: Tool, ctx: ToolContext, input_data: dict[str, Any]
    ) -> ToolExecutionResult:
        """
        Execute tool synchronously (blocking).

        Args:
            tool: Tool instance to execute
            ctx: ToolContext with dependencies
            input_data: Input data dict

        Returns:
            ToolExecutionResult with output or error
        """
        # Run in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.execute_async(tool, ctx, input_data))

    async def _execute_tool(
        self, tool: Tool, ctx: ToolContext, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute tool (handles both sync and async tools)."""
        result = tool.execute(ctx, input_data)

        # Handle async tools
        if asyncio.iscoroutine(result):
            result = await result

        return result

    def _validate_input(self, tool: Tool, input_data: dict[str, Any]) -> None:
        """
        Validate input data against tool's input schema.

        Args:
            tool: Tool instance
            input_data: Input data to validate

        Raises:
            ToolInputError: If validation fails
        """
        try:
            validate(instance=input_data, schema=tool.metadata.input_schema)
        except JSONSchemaValidationError as e:
            path = list(e.path) if e.path else None
            msg = f"Invalid input: {e.message}"
            raise ToolInputError(
                msg,
                tool_name=tool.metadata.name,
                path=path,
            ) from e

    def _validate_output(self, tool: Tool, output: dict[str, Any]) -> None:
        """
        Validate output data against tool's output schema.

        Args:
            tool: Tool instance
            output: Output data to validate

        Raises:
            ToolOutputError: If validation fails
        """
        try:
            validate(instance=output, schema=tool.metadata.output_schema)
        except JSONSchemaValidationError as e:
            path = list(e.path) if e.path else None
            msg = f"Invalid output: {e.message}"
            raise ToolOutputError(
                msg,
                tool_name=tool.metadata.name,
                path=path,
            ) from e


# Convenience functions

_default_executor = ToolExecutor()


async def run_tool_async(
    tool: Tool, ctx: ToolContext, input_data: dict[str, Any]
) -> ToolExecutionResult:
    """Run tool asynchronously with default executor."""
    return await _default_executor.execute_async(tool, ctx, input_data)


def run_tool(tool: Tool, ctx: ToolContext, input_data: dict[str, Any]) -> ToolExecutionResult:
    """Run tool synchronously with default executor."""
    return _default_executor.execute(tool, ctx, input_data)

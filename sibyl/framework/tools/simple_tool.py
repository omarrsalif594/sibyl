"""
SimpleTool - Minimal base class for tools.

Provides bare minimum structure for tools without any extras.
Use this when you want full control and minimal overhead.
"""

from abc import ABC
from dataclasses import dataclass
from typing import Any

from .tool_interface import ToolContext, ToolMetadata


@dataclass
class SimpleTool(ABC):
    """
    Minimal tool base class.

    Provides:
    - Tool Protocol compliance
    - Abstract execute() method
    - metadata class attribute support

    Does NOT provide:
    - Automatic timing
    - Error handling
    - Logging
    - Validation

    Usage:
        @dataclass
        class MySimpleTool(SimpleTool):
            metadata = ToolMetadata(
                name="my_tool",
                version="1.0.0",
                category="custom",
                description="Does something simple",
                input_schema={...},
                output_schema={...},
                max_execution_time_ms=5000,
            )

            def execute(self, ctx: ToolContext, input_data: dict[str, Any]) -> dict[str, Any]:
                # Your logic here - add your own timing, error handling, etc.
                import time
                start = time.time()

                result = {"output": "data"}

                duration_ms = (time.time() - start) * 1000
                result["execution_time_ms"] = duration_ms
                return result
    """

    # Subclasses should override this class attribute
    metadata: ToolMetadata

    def execute(self, ctx: ToolContext, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute tool with given context and input.

        Subclasses must implement this method.

        Args:
            ctx: ToolContext with dependencies and correlation_id
            input_data: Input dict (already validated against input_schema)

        Returns:
            Output dict (will be validated against output_schema)

        Raises:
            Any exceptions from your implementation
        """
        msg = f"{self.__class__.__name__} must implement execute() method"
        raise NotImplementedError(msg)

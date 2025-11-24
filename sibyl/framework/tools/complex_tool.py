"""
ComplexTool - Feature-rich base class with all mixins.

Provides automatic timing, error handling, and logging.
Use this for production tools that need robust features.
"""

from abc import ABC
from dataclasses import dataclass

from .mixins import ErrorHandlingMixin, LoggingMixin, TimingMixin
from .simple_tool import SimpleTool


@dataclass
class ComplexTool(LoggingMixin, ErrorHandlingMixin, TimingMixin, SimpleTool, ABC):
    """
    Feature-rich tool base class with all mixins.

    Provides:
    - Tool Protocol compliance
    - Automatic timing (via TimingMixin)
    - Consistent error handling (via ErrorHandlingMixin)
    - Automatic logging (via LoggingMixin)
    - Clean separation of concerns

    Does NOT provide:
    - Caching (add CachingMixin if needed)
    - Rate limiting (add RateLimitMixin if needed)
    - Custom validation (add ValidationMixin if needed)

    Usage:
        @dataclass
        class MyComplexTool(ComplexTool):
            metadata = ToolMetadata(
                name="my_tool",
                version="1.0.0",
                category="custom",
                description="Does something complex",
                input_schema={...},
                output_schema={...},
                max_execution_time_ms=5000,
            )

            def _execute_impl(self, ctx: ToolContext, input_data: dict[str, Any]) -> dict[str, Any]:
                # Your logic here - NO boilerplate needed!
                # Timing, error handling, and logging are automatic

                # Just return your result dict
                return {
                    "output": "data",
                    "count": 42,
                }
                # execution_time_ms is added automatically
                # Errors are caught and logged automatically
                # Execution is logged automatically

    MRO (Method Resolution Order):
        ComplexTool → LoggingMixin → ErrorHandlingMixin → TimingMixin → SimpleTool

    Execution flow:
        1. LoggingMixin.execute() - Logs start
        2. ErrorHandlingMixin.execute() - Wraps in try/catch
        3. TimingMixin.execute() - Adds timing
        4. YourTool._execute_impl() - Your logic
        5. TimingMixin.execute() - Adds execution_time_ms
        6. ErrorHandlingMixin.execute() - Catches any errors
        7. LoggingMixin.execute() - Logs finish
    """

    def __init__(self) -> None:
        """Initialize with logging."""
        LoggingMixin.__init__(self)

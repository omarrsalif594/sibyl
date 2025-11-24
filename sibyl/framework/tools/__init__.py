"""
Tool system - protocols, registry, and execution framework.
"""

from .complex_tool import ComplexTool

# Mixins
from .mixins import (
    ErrorHandlingMixin,
    LoggingMixin,
    TimingMixin,
    ValidationMixin,
)

# Base classes
from .simple_tool import SimpleTool

# Unified base classes - Compatible with domain/platform
from .tool_base import (
    ComposableTool,
    SibylTool,
    ToolExecutionError,
    ToolMetadata,
    ToolResult,
)
from .tool_executor import (
    ToolExecutor,
    run_tool,
    run_tool_async,
)
from .tool_interface import (
    Tool,
    ToolContext,
    ToolExecutionResult,
    ToolInputSchema,
    ToolOutputSchema,
)
from .tool_interface import ToolMetadata as FrameworkToolMetadata
from .tool_registry import (
    ToolRegistry,
    parse_semver,
)

__all__ = [
    "ComplexTool",
    "ComposableTool",
    "ErrorHandlingMixin",
    "FrameworkToolMetadata",
    "LoggingMixin",
    # Unified base classes
    "SibylTool",
    # Base classes
    "SimpleTool",
    # Mixins
    "TimingMixin",
    # Interface (Protocol-based)
    "Tool",
    "ToolContext",
    "ToolExecutionError",
    "ToolExecutionResult",
    # Executor
    "ToolExecutor",
    "ToolInputSchema",
    "ToolMetadata",
    "ToolOutputSchema",
    # Registry
    "ToolRegistry",
    "ToolResult",
    "ValidationMixin",
    "parse_semver",
    "run_tool",
    "run_tool_async",
]

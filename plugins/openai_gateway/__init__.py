"""
OpenAI Gateway Plugin

Exposes Sibyl pipelines as OpenAI-style tools for integration with
OpenAI SDK, ChatGPT, and other OpenAI-compatible frontends.
"""

from plugins.openai_gateway.openai_sibyl_tools import (
    OpenAISibylAdapter,
    ToolExecutionError,
    ToolMappingError,
    export_tool_definitions,
    handle_tool_call,
)

__all__ = [
    "OpenAISibylAdapter",
    "ToolExecutionError",
    "ToolMappingError",
    "export_tool_definitions",
    "handle_tool_call",
]

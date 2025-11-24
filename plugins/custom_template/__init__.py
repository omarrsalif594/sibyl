"""
Custom Plugin Template

Template for creating custom Sibyl frontend plugins.
Provides event-based integration with flexible configuration.
"""

from plugins.custom_template.custom_plugin_template import (
    CustomPlugin,
    PluginConfigError,
    PluginEvent,
    PluginExecutionError,
    PluginResponse,
    example_validation_handler,
)

__all__ = [
    "CustomPlugin",
    "PluginConfigError",
    "PluginEvent",
    "PluginExecutionError",
    "PluginResponse",
    "example_validation_handler",
]

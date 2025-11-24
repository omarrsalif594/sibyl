"""
Opencode Integration Adapter.

This module provides integration between Opencode commands and Sibyl pipelines,
enabling users to define custom Opencode commands that trigger Sibyl workflows.
"""

from plugins.opencode.opencode_sibyl_adapter import (
    OpencodeAdapter,
    execute_command,
    load_command_mapping,
    resolve_command,
)

__all__ = ["OpencodeAdapter", "execute_command", "load_command_mapping", "resolve_command"]

"""
Agents shop: high-level agent primitives.

This module provides convenient access to the core agent framework,
including agent base classes, factories, and tool catalogs.
"""

from sibyl.agents.base.agent import Agent
from sibyl.agents.factory.agent_factory import AgentFactory
from sibyl.agents.tools.catalog import get_tool_catalog

# ToolCatalog class doesn't exist yet, use the function instead
ToolCatalog = get_tool_catalog

__all__ = ["Agent", "AgentFactory", "ToolCatalog"]

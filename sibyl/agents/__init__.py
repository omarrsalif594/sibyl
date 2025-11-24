"""
Sibyl Core Agents - protocol-first agent framework.

The agents package now follows the modular patterns used across the platform,
keeping a slim public API while allowing extensions through protocols and
tool catalogs.

Quickstart:
    from sibyl.agents import AgentFactory, get_tool_catalog

    factory = AgentFactory(profile="default")
    planner = factory.create_planner()
    plan = await planner.execute({"goal": "Assess stock levels"})

Public API:
- AgentFactory / build_agents: construct agents with injected services
- get_tool_catalog / get_core_tools: discover available tools for a profile

See MIGRATION.md for import changes and DEVELOPER_GUIDE.md for extension tips.
"""

from sibyl.agents.factory import AgentFactory, build_agents
from sibyl.agents.tools import get_core_tools, get_tool_catalog

__all__ = ["AgentFactory", "build_agents", "get_core_tools", "get_tool_catalog"]

# Version is managed centrally in sibyl.__init__.py
# Do not hardcode version here

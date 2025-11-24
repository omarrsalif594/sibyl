"""Factory helpers for assembling agent suites.

Exports:
- AgentFactory: configurable builder for planner/executor/reviewer/search agents
- build_agents: convenience wrapper to create all core agents
- extend_tool_catalog: helper to inject additional tools into a factory instance

Usage:
    from sibyl.agents.factory import AgentFactory

    factory = AgentFactory(profile="default", llm_client=llm)
    agents = factory.create_all_agents()
"""

from sibyl.agents.factory.agent_factory import (
    AgentFactory,
    build_agents,
    extend_tool_catalog,
)

__all__ = ["AgentFactory", "build_agents", "extend_tool_catalog"]

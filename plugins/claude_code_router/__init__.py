"""
Claude Code Router Plugin.

A config-driven routing facade inspired by claude-code-router that provides
interfaces and rule-based routing without automatic policy decisions.

This plugin is purely config-driven:
- No LLM calls to decide routes
- No automatic local vs remote selection
- No dynamic policy decisions
- Simply matches rules and returns route decisions

Key components:
- router_types: Type definitions for routing
- router_config.yaml: Example configuration with rules
- router_engine: Pure rule-matching engine

Extension points:
- Add new route targets (local_specialist, remote_llm, etc.)
- Extend rule matching logic (context-based, metadata-based)
- Integrate with actual LLM providers and specialists
"""

from plugins.claude_code_router.router_engine import load_router_config, route
from plugins.claude_code_router.router_types import (
    RouteDecision,
    RouterConfig,
    RouteRequest,
)

__all__ = [
    "RouteDecision",
    "RouteRequest",
    "RouterConfig",
    "load_router_config",
    "route",
]

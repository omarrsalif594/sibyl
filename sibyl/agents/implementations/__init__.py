"""Concrete agent implementations built on the base protocol.

Exports:
- PlannerAgent, ExecutorAgent, ReviewAgent, SearchAgent

Usage:
    from sibyl.agents.implementations import PlannerAgent
"""

from typing import Any

from sibyl.agents.implementations.executor import ExecutorAgent
from sibyl.agents.implementations.planner import PlannerAgent
from sibyl.agents.implementations.search import SearchAgent


# Lazy import of ReviewAgent to avoid circular dependency
def __getattr__(name: str) -> Any:
    """Lazy import to avoid circular dependency."""
    if name == "ReviewAgent":
        from sibyl.agents.implementations.reviewer import ReviewAgent

        return ReviewAgent
    msg = f"module '{__name__}' has no attribute '{name}'"
    raise AttributeError(msg)


__all__ = [
    "ExecutorAgent",
    "PlannerAgent",
    "ReviewAgent",
    "SearchAgent",
]

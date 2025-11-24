"""Agent protocols and interfaces for type safety and extensibility."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from sibyl.agents.types import AgentId, AgentRequestLike, AgentResponseLike


@runtime_checkable
class Agent(Protocol):
    """Core agent protocol defining the agent interface."""

    agent_id: AgentId

    async def execute(self, request: AgentRequestLike) -> AgentResponseLike: ...


@runtime_checkable
class ToolAwareAgent(Agent, Protocol):
    """Protocol for agents that rely on a shared tool catalog."""

    tool_catalog: dict[str, Any]


__all__ = ["Agent", "ToolAwareAgent"]

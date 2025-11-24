"""Shared types for agent operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from collections.abc import Mapping

AgentId = str
AgentRequestPayload = dict[str, Any]
AgentResponsePayload = dict[str, Any]
AgentRequestLike = Union["AgentRequest", AgentRequestPayload]
AgentResponseLike = Union["AgentResponse", AgentResponsePayload]


@dataclass
class AgentRequest:
    """Standardized agent request wrapper."""

    payload: AgentRequestPayload
    context: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> AgentRequest:
        """
        Build a request from a mapping while extracting common fields.

        This keeps existing dict-style payloads compatible while making the
        context and metadata explicit for protocol implementers.
        """
        payload = dict(data)
        context = payload.pop("context", None) if "context" in payload else None
        metadata = payload.pop("metadata", None) if "metadata" in payload else None
        return cls(payload=payload, context=context, metadata=metadata)


@dataclass
class AgentResponse:
    """Standardized agent response wrapper."""

    result: AgentResponsePayload
    status: str = "success"
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> AgentResponsePayload:
        """Flatten the response for callers that expect a dictionary."""
        response: AgentResponsePayload = {"status": self.status, **self.result}
        if self.errors:
            response["errors"] = self.errors
        return response


__all__ = [
    "AgentId",
    "AgentRequest",
    "AgentRequestLike",
    "AgentRequestPayload",
    "AgentResponse",
    "AgentResponseLike",
    "AgentResponsePayload",
]

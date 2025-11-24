"""Hook context and result types with runtime logic.

This module provides concrete dataclasses for hook execution context and results.
These are runtime implementations separate from the protocol definitions.

The protocol definitions (ToolHook) remain in sibyl.core.protocols.infrastructure.hooks.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class HookContext(BaseModel):
    """Context passed to hooks during operation execution.

    Attributes:
        operation_name: Name of the operation being hooked
        operation_id: Unique ID for this operation invocation
        args: Positional arguments passed to operation
        kwargs: Keyword arguments passed to operation
        metadata: Additional metadata for hooks to use
        start_time: When the operation started
        session_id: Optional session ID for tracking
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    operation_name: str = Field(..., description="Name of the operation being hooked")
    operation_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique operation ID"
    )
    args: tuple[Any, ...] = Field(default_factory=tuple, description="Positional arguments")
    kwargs: dict[str, Any] = Field(default_factory=dict, description="Keyword arguments")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    start_time: datetime = Field(
        default_factory=datetime.utcnow, description="Operation start time"
    )
    session_id: str | None = Field(default=None, description="Optional session ID")

    def with_metadata(self, **new_metadata: Any) -> "HookContext":
        """Create new context with additional metadata.

        Args:
            **new_metadata: Metadata key-value pairs to add

        Returns:
            New HookContext with merged metadata
        """
        merged_metadata = {**self.metadata, **new_metadata}
        return HookContext(
            operation_name=self.operation_name,
            operation_id=self.operation_id,
            args=self.args,
            kwargs=self.kwargs,
            metadata=merged_metadata,
            start_time=self.start_time,
            session_id=self.session_id,
        )


@dataclass
class HookResult:
    """Result of hook execution.

    Tracks success/failure of individual hooks for observability.

    Attributes:
        hook_name: Name of the hook
        phase: Execution phase (before/after/on_error)
        success: Whether hook executed successfully
        error: Error if hook failed
        duration_ms: Execution duration in milliseconds
    """

    hook_name: str
    phase: str
    success: bool
    error: Exception | None = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/metrics."""
        return {
            "hook_name": self.hook_name,
            "phase": self.phase,
            "success": self.success,
            "error": str(self.error) if self.error else None,
            "duration_ms": self.duration_ms,
        }


__all__ = ["HookContext", "HookResult"]

"""Session Handle artifacts for managing stateful MCP sessions with checkpoints.

This module provides typed artifacts for tracking and managing stateful sessions
across MCP tools, with support for:
- Session lifecycle management (start, pause, resume, end)
- State checkpointing and restoration
- Multi-turn conversation tracking
- Long-running workflow state

It implements GAP-STATE-002 (Session State Persistence) and GAP-STATE-003
(Stateful MCP Tracking).

Example:
    from sibyl.core.artifacts.session_handle import SessionHandle

    # Create session for multi-turn conversation
    session = SessionHandle(
        session_id="conv_12345",
        provider="deep_code_reasoning",
        state={"analysis_depth": 3, "context": {...}}
    )

    # Create checkpoint before risky operation
    checkpoint_id = session.checkpoint("before_deep_analysis")

    # If something goes wrong, restore from checkpoint
    session.restore(checkpoint_id)
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Status of a session.

    These statuses track the lifecycle of a stateful MCP session.
    """

    ACTIVE = "active"  # Session is currently active
    PAUSED = "paused"  # Session is paused, can be resumed
    COMPLETED = "completed"  # Session has completed successfully
    FAILED = "failed"  # Session encountered an error
    CANCELLED = "cancelled"  # Session was explicitly cancelled


@dataclass
class Checkpoint:
    """A state checkpoint for session restoration.

    Attributes:
        id: Unique checkpoint identifier
        name: Human-readable checkpoint name
        state: Snapshot of session state at checkpoint time
        created_at: Timestamp when checkpoint was created
        metadata: Additional checkpoint metadata
    """

    id: str
    name: str
    state: dict[str, Any]
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            state=data["state"],
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SessionHandle:
    """Artifact for tracking stateful MCP sessions with checkpoint support.

    This handle represents a stateful session across one or more MCP tool calls,
    such as:
    - Multi-turn conversations (Deep Code Reasoning)
    - Long-running workflow executions (Conductor)
    - Iterative analysis pipelines
    - Distributed computation jobs

    Design Principles:
    - Explicit: All operations require passing MCPToolAdapter
    - Serializable: Can be JSON-serialized for persistence/resumption
    - Checkpoint-capable: Supports creating and restoring state snapshots
    - Provider-agnostic: Works with any stateful MCP

    Attributes:
        session_id: Unique session identifier
        provider: MCP provider name
        session_type: Type of session (conversation, workflow, analysis, etc.)
        state: Current session state dictionary
        checkpoints: List of state checkpoints for restoration
        status: Current session status
        created_at: Timestamp when session was created
        updated_at: Timestamp of last state update
        completed_at: Optional timestamp when session completed
        metadata: Additional session metadata

    Example:
        # Create session
        session = SessionHandle(
            session_id="sess_abc123",
            provider="deep_code_reasoning",
            session_type="conversation",
            state={"messages": [], "analysis_context": {...}}
        )

        # Update state as session progresses
        session.update_state({"messages": [...]})

        # Create checkpoint
        cp_id = session.checkpoint("after_initial_analysis")

        # Continue session...

        # Restore from checkpoint if needed
        session.restore(cp_id)
    """

    # Core identifiers
    session_id: str
    provider: str
    session_type: str = "generic"

    # State management
    state: dict[str, Any] = field(default_factory=dict)
    checkpoints: list[Checkpoint] = field(default_factory=list)
    status: SessionStatus = SessionStatus.ACTIVE

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    # Additional context
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate handle after initialization."""
        if not self.session_id:
            msg = "session_id must be specified"
            raise ValueError(msg)
        if not self.provider:
            msg = "provider must be specified"
            raise ValueError(msg)

    def update_state(self, updates: dict[str, Any]) -> None:
        """Update session state with new values.

        Args:
            updates: Dictionary of state updates to merge

        Example:
            session.update_state({"message_count": 5, "last_message": "..."})
        """
        self.state.update(updates)
        self.updated_at = datetime.now()

        logger.debug(
            f"Updated state for session {self.session_id}: {len(updates)} field(s) updated"
        )

    def checkpoint(self, name: str, metadata: dict[str, Any] | None = None) -> str:
        """Create a state checkpoint for potential restoration.

        Args:
            name: Human-readable checkpoint name
            metadata: Optional additional checkpoint metadata

        Returns:
            Checkpoint ID

        Example:
            # Before risky operation
            cp_id = session.checkpoint("before_expensive_analysis")

            try:
                # Perform risky operation
                result = await expensive_operation()
                session.update_state({"result": result})
            except Exception:
                # Restore to checkpoint
                session.restore(cp_id)
        """
        checkpoint_id = str(uuid.uuid4())

        # Create deep copy of current state
        import copy

        state_snapshot = copy.deepcopy(self.state)

        checkpoint = Checkpoint(
            id=checkpoint_id,
            name=name,
            state=state_snapshot,
            created_at=datetime.now(),
            metadata=metadata or {},
        )

        self.checkpoints.append(checkpoint)

        logger.info(
            f"Created checkpoint '{name}' (id={checkpoint_id}) for session {self.session_id}"
        )

        return checkpoint_id

    def restore(self, checkpoint_id: str) -> None:
        """Restore session state from a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to restore

        Raises:
            ValueError: If checkpoint ID not found

        Example:
            session.restore(checkpoint_id)
        """
        # Find checkpoint
        checkpoint = None
        for cp in self.checkpoints:
            if cp.id == checkpoint_id:
                checkpoint = cp
                break

        if not checkpoint:
            msg = f"Checkpoint {checkpoint_id} not found in session {self.session_id}"
            raise ValueError(msg)

        # Restore state
        import copy

        self.state = copy.deepcopy(checkpoint.state)
        self.updated_at = datetime.now()

        logger.info(
            f"Restored session {self.session_id} from checkpoint "
            f"'{checkpoint.name}' (id={checkpoint_id})"
        )

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List all checkpoints for this session.

        Returns:
            List of checkpoint info dictionaries

        Example:
            checkpoints = session.list_checkpoints()
            for cp in checkpoints:
                print(f"{cp['name']}: {cp['created_at']}")
        """
        return [
            {
                "id": cp.id,
                "name": cp.name,
                "created_at": cp.created_at.isoformat(),
                "metadata": cp.metadata,
            }
            for cp in self.checkpoints
        ]

    def mark_completed(self) -> None:
        """Mark session as completed."""
        self.status = SessionStatus.COMPLETED
        self.completed_at = datetime.now()
        logger.info("Session %s marked as completed", self.session_id)

    def mark_failed(self, error_message: str | None = None) -> None:
        """Mark session as failed.

        Args:
            error_message: Optional error message to include in metadata
        """
        self.status = SessionStatus.FAILED
        self.completed_at = datetime.now()

        if error_message:
            self.metadata["error"] = error_message

        logger.error("Session %s marked as failed: %s", self.session_id, error_message)

    def mark_cancelled(self) -> None:
        """Mark session as cancelled."""
        self.status = SessionStatus.CANCELLED
        self.completed_at = datetime.now()
        logger.info("Session %s marked as cancelled", self.session_id)

    def pause(self) -> None:
        """Pause session (can be resumed later)."""
        if self.status != SessionStatus.ACTIVE:
            msg = f"Cannot pause session in status {self.status.value}, must be ACTIVE"
            raise ValueError(msg)

        self.status = SessionStatus.PAUSED
        logger.info("Session %s paused", self.session_id)

    def resume(self) -> None:
        """Resume paused session."""
        if self.status != SessionStatus.PAUSED:
            msg = f"Cannot resume session in status {self.status.value}, must be PAUSED"
            raise ValueError(msg)

        self.status = SessionStatus.ACTIVE
        self.updated_at = datetime.now()
        logger.info("Session %s resumed", self.session_id)

    @classmethod
    def from_mcp_response(
        cls,
        response: dict[str, Any],
        provider: str,
        session_type: str = "generic",
        session_id_key: str = "session_id",
        **kwargs,
    ) -> "SessionHandle":
        """Factory method to create handle from MCP tool response.

        Args:
            response: MCP tool response containing session ID
            provider: MCP provider name
            session_type: Type of session
            session_id_key: Key name for session ID in response
            **kwargs: Additional SessionHandle parameters

        Returns:
            New SessionHandle instance

        Raises:
            ValueError: If response doesn't contain session ID

        Example:
            response = {"session_id": "sess_123", "status": "started"}
            session = SessionHandle.from_mcp_response(
                response,
                provider="deep_code_reasoning",
                session_type="conversation"
            )
        """
        session_id = response.get(session_id_key)
        if not session_id:
            # Try common alternative keys
            for alt_key in ["id", "conversation_id", "workflow_id"]:
                session_id = response.get(alt_key)
                if session_id:
                    break

        if not session_id:
            msg = (
                f"MCP response does not contain session ID (tried keys: "
                f"{session_id_key}, id, conversation_id, workflow_id): {response}"
            )
            raise ValueError(msg)

        # Extract state from response
        state = {k: v for k, v in response.items() if k not in [session_id_key, "status"]}

        # Parse status if present
        status_str = response.get("status", "active").lower()
        status_map = {
            "active": SessionStatus.ACTIVE,
            "started": SessionStatus.ACTIVE,
            "running": SessionStatus.ACTIVE,
            "paused": SessionStatus.PAUSED,
            "suspended": SessionStatus.PAUSED,
            "completed": SessionStatus.COMPLETED,
            "finished": SessionStatus.COMPLETED,
            "failed": SessionStatus.FAILED,
            "error": SessionStatus.FAILED,
            "cancelled": SessionStatus.CANCELLED,
            "canceled": SessionStatus.CANCELLED,
        }
        status = status_map.get(status_str, SessionStatus.ACTIVE)

        return cls(
            session_id=session_id,
            provider=provider,
            session_type=session_type,
            state=state,
            status=status,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence.

        Returns:
            Dictionary representation (JSON-serializable)
        """
        return {
            "session_id": self.session_id,
            "provider": self.provider,
            "session_type": self.session_type,
            "state": self.state,
            "checkpoints": [cp.to_dict() for cp in self.checkpoints],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionHandle":
        """Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            SessionHandle instance
        """
        # Parse timestamps
        created_at = datetime.fromisoformat(data["created_at"])
        updated_at = datetime.fromisoformat(data["updated_at"])
        completed_at = (
            datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        )

        # Parse status
        status = SessionStatus(data["status"])

        # Parse checkpoints
        checkpoints = [Checkpoint.from_dict(cp) for cp in data.get("checkpoints", [])]

        return cls(
            session_id=data["session_id"],
            provider=data["provider"],
            session_type=data.get("session_type", "generic"),
            state=data.get("state", {}),
            checkpoints=checkpoints,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            metadata=data.get("metadata", {}),
        )


# Custom exceptions
class SessionError(Exception):
    """Base exception for session-related errors."""


class SessionNotFoundError(SessionError):
    """Raised when session cannot be found."""


class CheckpointNotFoundError(SessionError):
    """Raised when checkpoint cannot be found."""


class SessionStateError(SessionError):
    """Raised when session is in invalid state for operation."""

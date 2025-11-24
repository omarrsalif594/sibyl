"""Checkpoint protocol for resumable operations.

This module defines protocols and data structures for:
- Saving operation state at checkpoints
- Resuming from last checkpoint after failure
- Managing checkpoint lifecycle

Enables checkpointing and resumption for long-running operations.

Key concepts:
- Checkpoint: Snapshot of operation state at a specific point
- CheckpointStore: Persistence layer for checkpoints
- Resumable operation: Operation that can save/restore state

Example:
    from sibyl.mcp_server.infrastructure.checkpointing import (
        OperationCheckpoint,
        CheckpointStore,
    )

    # Save checkpoint
    checkpoint = OperationCheckpoint(
        operation_id="compile-batch-123",
        operation_name="batch_compile",
        checkpoint_id="wave_1_complete",
        state={"completed_models": ["resource_stage_users", "resource_stage_orders"]},
        metadata={"wave": 1, "total_waves": 3},
    )
    store.save_checkpoint(checkpoint)

    # Resume from checkpoint
    last_checkpoint = store.load_latest_checkpoint("compile-batch-123")
    if last_checkpoint:
        completed = last_checkpoint.state["completed_models"]
        # Resume from where we left off
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class OperationCheckpoint:
    """Checkpoint representing operation state at a specific point.

    Attributes:
        operation_id: Unique ID for the operation (shared across retries)
        operation_name: Name of the operation
        checkpoint_id: Unique ID for this checkpoint
        state: Operation state data (must be JSON-serializable)
        metadata: Additional metadata (progress, timestamps, etc.)
        created_at: When checkpoint was created
        sequence_number: Sequential checkpoint number (1, 2, 3, ...)
    """

    operation_id: str
    operation_name: str
    checkpoint_id: str
    state: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    sequence_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert checkpoint to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "operation_id": self.operation_id,
            "operation_name": self.operation_name,
            "checkpoint_id": self.checkpoint_id,
            "state": self.state,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "sequence_number": self.sequence_number,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OperationCheckpoint":
        """Create checkpoint from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            OperationCheckpoint instance
        """
        return cls(
            operation_id=data["operation_id"],
            operation_name=data["operation_name"],
            checkpoint_id=data["checkpoint_id"],
            state=data["state"],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.utcnow()),
            sequence_number=data.get("sequence_number", 0),
        )


@runtime_checkable
class CheckpointStore(Protocol):
    """Protocol for checkpoint persistence layer.

    Implementations can use:
    - JSON files
    - SQLite database
    - Redis
    - PostgreSQL
    - etc.
    """

    def save_checkpoint(self, checkpoint: OperationCheckpoint) -> None:
        """Save a checkpoint.

        Args:
            checkpoint: Checkpoint to save
        """
        ...

    def load_checkpoint(self, operation_id: str, checkpoint_id: str) -> OperationCheckpoint | None:
        """Load a specific checkpoint.

        Args:
            operation_id: Operation ID
            checkpoint_id: Checkpoint ID

        Returns:
            Checkpoint or None if not found
        """
        ...

    def load_latest_checkpoint(self, operation_id: str) -> OperationCheckpoint | None:
        """Load the most recent checkpoint for an operation.

        Args:
            operation_id: Operation ID

        Returns:
            Latest checkpoint or None if not found
        """
        ...

    def list_checkpoints(self, operation_id: str) -> list[OperationCheckpoint]:
        """List all checkpoints for an operation.

        Args:
            operation_id: Operation ID

        Returns:
            List of checkpoints ordered by sequence_number
        """
        ...

    def delete_checkpoint(self, operation_id: str, checkpoint_id: str) -> bool:
        """Delete a specific checkpoint.

        Args:
            operation_id: Operation ID
            checkpoint_id: Checkpoint ID

        Returns:
            True if deleted, False if not found
        """
        ...

    def delete_all_checkpoints(self, operation_id: str) -> int:
        """Delete all checkpoints for an operation.

        Args:
            operation_id: Operation ID

        Returns:
            Number of checkpoints deleted
        """
        ...

    def cleanup_old_checkpoints(self, max_age_days: int = 7) -> int:
        """Clean up checkpoints older than max_age_days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of checkpoints deleted
        """
        ...


@dataclass
class ResumableOperationState:
    """State for resumable operation execution.

    Tracks:
    - Current checkpoint
    - Completed items
    - Pending items
    - Errors
    - Progress

    Attributes:
        operation_id: Unique operation ID
        operation_name: Operation name
        completed_items: List of completed item names
        pending_items: List of remaining items to process
        failed_items: List of failed items with errors
        current_checkpoint: Current checkpoint ID
        progress: Progress percentage (0.0-1.0)
        started_at: When operation started
        last_checkpoint_at: When last checkpoint was saved
    """

    operation_id: str
    operation_name: str
    completed_items: list[str] = field(default_factory=list)
    pending_items: list[str] = field(default_factory=list)
    failed_items: list[dict[str, Any]] = field(default_factory=list)
    current_checkpoint: str | None = None
    progress: float = 0.0
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_checkpoint_at: datetime | None = None

    def to_checkpoint(self, checkpoint_id: str | None = None) -> OperationCheckpoint:
        """Convert state to checkpoint.

        Args:
            checkpoint_id: Optional checkpoint ID (auto-generated if None)

        Returns:
            OperationCheckpoint instance
        """
        if checkpoint_id is None:
            checkpoint_id = f"checkpoint_{len(self.completed_items)}"

        return OperationCheckpoint(
            operation_id=self.operation_id,
            operation_name=self.operation_name,
            checkpoint_id=checkpoint_id,
            state={
                "completed_items": self.completed_items,
                "pending_items": self.pending_items,
                "failed_items": self.failed_items,
                "current_checkpoint": self.current_checkpoint,
                "progress": self.progress,
            },
            metadata={
                "started_at": self.started_at.isoformat(),
                "last_checkpoint_at": self.last_checkpoint_at.isoformat()
                if self.last_checkpoint_at
                else None,
                "completed_count": len(self.completed_items),
                "pending_count": len(self.pending_items),
                "failed_count": len(self.failed_items),
            },
            sequence_number=len(self.completed_items),
        )

    @classmethod
    def from_checkpoint(cls, checkpoint: OperationCheckpoint) -> "ResumableOperationState":
        """Create state from checkpoint.

        Args:
            checkpoint: Checkpoint to restore from

        Returns:
            ResumableOperationState instance
        """
        return cls(
            operation_id=checkpoint.operation_id,
            operation_name=checkpoint.operation_name,
            completed_items=checkpoint.state.get("completed_items", []),
            pending_items=checkpoint.state.get("pending_items", []),
            failed_items=checkpoint.state.get("failed_items", []),
            current_checkpoint=checkpoint.checkpoint_id,
            progress=checkpoint.state.get("progress", 0.0),
            started_at=datetime.fromisoformat(checkpoint.metadata.get("started_at"))
            if checkpoint.metadata.get("started_at")
            else datetime.utcnow(),
            last_checkpoint_at=checkpoint.created_at,
        )

    def mark_completed(self, item: str) -> None:
        """Mark an item as completed.

        Args:
            item: Item name
        """
        if item in self.pending_items:
            self.pending_items.remove(item)
        if item not in self.completed_items:
            self.completed_items.append(item)

        self._update_progress()

    def mark_failed(self, item: str, error: str | Exception) -> None:
        """Mark an item as failed.

        Args:
            item: Item name
            error: Error message or exception
        """
        if item in self.pending_items:
            self.pending_items.remove(item)

        self.failed_items.append(
            {
                "item": item,
                "error": str(error),
                "failed_at": datetime.utcnow().isoformat(),
            }
        )

        self._update_progress()

    def _update_progress(self) -> None:
        """Update progress percentage."""
        total = len(self.completed_items) + len(self.pending_items) + len(self.failed_items)
        if total > 0:
            self.progress = len(self.completed_items) / total

    def should_checkpoint(self, checkpoint_interval: int = 10) -> bool:
        """Check if should save checkpoint based on interval.

        Args:
            checkpoint_interval: Number of completed items between checkpoints

        Returns:
            True if should checkpoint
        """
        if not self.completed_items:
            return False

        # Checkpoint every N completed items
        return len(self.completed_items) % checkpoint_interval == 0

"""Learning system protocol for adaptive error handling.

This module provides protocols and data structures for:
- Recording fix attempts and their outcomes
- Learning from historical successes/failures
- Recommending new error patterns
- Auto-updating error classification rules

Adaptive learning system for pattern optimization based on historical outcomes.

Key concepts:
- LearningRecord: Track a fix attempt (error, fix applied, outcome)
- LearningStore: Persistence for learning records
- Pattern discovery: Identify new error patterns from unknowns
- Success rate tracking: Which fixes work best for which errors

Example:
    from sibyl.mcp_server.infrastructure.learning import (
        LearningRecord,
        LearningStore,
        record_fix_attempt,
    )

    # Record a successful fix
    record = LearningRecord(
        error_message="Type mismatch: TIMESTAMP vs DATETIME",
        error_category="type_mismatch",
        fix_applied="Changed TIMESTAMP_SUB to DATETIME_SUB",
        outcome="success",
        model_name="example_resource",
    )
    store.save_record(record)

    # Later: Learn from patterns
    patterns = learning_engine.discover_patterns()
    # Recommends: Add "TIMESTAMP vs DATETIME" to type_mismatch keywords
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

logger = logging.getLogger(__name__)


class FixOutcome(str, Enum):
    """Outcome of a fix attempt."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"  # Fixed some issues but not all


@dataclass
class LearningRecord:
    """Record of a fix attempt for learning purposes.

    Attributes:
        record_id: Unique record ID
        error_message: Original error message
        error_category: Classified error category
        fix_applied: Description of fix that was applied
        outcome: Whether fix succeeded/failed
        model_name: Model where error occurred
        confidence: Classification confidence (0.0-1.0)
        matched_keywords: Keywords that matched during classification
        time_to_fix_seconds: How long fix took
        retry_count: Number of retries before success/failure
        created_at: When record was created
        metadata: Additional context
    """

    record_id: str = field(default_factory=lambda: str(uuid4()))
    error_message: str = ""
    error_category: str = "unknown"
    fix_applied: str = ""
    outcome: FixOutcome = FixOutcome.FAILURE
    model_name: str | None = None
    confidence: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)
    time_to_fix_seconds: float = 0.0
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "record_id": self.record_id,
            "error_message": self.error_message,
            "error_category": self.error_category,
            "fix_applied": self.fix_applied,
            "outcome": self.outcome.value,
            "model_name": self.model_name,
            "confidence": self.confidence,
            "matched_keywords": self.matched_keywords,
            "time_to_fix_seconds": self.time_to_fix_seconds,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningRecord":
        """Create record from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            LearningRecord instance
        """
        return cls(
            record_id=data.get("record_id", str(uuid4())),
            error_message=data.get("error_message", ""),
            error_category=data.get("error_category", "unknown"),
            fix_applied=data.get("fix_applied", ""),
            outcome=FixOutcome(data.get("outcome", "failure")),
            model_name=data.get("model_name"),
            confidence=data.get("confidence", 0.0),
            matched_keywords=data.get("matched_keywords", []),
            time_to_fix_seconds=data.get("time_to_fix_seconds", 0.0),
            retry_count=data.get("retry_count", 0),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.utcnow()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PatternRecommendation:
    """Recommendation for a new error pattern.

    Attributes:
        category: Recommended category name
        keywords: Recommended keywords to add
        suggested_fixes: Recommended fixes to add
        confidence: Confidence in this recommendation (0.0-1.0)
        supporting_records: Learning records that support this recommendation
        frequency: How often this pattern appeared
        success_rate: Success rate of fixes for this pattern
    """

    category: str
    keywords: list[str]
    suggested_fixes: list[str]
    confidence: float
    supporting_records: list[str] = field(default_factory=list)  # Record IDs
    frequency: int = 0
    success_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category,
            "keywords": self.keywords,
            "suggested_fixes": self.suggested_fixes,
            "confidence": self.confidence,
            "supporting_records": self.supporting_records,
            "frequency": self.frequency,
            "success_rate": self.success_rate,
        }


@runtime_checkable
class LearningStore(Protocol):
    """Protocol for learning record persistence.

    Implementations can use:
    - JSON files
    - SQLite database
    - PostgreSQL
    - Redis
    """

    def save_record(self, record: LearningRecord) -> None:
        """Save a learning record.

        Args:
            record: Learning record to save
        """
        ...

    def load_record(self, record_id: str) -> LearningRecord | None:
        """Load a specific record.

        Args:
            record_id: Record ID

        Returns:
            Record or None if not found
        """
        ...

    def list_records(
        self,
        category: str | None = None,
        outcome: FixOutcome | None = None,
        limit: int = 100,
    ) -> list[LearningRecord]:
        """List learning records with optional filters.

        Args:
            category: Filter by error category
            outcome: Filter by outcome
            limit: Maximum records to return

        Returns:
            List of records
        """
        ...

    def get_statistics(self) -> dict[str, Any]:
        """Get learning statistics.

        Returns:
            Dictionary with statistics (total records, success rate, etc.)
        """
        ...

    def delete_old_records(self, max_age_days: int = 90) -> int:
        """Delete records older than max_age_days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of records deleted
        """
        ...


@dataclass
class FixSuccessPattern:
    """Pattern of successful fixes for a category.

    Tracks which fixes work best for specific error categories.

    Attributes:
        category: Error category
        fix_description: Description of the fix
        success_count: Number of successful applications
        failure_count: Number of failed applications
        success_rate: Success rate (0.0-1.0)
        avg_time_to_fix_seconds: Average time to apply fix
        models: List of models where this fix worked
        last_used: When fix was last used
    """

    category: str
    fix_description: str
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    avg_time_to_fix_seconds: float = 0.0
    models: list[str] = field(default_factory=list)
    last_used: datetime | None = None

    def update_statistics(self) -> None:
        """Update computed statistics."""
        total = self.success_count + self.failure_count
        if total > 0:
            self.success_rate = self.success_count / total

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category,
            "fix_description": self.fix_description,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "avg_time_to_fix_seconds": self.avg_time_to_fix_seconds,
            "models": self.models,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

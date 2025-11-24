"""Quality control domain protocols and types.

This module defines the protocol interfaces and data structures for the quality
control system that validates tool outputs before returning them to clients.

The QC system provides:
- Structured validation verdicts (GREEN/YELLOW/RED)
- Error categorization and suggested fixes
- Automatic retry logic with enriched context
- Metrics tracking for QC performance

Design principles:
- Protocol-based interface for dependency inversion
- Immutable verdict structures for safety
- Rich metadata for observability
- Composable validators for extensibility
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

# Import VerdictStatus from core contracts to avoid layering violations
from sibyl.core.contracts.validator_base import VerdictStatus


@dataclass(frozen=True)
class ValidationVerdict:
    """Result of a quality control validation.

    Attributes:
        status: Verdict status (GREEN/YELLOW/RED)
        feedback: Human-readable feedback message
        error_category: Optional error category (e.g., "syntax_error", "type_mismatch")
        suggested_fixes: List of suggested fixes for the issue
        validator_name: Name of the validator that produced this verdict
        timestamp: When the validation was performed
        metadata: Additional context (e.g., error locations, affected resources)
        validation_id: Unique identifier for this validation
    """

    status: VerdictStatus
    feedback: str
    error_category: str | None = None
    suggested_fixes: list[str] = field(default_factory=list)
    validator_name: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    validation_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        """Validate verdict structure."""
        # Ensure status is VerdictStatus enum
        if isinstance(self.status, str):
            # Convert string to enum if needed
            object.__setattr__(self, "status", VerdictStatus(self.status))

        # RED verdicts should have error_category
        if self.status == VerdictStatus.RED and not self.error_category:
            msg = "RED verdicts must have an error_category"
            raise ValueError(msg)

        # Suggested fixes should be non-empty for RED/YELLOW
        if self.status in (VerdictStatus.RED, VerdictStatus.YELLOW) and not self.suggested_fixes:
            # Warning, not error - some validators may not have suggestions
            pass

    @property
    def is_success(self) -> bool:
        """Whether validation passed (GREEN or YELLOW)."""
        return self.status in (VerdictStatus.GREEN, VerdictStatus.YELLOW)

    @property
    def requires_retry(self) -> bool:
        """Whether this verdict should trigger a retry."""
        return self.status == VerdictStatus.RED

    def to_dict(self) -> dict[str, Any]:
        """Convert verdict to dictionary for serialization."""
        return {
            "validation_id": self.validation_id,
            "status": self.status.value,
            "feedback": self.feedback,
            "error_category": self.error_category,
            "suggested_fixes": self.suggested_fixes,
            "validator_name": self.validator_name,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class QCRetryMetadata:
    """Metadata tracking retry attempts for QC validation.

    Attributes:
        attempt: Current retry attempt number (1-indexed)
        max_attempts: Maximum number of retry attempts allowed
        previous_verdicts: List of verdicts from previous attempts
        previous_fixes_tried: List of fixes that were attempted
        operation_id: Identifier linking all retries for the same operation
    """

    attempt: int
    max_attempts: int
    previous_verdicts: list[ValidationVerdict] = field(default_factory=list)
    previous_fixes_tried: list[str] = field(default_factory=list)
    operation_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        """Validate retry metadata."""
        if self.attempt < 1:
            msg = f"attempt must be >= 1, got {self.attempt}"
            raise ValueError(msg)

        if self.max_attempts < 1:
            msg = f"max_attempts must be >= 1, got {self.max_attempts}"
            raise ValueError(msg)

        if self.attempt > self.max_attempts:
            msg = f"attempt ({self.attempt}) cannot exceed max_attempts ({self.max_attempts})"
            raise ValueError(msg)

    @property
    def is_final_attempt(self) -> bool:
        """Whether this is the final retry attempt."""
        return self.attempt >= self.max_attempts

    @property
    def retries_exhausted(self) -> bool:
        """Whether all retry attempts have been used."""
        return self.attempt >= self.max_attempts

    def to_dict(self) -> dict[str, Any]:
        """Convert retry metadata to dictionary."""
        return {
            "operation_id": self.operation_id,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "previous_verdicts": [v.to_dict() for v in self.previous_verdicts],
            "previous_fixes_tried": self.previous_fixes_tried,
        }


@runtime_checkable
class Validator(Protocol):
    """Protocol for QC validators.

    Validators inspect tool outputs and return verdicts about their quality.
    They can check syntax, semantics, anti-patterns, or any other quality criteria.
    """

    @property
    def name(self) -> str:
        """Validator name for identification."""
        ...

    async def validate(self, output: Any, context: dict[str, Any]) -> ValidationVerdict:
        """Validate tool output and return a verdict.

        Args:
            output: The tool output to validate (type depends on tool)
            context: Additional context for validation (e.g., tool name, model name)

        Returns:
            ValidationVerdict with status and feedback
        """
        ...


@runtime_checkable
class QualityControlProvider(Protocol):
    """Protocol for quality control orchestration.

    The QC provider coordinates multiple validators and manages retry logic.
    """

    async def validate_output(
        self,
        output: Any,
        context: dict[str, Any],
        validators: list[Validator] | None = None,
    ) -> ValidationVerdict:
        """Validate output using configured validators.

        Args:
            output: Tool output to validate
            context: Validation context
            validators: Optional list of validators (uses defaults if None)

        Returns:
            Aggregated validation verdict
        """
        ...

    async def validate_with_retry(
        self,
        operation: Any,  # Callable that produces output
        context: dict[str, Any],
        max_retries: int = 2,
        validators: list[Validator] | None = None,
    ) -> tuple[Any, ValidationVerdict, QCRetryMetadata]:
        """Execute operation with automatic QC retry on RED verdicts.

        Args:
            operation: Callable that produces output to validate
            context: Validation context
            max_retries: Maximum number of retry attempts
            validators: Optional list of validators

        Returns:
            Tuple of (output, final_verdict, retry_metadata)

        Raises:
            QualityControlError: If all retry attempts are exhausted with RED verdict
        """
        ...

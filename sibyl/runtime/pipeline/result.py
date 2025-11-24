"""Pipeline result envelope for runtime execution.

This module provides a standardized result model for pipeline execution,
including success/failure status, error details, and observability metadata.

Example:
    # Success result
    result = PipelineResult.success(
        data={"output": "result data"},
        trace_id="abc-123",
        duration_ms=1234.5,
    )

    # Error result
    result = PipelineResult.error(
        error=PipelineError(
            type="ValidationError",
            message="Invalid input",
            details={"field": "query"},
        ),
        trace_id="abc-123",
        duration_ms=100.0,
    )
"""

import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PipelineStatus(Enum):
    """Status of a pipeline execution."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class TokenUsage:
    """Token usage information for LLM calls.

    Attributes:
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total tokens used (prompt + completion)
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Add two TokenUsage instances together."""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary for serialization."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class StepResult:
    """Result information for a single pipeline step.

    Attributes:
        step_name: Name of the step (e.g., "rag.chunker")
        shop_name: Name of the shop executing the step
        technique_name: Name of the technique
        status: Step execution status
        duration_ms: Step execution duration in milliseconds
        start_time: Step start timestamp (ISO format)
        end_time: Step end timestamp (ISO format)
        tokens: Token usage for this step (if applicable)
        error: Error information if step failed
    """

    step_name: str
    shop_name: str
    technique_name: str
    status: str  # "success", "error", "skipped"
    duration_ms: float
    start_time: str
    end_time: str
    tokens: TokenUsage | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "step_name": self.step_name,
            "shop_name": self.shop_name,
            "technique_name": self.technique_name,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }

        if self.tokens:
            result["tokens"] = self.tokens.to_dict()

        if self.error:
            result["error"] = self.error

        return result


@dataclass
class PipelineError:
    """Structured error information for pipeline failures.

    Attributes:
        type: Error type (e.g., "ValidationError", "ProviderError", "TimeoutError")
        message: Human-readable error message
        details: Additional error context (serializable dict)
        stack_trace: Optional stack trace for debugging
    """

    type: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    stack_trace: str | None = None

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        error_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> "PipelineError":
        """Create a PipelineError from an exception.

        Args:
            exc: Exception instance
            error_type: Optional error type override (defaults to exception class name)
            details: Additional error details

        Returns:
            PipelineError instance
        """
        return cls(
            type=error_type or exc.__class__.__name__,
            message=str(exc),
            details=details or {},
            stack_trace="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "type": self.type,
            "message": self.message,
            "details": self.details,
            "stack_trace": self.stack_trace,
        }


@dataclass
class PipelineResult:
    """Result envelope for pipeline execution.

    This provides a standardized result format that includes:
    - Success/failure status
    - Result data or error information
    - Observability metadata (trace_id, duration, logs)
    - Per-step timing and token usage
    - Cost estimation

    Attributes:
        ok: True if execution succeeded, False otherwise
        status: Execution status (SUCCESS, ERROR, or TIMEOUT)
        data: Result data (only present on success)
        error: Error information (only present on failure)
        trace_id: Unique trace ID for correlating logs
        logs: Optional list of log entries collected during execution
        duration_ms: Execution duration in milliseconds
        pipeline_name: Name of the pipeline executed
        start_time: Pipeline start timestamp (ISO format)
        end_time: Pipeline end timestamp (ISO format)
        step_results: Per-step execution results
        tokens: Aggregated token usage across all steps
        estimated_cost_usd: Estimated cost in USD (if token pricing available)
    """

    ok: bool
    status: PipelineStatus
    data: dict[str, Any] | None = None
    error: PipelineError | None = None
    trace_id: str = ""
    logs: list[dict[str, Any]] | None = None
    duration_ms: float | None = None
    pipeline_name: str = ""
    start_time: str = ""
    end_time: str = ""
    step_results: list[StepResult] = field(default_factory=list)
    tokens: TokenUsage | None = None
    estimated_cost_usd: float | None = None

    @classmethod
    def success(
        cls,
        data: dict[str, Any],
        trace_id: str = "",
        logs: list[dict[str, Any]] | None = None,
        duration_ms: float | None = None,
        pipeline_name: str = "",
        start_time: str = "",
        end_time: str = "",
        step_results: list[StepResult] | None = None,
        tokens: TokenUsage | None = None,
        estimated_cost_usd: float | None = None,
    ) -> "PipelineResult":
        """Create a success result.

        Args:
            data: Result data
            trace_id: Trace ID for log correlation
            logs: Optional log entries
            duration_ms: Execution duration in milliseconds
            pipeline_name: Name of the pipeline
            start_time: Pipeline start timestamp
            end_time: Pipeline end timestamp
            step_results: Per-step execution results
            tokens: Aggregated token usage
            estimated_cost_usd: Estimated cost in USD

        Returns:
            PipelineResult instance with success status
        """
        return cls(
            ok=True,
            status=PipelineStatus.SUCCESS,
            data=data,
            error=None,  # Explicitly set to None for success
            trace_id=trace_id,
            logs=logs,
            duration_ms=duration_ms,
            pipeline_name=pipeline_name,
            start_time=start_time,
            end_time=end_time,
            step_results=step_results or [],
            tokens=tokens,
            estimated_cost_usd=estimated_cost_usd,
        )

    @classmethod
    def error(
        cls,
        error: PipelineError,
        trace_id: str = "",
        logs: list[dict[str, Any]] | None = None,
        duration_ms: float | None = None,
        pipeline_name: str = "",
        start_time: str = "",
        end_time: str = "",
        step_results: list[StepResult] | None = None,
        tokens: TokenUsage | None = None,
        estimated_cost_usd: float | None = None,
    ) -> "PipelineResult":
        """Create an error result.

        Args:
            error: Error information
            trace_id: Trace ID for log correlation
            logs: Optional log entries
            duration_ms: Execution duration in milliseconds
            pipeline_name: Name of the pipeline
            start_time: Pipeline start timestamp
            end_time: Pipeline end timestamp
            step_results: Per-step execution results (up to failure point)
            tokens: Aggregated token usage (up to failure point)
            estimated_cost_usd: Estimated cost in USD

        Returns:
            PipelineResult instance with error status
        """
        # Determine status from error type
        status = PipelineStatus.TIMEOUT if error.type == "TimeoutError" else PipelineStatus.ERROR

        return cls(
            ok=False,
            status=status,
            error=error,
            trace_id=trace_id,
            logs=logs,
            duration_ms=duration_ms,
            pipeline_name=pipeline_name,
            start_time=start_time,
            end_time=end_time,
            step_results=step_results or [],
            tokens=tokens,
            estimated_cost_usd=estimated_cost_usd,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        result = {
            "ok": self.ok,
            "status": self.status.value,
            "trace_id": self.trace_id,
            "pipeline_name": self.pipeline_name,
        }

        if self.data is not None:
            result["data"] = self.data

        if self.error is not None:
            result["error"] = self.error.to_dict()

        if self.logs is not None:
            result["logs"] = self.logs

        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms

        if self.start_time:
            result["start_time"] = self.start_time

        if self.end_time:
            result["end_time"] = self.end_time

        if self.step_results:
            result["step_results"] = [step.to_dict() for step in self.step_results]

        if self.tokens is not None:
            result["tokens"] = self.tokens.to_dict()

        if self.estimated_cost_usd is not None:
            result["estimated_cost_usd"] = self.estimated_cost_usd

        return result

    def __repr__(self) -> str:
        """String representation for debugging."""
        if self.ok:
            return (
                f"PipelineResult(ok=True, trace_id={self.trace_id}, duration_ms={self.duration_ms})"
            )
        return f"PipelineResult(ok=False, error={self.error.type}, trace_id={self.trace_id})"

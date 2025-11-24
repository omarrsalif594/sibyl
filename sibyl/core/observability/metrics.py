"""Metrics collection and tracking for pipeline execution.

This module provides lightweight metrics tracking for observability,
including per-step timing, retry counts, and outcome tracking.

Example:
    from sibyl.core.observability import MetricsCollector

    collector = MetricsCollector()

    # Start tracking a pipeline
    collector.pipeline_start("my_pipeline", trace_id="abc-123")

    # Track step execution
    with collector.track_step("step_1"):
        # Execute step
        pass

    # Record outcome
    collector.step_outcome("step_1", "success")

    # Get metrics
    metrics = collector.get_pipeline_metrics()
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class StepOutcome(Enum):
    """Outcome of a step execution."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class StepMetrics:
    """Metrics for a single pipeline step.

    Attributes:
        step_name: Name of the step
        start_time: Step start timestamp (ISO format)
        end_time: Step end timestamp (ISO format)
        duration_ms: Execution duration in milliseconds
        outcome: Step outcome (success, error, timeout, skipped)
        retry_count: Number of retries attempted
        error_message: Error message if failed
        metadata: Additional metadata
    """

    step_name: str
    start_time: str
    end_time: str
    duration_ms: float
    outcome: StepOutcome
    retry_count: int = 0
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "step_name": self.step_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "outcome": self.outcome.value,
            "retry_count": self.retry_count,
        }

        if self.error_message:
            result["error_message"] = self.error_message

        if self.metadata:
            result["metadata"] = self.metadata

        return result


@dataclass
class PipelineMetrics:
    """Aggregated metrics for a pipeline execution.

    Attributes:
        pipeline_name: Name of the pipeline
        trace_id: Unique trace ID
        start_time: Pipeline start timestamp (ISO format)
        end_time: Pipeline end timestamp (ISO format)
        duration_ms: Total execution duration in milliseconds
        step_metrics: List of per-step metrics
        total_steps: Total number of steps
        successful_steps: Number of successful steps
        failed_steps: Number of failed steps
        skipped_steps: Number of skipped steps
        metadata: Additional metadata
    """

    pipeline_name: str
    trace_id: str
    start_time: str
    end_time: str
    duration_ms: float
    step_metrics: list[StepMetrics] = field(default_factory=list)
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pipeline_name": self.pipeline_name,
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "step_metrics": [m.to_dict() for m in self.step_metrics],
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "metadata": self.metadata,
        }


class MetricsCollector:
    """Collects and tracks metrics during pipeline execution.

    This collector provides a lightweight way to track:
    - Pipeline and step execution times
    - Step outcomes (success, error, timeout, skipped)
    - Retry counts
    - Custom metadata

    Attributes:
        pipeline_name: Name of the current pipeline
        trace_id: Trace ID for the current execution
        step_stack: Stack of currently executing steps
        completed_steps: List of completed step metrics
    """

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self.pipeline_name: str | None = None
        self.trace_id: str | None = None
        self.pipeline_start_time: float | None = None
        self.pipeline_end_time: float | None = None
        self.step_stack: list[dict[str, Any]] = []
        self.completed_steps: list[StepMetrics] = []
        self.metadata: dict[str, Any] = {}

    def pipeline_start(
        self,
        pipeline_name: str,
        trace_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Mark the start of a pipeline execution.

        Args:
            pipeline_name: Name of the pipeline
            trace_id: Unique trace ID
            metadata: Optional metadata to attach
        """
        self.pipeline_name = pipeline_name
        self.trace_id = trace_id
        self.pipeline_start_time = time.time()
        self.metadata = metadata or {}

        logger.debug(
            f"Pipeline started: {pipeline_name} [trace_id={trace_id}]",
            extra={"trace_id": trace_id, "pipeline_name": pipeline_name},
        )

    def pipeline_end(self) -> None:
        """Mark the end of a pipeline execution."""
        self.pipeline_end_time = time.time()

        if self.pipeline_start_time and self.pipeline_name:
            duration_ms = (self.pipeline_end_time - self.pipeline_start_time) * 1000

            logger.debug(
                f"Pipeline ended: {self.pipeline_name} [duration={duration_ms:.2f}ms]",
                extra={
                    "trace_id": self.trace_id,
                    "pipeline_name": self.pipeline_name,
                    "duration_ms": duration_ms,
                },
            )

    @contextmanager
    def track_step(self, step_name: str, metadata: dict[str, Any] | None = None) -> Any:
        """Context manager to track step execution timing.

        Args:
            step_name: Name of the step
            metadata: Optional metadata to attach

        Yields:
            None

        Example:
            with collector.track_step("my_step"):
                # Execute step
                pass
        """
        start_time = time.time()
        start_iso = datetime.utcnow().isoformat() + "Z"

        # Push to stack
        self.step_stack.append(
            {
                "step_name": step_name,
                "start_time": start_time,
                "start_iso": start_iso,
                "metadata": metadata or {},
            }
        )

        logger.debug(
            f"Step started: {step_name}",
            extra={
                "trace_id": self.trace_id,
                "pipeline_name": self.pipeline_name,
                "step_name": step_name,
            },
        )

        try:
            yield
        finally:
            # Pop from stack
            if self.step_stack:
                step_data = self.step_stack.pop()
                end_time = time.time()
                datetime.utcnow().isoformat() + "Z"
                duration_ms = (end_time - step_data["start_time"]) * 1000

                logger.debug(
                    f"Step ended: {step_name} [duration={duration_ms:.2f}ms]",
                    extra={
                        "trace_id": self.trace_id,
                        "pipeline_name": self.pipeline_name,
                        "step_name": step_name,
                        "duration_ms": duration_ms,
                    },
                )

    def step_outcome(
        self,
        step_name: str,
        outcome: str,
        retry_count: int = 0,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record the outcome of a step execution.

        Args:
            step_name: Name of the step
            outcome: Outcome (success, error, timeout, skipped)
            retry_count: Number of retries attempted
            error_message: Error message if failed
            metadata: Additional metadata
        """
        # Find corresponding step in stack or completed steps
        # For now, we'll create a metrics entry
        try:
            outcome_enum = StepOutcome(outcome)
        except ValueError:
            logger.warning("Invalid outcome '%s', using ERROR", outcome)
            outcome_enum = StepOutcome.ERROR

        # Create step metrics (simplified - would normally retrieve from stack)
        step_metrics = StepMetrics(
            step_name=step_name,
            start_time=datetime.utcnow().isoformat() + "Z",
            end_time=datetime.utcnow().isoformat() + "Z",
            duration_ms=0.0,
            outcome=outcome_enum,
            retry_count=retry_count,
            error_message=error_message,
            metadata=metadata or {},
        )

        self.completed_steps.append(step_metrics)

        logger.info(
            f"Step outcome: {step_name} = {outcome}",
            extra={
                "trace_id": self.trace_id,
                "pipeline_name": self.pipeline_name,
                "step_name": step_name,
                "outcome": outcome,
                "retry_count": retry_count,
            },
        )

    def get_pipeline_metrics(self) -> PipelineMetrics | None:
        """Get aggregated metrics for the pipeline execution.

        Returns:
            PipelineMetrics or None if pipeline not started
        """
        if not self.pipeline_name or not self.trace_id or not self.pipeline_start_time:
            return None

        end_time = self.pipeline_end_time or time.time()
        duration_ms = (end_time - self.pipeline_start_time) * 1000

        # Count outcomes
        successful = sum(1 for m in self.completed_steps if m.outcome == StepOutcome.SUCCESS)
        failed = sum(1 for m in self.completed_steps if m.outcome == StepOutcome.ERROR)
        skipped = sum(1 for m in self.completed_steps if m.outcome == StepOutcome.SKIPPED)

        return PipelineMetrics(
            pipeline_name=self.pipeline_name,
            trace_id=self.trace_id,
            start_time=datetime.fromtimestamp(self.pipeline_start_time).isoformat() + "Z",
            end_time=datetime.fromtimestamp(end_time).isoformat() + "Z",
            duration_ms=duration_ms,
            step_metrics=self.completed_steps,
            total_steps=len(self.completed_steps),
            successful_steps=successful,
            failed_steps=failed,
            skipped_steps=skipped,
            metadata=self.metadata,
        )

    def reset(self) -> None:
        """Reset collector for new pipeline execution."""
        self.pipeline_name = None
        self.trace_id = None
        self.pipeline_start_time = None
        self.pipeline_end_time = None
        self.step_stack = []
        self.completed_steps = []
        self.metadata = {}

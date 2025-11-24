"""Observability utilities for pipeline execution.

This module provides utilities for tracking and logging pipeline execution
with comprehensive observability including:
- Structured logging with trace IDs
- Token usage tracking and aggregation
- Cost estimation
- Per-step timing and status
- Metrics collection

Example:
    from sibyl.runtime.pipeline.observability import PipelineObserver

    observer = PipelineObserver(pipeline_name="web_research")

    # Track step execution
    with observer.track_step("rag.chunker", "web_research_shop", "chunker") as step:
        result = execute_technique()
        step.record_tokens(prompt_tokens=100, completion_tokens=50)

    # Get final result
    pipeline_result = observer.build_result(
        ok=True,
        data={"output": "result"},
    )
"""

import logging
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from sibyl.runtime.pipeline.pricing import estimate_cost_from_usage
from sibyl.runtime.pipeline.result import (
    PipelineError,
    PipelineResult,
    PipelineStatus,
    StepResult,
    TokenUsage,
)

logger = logging.getLogger(__name__)


def _get_metrics_collector() -> Any:
    """Lazy import of metrics collector to avoid circular imports."""
    try:
        from sibyl.runtime.pipeline.metrics import get_metrics_collector  # optional dependency

        return get_metrics_collector()
    except ImportError:
        # If metrics module not available, return None
        return None


class StepTracker:
    """Tracks execution of a single pipeline step.

    Attributes:
        step_name: Full step reference (e.g., "rag.chunker")
        shop_name: Shop executing the step
        technique_name: Technique being executed
        trace_id: Trace ID for correlation
        start_time: Step start timestamp
        start_time_iso: ISO format start time
    """

    def __init__(
        self,
        step_name: str,
        shop_name: str,
        technique_name: str,
        trace_id: str,
    ) -> None:
        """Initialize step tracker.

        Args:
            step_name: Full step reference
            shop_name: Shop name
            technique_name: Technique name
            trace_id: Trace ID for correlation
        """
        self.step_name = step_name
        self.shop_name = shop_name
        self.technique_name = technique_name
        self.trace_id = trace_id
        self.start_time = time.time()
        self.start_time_iso = datetime.utcnow().isoformat() + "Z"
        self.tokens = TokenUsage()
        self.status = "success"
        self.error: str | None = None

    def record_tokens(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int | None = None,
    ) -> None:
        """Record token usage for this step.

        Args:
            prompt_tokens: Number of prompt/input tokens
            completion_tokens: Number of completion/output tokens
            total_tokens: Total tokens (computed if not provided)
        """
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens

        self.tokens = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def record_error(self, error: str) -> None:
        """Record an error for this step.

        Args:
            error: Error message
        """
        self.status = "error"
        self.error = error

    def finalize(self) -> StepResult:
        """Finalize step and create StepResult.

        Returns:
            StepResult with all collected information
        """
        end_time = time.time()
        end_time_iso = datetime.utcnow().isoformat() + "Z"
        duration_ms = (end_time - self.start_time) * 1000

        # Log step completion
        log_data = {
            "event": "step_complete",
            "trace_id": self.trace_id,
            "step_name": self.step_name,
            "shop_name": self.shop_name,
            "technique_name": self.technique_name,
            "status": self.status,
            "duration_ms": duration_ms,
            "start_time": self.start_time_iso,
            "end_time": end_time_iso,
        }

        if self.tokens.total_tokens > 0:
            log_data["tokens"] = self.tokens.to_dict()

        if self.error:
            log_data["error"] = self.error

        logger.info(f"Step completed: {self.step_name}", extra={"structured": log_data})

        # Record metrics (if available)
        metrics_collector = _get_metrics_collector()
        if metrics_collector:
            metrics_collector.record_step_execution(
                pipeline_name="",  # Will be filled by PipelineObserver
                step_name=self.step_name,
                shop_name=self.shop_name,
                duration_ms=duration_ms,
                status=self.status,
                trace_id=self.trace_id,
            )

        return StepResult(
            step_name=self.step_name,
            shop_name=self.shop_name,
            technique_name=self.technique_name,
            status=self.status,
            duration_ms=duration_ms,
            start_time=self.start_time_iso,
            end_time=end_time_iso,
            tokens=self.tokens if self.tokens.total_tokens > 0 else None,
            error=self.error,
        )


class PipelineObserver:
    """Observability tracking for pipeline execution.

    This class provides comprehensive observability for pipeline execution:
    - Generates and maintains trace IDs
    - Tracks per-step execution (timing, tokens, status)
    - Aggregates metrics across steps
    - Estimates costs
    - Emits structured logs
    - Records metrics

    Attributes:
        pipeline_name: Name of the pipeline
        trace_id: Unique trace ID for this execution
        start_time: Pipeline start timestamp
        start_time_iso: ISO format start time
        step_results: List of completed step results
        total_tokens: Aggregated token usage
    """

    def __init__(self, pipeline_name: str, trace_id: str | None = None) -> None:
        """Initialize pipeline observer.

        Args:
            pipeline_name: Name of the pipeline
            trace_id: Optional trace ID (generated if not provided)
        """
        self.pipeline_name = pipeline_name
        self.trace_id = trace_id or str(uuid.uuid4())
        self.start_time = time.time()
        self.start_time_iso = datetime.utcnow().isoformat() + "Z"
        self.step_results: list[StepResult] = []
        self.total_tokens = TokenUsage()
        self._current_model: str | None = None

        # Log pipeline start
        logger.info(
            f"Pipeline started: {pipeline_name}",
            extra={
                "structured": {
                    "event": "pipeline_start",
                    "trace_id": self.trace_id,
                    "pipeline_name": pipeline_name,
                    "timestamp": self.start_time_iso,
                }
            },
        )

    def set_model(self, model: str) -> None:
        """Set the model being used for cost estimation.

        Args:
            model: Model name (e.g., "gpt-4", "claude-3-opus")
        """
        self._current_model = model

    @contextmanager
    def track_step(
        self,
        step_name: str,
        shop_name: str,
        technique_name: str,
    ) -> Iterator[StepTracker]:
        """Context manager for tracking step execution.

        Args:
            step_name: Full step reference
            shop_name: Shop name
            technique_name: Technique name

        Yields:
            StepTracker for recording step metrics

        Example:
            with observer.track_step("rag.chunker", "rag_shop", "chunker") as step:
                result = execute_technique()
                step.record_tokens(prompt_tokens=100, completion_tokens=50)
        """
        tracker = StepTracker(step_name, shop_name, technique_name, self.trace_id)

        try:
            yield tracker
        except Exception as e:
            tracker.record_error(str(e))
            raise
        finally:
            # Finalize step and collect results
            step_result = tracker.finalize()
            self.step_results.append(step_result)

            # Aggregate tokens
            if step_result.tokens:
                self.total_tokens = self.total_tokens + step_result.tokens

    def build_result(
        self,
        ok: bool,
        data: dict[str, Any] | None = None,
        error: PipelineError | None = None,
    ) -> PipelineResult:
        """Build final PipelineResult with all observability data.

        Args:
            ok: Whether pipeline succeeded
            data: Result data (if success)
            error: Error information (if failure)

        Returns:
            Complete PipelineResult with observability metadata
        """
        end_time = time.time()
        end_time_iso = datetime.utcnow().isoformat() + "Z"
        duration_ms = (end_time - self.start_time) * 1000

        # Determine status
        if ok:
            status = PipelineStatus.SUCCESS
        elif error and error.type == "TimeoutError":
            status = PipelineStatus.TIMEOUT
        else:
            status = PipelineStatus.ERROR

        # Estimate cost
        estimated_cost: float | None = None
        if self._current_model and self.total_tokens.total_tokens > 0:
            estimated_cost = estimate_cost_from_usage(
                model=self._current_model,
                tokens_in=self.total_tokens.prompt_tokens,
                tokens_out=self.total_tokens.completion_tokens,
            )

        # Log pipeline completion
        log_data = {
            "event": "pipeline_complete",
            "trace_id": self.trace_id,
            "pipeline_name": self.pipeline_name,
            "status": status.value,
            "duration_ms": duration_ms,
            "start_time": self.start_time_iso,
            "end_time": end_time_iso,
            "num_steps": len(self.step_results),
        }

        if self.total_tokens.total_tokens > 0:
            log_data["tokens"] = self.total_tokens.to_dict()

        if estimated_cost is not None:
            log_data["estimated_cost_usd"] = estimated_cost

        if error:
            log_data["error_type"] = error.type
            log_data["error_message"] = error.message

        logger.info(
            f"Pipeline completed: {self.pipeline_name} ({status.value})",
            extra={"structured": log_data},
        )

        # Record metrics (if available)
        metrics_collector = _get_metrics_collector()
        if metrics_collector:
            metrics_collector.record_pipeline_run(
                pipeline_name=self.pipeline_name,
                status=status.value,
                duration_ms=duration_ms,
                trace_id=self.trace_id,
                tokens=self.total_tokens.to_dict() if self.total_tokens.total_tokens > 0 else None,
                estimated_cost_usd=estimated_cost,
            )

        # Build result
        if ok:
            return PipelineResult.success(
                data=data or {},
                trace_id=self.trace_id,
                duration_ms=duration_ms,
                pipeline_name=self.pipeline_name,
                start_time=self.start_time_iso,
                end_time=end_time_iso,
                step_results=self.step_results,
                tokens=self.total_tokens if self.total_tokens.total_tokens > 0 else None,
                estimated_cost_usd=estimated_cost,
            )
        return PipelineResult.error(
            error=error or PipelineError(type="UnknownError", message="Unknown error"),
            trace_id=self.trace_id,
            duration_ms=duration_ms,
            pipeline_name=self.pipeline_name,
            start_time=self.start_time_iso,
            end_time=end_time_iso,
            step_results=self.step_results,
            tokens=self.total_tokens if self.total_tokens.total_tokens > 0 else None,
            estimated_cost_usd=estimated_cost,
        )

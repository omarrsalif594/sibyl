"""Metrics collection for pipeline execution.

This module provides lightweight metrics collection for runtime operations,
capturing pipeline and step execution statistics without requiring external
dependencies.

Metrics are logged as structured data and can be consumed by monitoring
systems (Datadog, Prometheus, etc.) via log aggregation.

Example:
    collector = RuntimeMetricsCollector()

    # Record pipeline execution
    collector.record_pipeline_run(
        pipeline_name="my_pipeline",
        status="success",
        duration_ms=1234.5,
        trace_id="abc-123",
    )

    # Record step execution
    collector.record_step_execution(
        pipeline_name="my_pipeline",
        step_name="chunker",
        shop_name="rag_shop",
        duration_ms=456.7,
        status="success",
        trace_id="abc-123",
    )
"""

import logging
from collections import defaultdict
from threading import Lock
from typing import Any

logger = logging.getLogger("sibyl.runtime.metrics")


class RuntimeMetricsCollector:
    """Collects and logs metrics for pipeline execution.

    This collector:
    - Logs metrics as structured data
    - Maintains in-memory counters for basic stats
    - Thread-safe for concurrent pipeline execution

    Metrics are logged at INFO level with structured data that can be
    parsed by log aggregation systems.
    """

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self._counters: dict[str, int] = defaultdict(int)
        self._lock = Lock()

    def record_pipeline_run(
        self,
        pipeline_name: str,
        status: str,
        duration_ms: float,
        trace_id: str = "",
        workspace_name: str = "",
        tokens: dict[str, int] | None = None,
        estimated_cost_usd: float | None = None,
        **extra: Any,
    ) -> None:
        """Record a pipeline execution.

        Args:
            pipeline_name: Name of the pipeline
            status: Execution status (success, error, timeout)
            duration_ms: Execution duration in milliseconds
            trace_id: Trace ID for correlation
            workspace_name: Workspace name
            tokens: Token usage dictionary (prompt_tokens, completion_tokens, total_tokens)
            estimated_cost_usd: Estimated cost in USD
            **extra: Additional metadata
        """
        # Increment counter
        counter_key = f"pipeline_run_count.{pipeline_name}.{status}"
        with self._lock:
            self._counters[counter_key] += 1

            # Track token usage
            if tokens:
                token_counter_key = f"pipeline_tokens.{pipeline_name}"
                self._counters[token_counter_key] += tokens.get("total_tokens", 0)

            # Track cost
            if estimated_cost_usd is not None:
                # Store cost in cents as integer for counter
                cost_cents = int(estimated_cost_usd * 100)
                cost_counter_key = f"pipeline_cost_cents.{pipeline_name}"
                self._counters[cost_counter_key] += cost_cents

        # Log metric
        metric_data = {
            "metric_type": "pipeline_run",
            "pipeline_name": pipeline_name,
            "status": status,
            "duration_ms": duration_ms,
            "duration_seconds": duration_ms / 1000.0,
            "trace_id": trace_id,
        }

        if workspace_name:
            metric_data["workspace_name"] = workspace_name

        if tokens:
            metric_data["tokens"] = tokens

        if estimated_cost_usd is not None:
            metric_data["estimated_cost_usd"] = estimated_cost_usd

        metric_data.update(extra)

        logger.info(
            f"Pipeline run: {pipeline_name} ({status}) in {duration_ms:.2f}ms",
            extra={"metric": metric_data},
        )

    def record_step_execution(
        self,
        pipeline_name: str,
        step_name: str,
        shop_name: str,
        duration_ms: float,
        status: str,
        trace_id: str = "",
        **extra: Any,
    ) -> None:
        """Record a pipeline step execution.

        Args:
            pipeline_name: Name of the pipeline
            step_name: Name of the step
            shop_name: Name of the shop
            duration_ms: Execution duration in milliseconds
            status: Execution status (success, error, skipped)
            trace_id: Trace ID for correlation
            **extra: Additional metadata
        """
        # Increment counter
        counter_key = f"step_execution_count.{pipeline_name}.{step_name}.{status}"
        with self._lock:
            self._counters[counter_key] += 1

        # Log metric
        metric_data = {
            "metric_type": "step_execution",
            "pipeline_name": pipeline_name,
            "step_name": step_name,
            "shop_name": shop_name,
            "status": status,
            "duration_ms": duration_ms,
            "duration_seconds": duration_ms / 1000.0,
            "trace_id": trace_id,
        }

        metric_data.update(extra)

        logger.info(
            f"Step execution: {step_name} in {shop_name} ({status}) in {duration_ms:.2f}ms",
            extra={"metric": metric_data},
        )

    def record_provider_call(
        self,
        provider_name: str,
        provider_type: str,
        duration_ms: float,
        status: str,
        trace_id: str = "",
        **extra: Any,
    ) -> None:
        """Record a provider call.

        Args:
            provider_name: Name of the provider
            provider_type: Type of provider (llm, embeddings, mcp, etc.)
            duration_ms: Call duration in milliseconds
            status: Call status (success, error, timeout)
            trace_id: Trace ID for correlation
            **extra: Additional metadata
        """
        # Increment counter
        counter_key = f"provider_call_count.{provider_name}.{status}"
        with self._lock:
            self._counters[counter_key] += 1

        # Log metric
        metric_data = {
            "metric_type": "provider_call",
            "provider_name": provider_name,
            "provider_type": provider_type,
            "status": status,
            "duration_ms": duration_ms,
            "duration_seconds": duration_ms / 1000.0,
            "trace_id": trace_id,
        }

        metric_data.update(extra)

        logger.info(
            f"Provider call: {provider_name} ({status}) in {duration_ms:.2f}ms",
            extra={"metric": metric_data},
        )

    def get_counters(self) -> dict[str, int]:
        """Get current counter values.

        Returns:
            Dictionary of counter names to values
        """
        with self._lock:
            return dict(self._counters)

    def reset_counters(self) -> None:
        """Reset all counters to zero.

        Useful for testing or when starting a new collection period.
        """
        with self._lock:
            self._counters.clear()


# Global metrics collector instance
_global_collector: RuntimeMetricsCollector | None = None


def get_metrics_collector() -> RuntimeMetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        RuntimeMetricsCollector instance
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = RuntimeMetricsCollector()
    return _global_collector


def set_metrics_collector(collector: RuntimeMetricsCollector) -> None:
    """Set the global metrics collector instance.

    Args:
        collector: RuntimeMetricsCollector instance
    """
    global _global_collector
    _global_collector = collector

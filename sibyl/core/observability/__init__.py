"""Observability module for metrics, tracing, and debugging.

This module provides lightweight observability tools for Sibyl pipelines:
- Metrics collection (timing, outcomes, retries)
- Distributed tracing (trace and span IDs)
- Debugging tools (dry-run mode)
"""

from sibyl.core.observability.dryrun import (
    DryRunPlanner,
    ExecutionPlan,
    PlannedStep,
)
from sibyl.core.observability.metrics import (
    MetricsCollector,
    PipelineMetrics,
    StepMetrics,
    StepOutcome,
)
from sibyl.core.observability.tracing import (
    Span,
    SpanEvent,
    TraceContext,
    create_trace,
)

__all__ = [
    "DryRunPlanner",
    "ExecutionPlan",
    "MetricsCollector",
    "PipelineMetrics",
    "PlannedStep",
    "Span",
    "SpanEvent",
    "StepMetrics",
    "StepOutcome",
    "TraceContext",
    "create_trace",
]

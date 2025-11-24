"""Distributed tracing for pipeline execution.

This module provides minimal tracing capabilities with trace and span IDs
for correlating logs and debugging distributed pipelines.

Example:
    from sibyl.core.observability import TraceContext, create_trace

    # Create a trace context
    trace = create_trace("my_pipeline")

    # Create a span for a step
    with trace.span("step_1") as span:
        # Execute step
        span.set_attribute("param", "value")
        span.add_event("Processing started")
"""

import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SpanEvent:
    """Event within a span.

    Attributes:
        name: Event name
        timestamp: Event timestamp (ISO format)
        attributes: Event attributes
    """

    name: str
    timestamp: str
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "attributes": self.attributes,
        }


@dataclass
class Span:
    """Trace span representing a unit of work.

    Attributes:
        span_id: Unique span ID
        trace_id: Parent trace ID
        parent_span_id: Parent span ID (if nested)
        name: Span name
        start_time: Span start timestamp (ISO format)
        end_time: Span end timestamp (ISO format)
        duration_ms: Span duration in milliseconds
        attributes: Span attributes
        events: List of events within span
        status: Span status (ok, error)
        error: Error information if failed
    """

    span_id: str
    trace_id: str
    parent_span_id: str | None
    name: str
    start_time: str
    end_time: str | None = None
    duration_ms: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)
    status: str = "ok"
    error: str | None = None

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute.

        Args:
            key: Attribute key
            value: Attribute value
        """
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add an event to the span.

        Args:
            name: Event name
            attributes: Optional event attributes
        """
        event = SpanEvent(
            name=name,
            timestamp=datetime.utcnow().isoformat() + "Z",
            attributes=attributes or {},
        )
        self.events.append(event)

        logger.debug(
            f"Span event: {name}",
            extra={
                "trace_id": self.trace_id,
                "span_id": self.span_id,
                "event_name": name,
            },
        )

    def set_error(self, error: str) -> None:
        """Mark span as error.

        Args:
            error: Error message
        """
        self.status = "error"
        self.error = error

        logger.error(
            f"Span error: {error}",
            extra={
                "trace_id": self.trace_id,
                "span_id": self.span_id,
                "error": error,
            },
        )

    def end(self, end_time: float | None = None) -> None:
        """End the span.

        Args:
            end_time: Optional end time (defaults to now)
        """
        if not self.end_time:
            end_timestamp = end_time or time.time()
            self.end_time = datetime.utcnow().isoformat() + "Z"

            # Calculate duration if we have numeric start time
            if hasattr(self, "_start_timestamp"):
                self.duration_ms = (end_timestamp - self._start_timestamp) * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": [e.to_dict() for e in self.events],
            "status": self.status,
            "error": self.error,
        }


class TraceContext:
    """Context for a distributed trace.

    This class manages a trace and its spans, providing a hierarchical
    structure for tracking pipeline execution.

    Attributes:
        trace_id: Unique trace ID
        root_span: Root span for the trace
        active_spans: Stack of currently active spans
        completed_spans: List of completed spans
    """

    def __init__(self, trace_id: str, operation_name: str) -> None:
        """Initialize trace context.

        Args:
            trace_id: Unique trace ID
            operation_name: Name of the root operation
        """
        self.trace_id = trace_id
        self.root_span = self._create_span(operation_name, parent_span_id=None)
        self.active_spans: list[Span] = [self.root_span]
        self.completed_spans: list[Span] = []

        logger.info(
            f"Trace started: {operation_name}",
            extra={"trace_id": trace_id, "operation_name": operation_name},
        )

    def _create_span(self, name: str, parent_span_id: str | None) -> Span:
        """Create a new span.

        Args:
            name: Span name
            parent_span_id: Parent span ID (if nested)

        Returns:
            New Span instance
        """
        span_id = str(uuid.uuid4())[:8]  # Short span ID
        start_timestamp = time.time()

        span = Span(
            span_id=span_id,
            trace_id=self.trace_id,
            parent_span_id=parent_span_id,
            name=name,
            start_time=datetime.utcnow().isoformat() + "Z",
        )

        # Store numeric timestamp for duration calculation
        span._start_timestamp = start_timestamp

        return span

    @contextmanager
    def span(self, name: str, attributes: dict[str, Any] | None = None) -> Any:
        """Create a child span within this trace.

        Args:
            name: Span name
            attributes: Optional initial attributes

        Yields:
            Span instance

        Example:
            with trace.span("step_1") as span:
                span.set_attribute("param", "value")
                # Execute step
        """
        # Get parent span ID from current active span
        parent_span_id = self.active_spans[-1].span_id if self.active_spans else None

        # Create new span
        span = self._create_span(name, parent_span_id)

        # Set initial attributes
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        # Push to active stack
        self.active_spans.append(span)

        logger.debug(
            f"Span started: {name}",
            extra={
                "trace_id": self.trace_id,
                "span_id": span.span_id,
                "parent_span_id": parent_span_id,
            },
        )

        try:
            yield span
        except Exception as e:
            span.set_error(str(e))
            raise
        finally:
            # Pop from stack and mark as completed
            if self.active_spans:
                completed_span = self.active_spans.pop()
                completed_span.end()
                self.completed_spans.append(completed_span)

                logger.debug(
                    f"Span ended: {name} [duration={completed_span.duration_ms:.2f}ms]",
                    extra={
                        "trace_id": self.trace_id,
                        "span_id": completed_span.span_id,
                        "duration_ms": completed_span.duration_ms,
                    },
                )

    def end(self) -> None:
        """End the trace."""
        # End root span
        if self.root_span and not self.root_span.end_time:
            self.root_span.end()

        logger.info(
            f"Trace ended: {self.root_span.name}",
            extra={
                "trace_id": self.trace_id,
                "duration_ms": self.root_span.duration_ms,
            },
        )

    def get_spans(self) -> list[Span]:
        """Get all spans in this trace.

        Returns:
            List of all spans (completed and active)
        """
        return [self.root_span, *self.completed_spans]

    def to_dict(self) -> dict[str, Any]:
        """Convert trace to dictionary for serialization.

        Returns:
            Dictionary with trace information
        """
        return {
            "trace_id": self.trace_id,
            "root_span": self.root_span.to_dict(),
            "spans": [s.to_dict() for s in self.completed_spans],
            "total_spans": len(self.completed_spans) + 1,  # +1 for root span
        }


def create_trace(operation_name: str, trace_id: str | None = None) -> TraceContext:
    """Create a new trace context.

    Args:
        operation_name: Name of the root operation
        trace_id: Optional trace ID (generates one if not provided)

    Returns:
        TraceContext instance

    Example:
        trace = create_trace("my_pipeline")
        with trace.span("step_1"):
            # Execute step
            pass
        trace.end()
    """
    if not trace_id:
        trace_id = str(uuid.uuid4())

    return TraceContext(trace_id, operation_name)

"""Runtime Hardening Demo

This script demonstrates the runtime hardening features:
- Structured logging with trace IDs
- Error envelopes with PipelineResult
- Metrics collection

Run this to see the functionality in action.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Never

from sibyl.runtime.pipeline.metrics import RuntimeMetricsCollector
from sibyl.runtime.pipeline.result import PipelineError, PipelineResult

# Configure logging to show structured data
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def demo_pipeline_result() -> None:
    """Demonstrate PipelineResult envelope."""

    # Success result
    success_result = PipelineResult.success(
        data={
            "pipeline_name": "web_research_pipeline",
            "query": "What is Sibyl?",
            "last_result": {
                "answer": "Sibyl is an AI framework",
                "sources": ["doc1", "doc2"],
            },
        },
        trace_id="abc-123-def-456",
        duration_ms=1234.56,
    )

    # Error result
    error = PipelineError(
        type="ValidationError",
        message="Invalid pipeline configuration",
        details={
            "pipeline_name": "invalid_pipeline",
            "error_field": "steps",
            "reason": "No steps defined",
        },
    )

    PipelineResult.error(
        error=error,
        trace_id="xyz-789-uvw-012",
        duration_ms=123.45,
    )

    # Timeout result
    timeout_error = PipelineError(
        type="TimeoutError",
        message="Pipeline execution exceeded time limit",
        details={
            "pipeline_name": "slow_pipeline",
            "timeout_s": 30,
            "elapsed_s": 31.2,
        },
    )

    PipelineResult.error(
        error=timeout_error,
        trace_id="timeout-111-222-333",
        duration_ms=31200.0,
    )

    # Serialization
    success_result.to_dict()


def demo_metrics_collection() -> None:
    """Demonstrate metrics collection."""

    collector = RuntimeMetricsCollector()
    collector.reset_counters()

    # Simulate pipeline runs
    for i in range(5):
        collector.record_pipeline_run(
            pipeline_name="web_research_pipeline",
            status="success",
            duration_ms=1000 + i * 100,
            trace_id=f"trace-{i}",
            workspace_name="production",
        )

    # Simulate errors
    for i in range(2):
        collector.record_pipeline_run(
            pipeline_name="web_research_pipeline",
            status="error",
            duration_ms=500 + i * 50,
            trace_id=f"error-trace-{i}",
            workspace_name="production",
        )

    # Simulate step executions
    for i in range(3):
        collector.record_step_execution(
            pipeline_name="web_research_pipeline",
            step_name="rag_shop.chunker",
            shop_name="rag_shop",
            duration_ms=200 + i * 20,
            status="success",
            trace_id=f"trace-{i}",
        )

    # Show counters
    counters = collector.get_counters()
    for _key, _value in sorted(counters.items()):
        pass


def demo_error_from_exception() -> None:
    """Demonstrate error creation from exceptions."""

    # Simulate a technique execution error
    def failing_technique() -> Never:
        msg = "Invalid input: query cannot be empty"
        raise ValueError(msg)

    # Create an exception and convert to PipelineError
    try:
        failing_technique()
    except ValueError as e:
        PipelineError.from_exception(
            e,
            error_type="TechniqueError",
            details={
                "technique": "chunker",
                "shop": "rag_shop",
                "input_data": "",
            },
        )


def demo_trace_id_usage() -> None:
    """Demonstrate trace ID usage for log correlation."""

    # Create a result with trace ID

    # Simulate logging at different levels
    logging.getLogger("sibyl.runtime")

    # These logs would normally be emitted by the runtime


def main() -> None:
    """Run all demos."""

    demo_pipeline_result()
    demo_metrics_collection()
    demo_error_from_exception()
    demo_trace_id_usage()


if __name__ == "__main__":
    main()

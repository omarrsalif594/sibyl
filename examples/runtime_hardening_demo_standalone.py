"""Runtime Hardening Demo (Standalone)

This script demonstrates the runtime hardening features without
importing the full framework (to avoid circular import issues).

Run: python examples/runtime_hardening_demo_standalone.py
"""

import importlib.util
from typing import Never


def load_module(name, filepath: Any) -> Any:
    """Load a module directly from filepath."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load modules directly
result_mod = load_module("result", "sibyl/framework/runtime/result.py")
metrics_mod = load_module("metrics", "sibyl/framework/runtime/metrics.py")

PipelineResult = result_mod.PipelineResult
PipelineError = result_mod.PipelineError
PipelineStatus = result_mod.PipelineStatus
RuntimeMetricsCollector = metrics_mod.RuntimeMetricsCollector


def demo_pipeline_result() -> None:
    """Demonstrate PipelineResult envelope."""

    # Success result
    PipelineResult.success(
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


def main() -> None:
    """Run all demos."""

    demo_pipeline_result()
    demo_metrics_collection()
    demo_error_from_exception()


if __name__ == "__main__":
    main()

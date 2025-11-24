#!/usr/bin/env python3
"""Observability demonstration script.

This script demonstrates the observability features implemented in TRACK-P4.
It simulates a pipeline execution and shows all observability data.

Usage:
    python examples/observability_demo.py
"""

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def import_module_from_path(module_name: str, file_path: str) -> Any:
    """Import a module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Import modules directly to avoid circular imports
base_path = Path(__file__).parent.parent

result_module = import_module_from_path(
    "sibyl.runtime.pipeline.result", str(base_path / "sibyl" / "runtime" / "pipeline" / "result.py")
)

pricing_module = import_module_from_path(
    "sibyl.runtime.pipeline.pricing",
    str(base_path / "sibyl" / "runtime" / "pipeline" / "pricing.py"),
)

observability_module = import_module_from_path(
    "sibyl.runtime.pipeline.observability",
    str(base_path / "sibyl" / "runtime" / "pipeline" / "observability.py"),
)

# Extract classes and functions
TokenUsage = result_module.TokenUsage
StepResult = result_module.StepResult
PipelineResult = result_module.PipelineResult
PipelineStatus = result_module.PipelineStatus

estimate_cost = pricing_module.estimate_cost
get_model_pricing = pricing_module.get_model_pricing
get_all_model_pricing = pricing_module.get_all_model_pricing

PipelineObserver = observability_module.PipelineObserver


def print_header(title: str) -> None:
    """Print a formatted header."""


def print_section(title: str) -> None:
    """Print a formatted section."""


def demo_token_usage() -> None:
    """Demonstrate TokenUsage tracking."""
    print_section("1. Token Usage Tracking")

    # Create token usage for steps
    step1_tokens = TokenUsage(prompt_tokens=500, completion_tokens=250, total_tokens=750)
    step2_tokens = TokenUsage(prompt_tokens=1000, completion_tokens=400, total_tokens=1400)

    # Aggregate tokens
    step1_tokens + step2_tokens


def demo_pricing() -> None:
    """Demonstrate pricing and cost estimation."""
    print_section("2. Pricing and Cost Estimation")

    # Show available models
    pricing_table = get_all_model_pricing()

    for model in ["gpt-4", "gpt-3.5-turbo", "claude-sonnet-4-5-20250929", "text-embedding-3-small"]:
        pricing = pricing_table.get(model)
        if pricing:
            pass

    # Estimate costs

    scenarios = [
        ("gpt-4", 1000, 500, "Small GPT-4 request"),
        ("gpt-4", 10000, 2000, "Large GPT-4 request"),
        ("gpt-3.5-turbo", 10000, 2000, "Large GPT-3.5 request"),
        ("claude-sonnet-4-5-20250929", 5000, 1500, "Claude Sonnet request"),
    ]

    for model, prompt_tokens, completion_tokens, _description in scenarios:
        estimate_cost(model, prompt_tokens, completion_tokens)


def demo_pipeline_observer() -> Any:
    """Demonstrate PipelineObserver usage."""
    print_section("3. Pipeline Observer in Action")

    # Create observer
    observer = PipelineObserver(pipeline_name="web_research_demo")
    observer.set_model("gpt-4")

    # Simulate step 1: Query processing
    with observer.track_step(
        "web_research_shop.query_processor", "web_research_shop", "query_processor"
    ) as step:
        # Simulate work
        import time  # noqa: PLC0415

        time.sleep(0.1)
        step.record_tokens(prompt_tokens=150, completion_tokens=50)

    # Simulate step 2: Document retrieval
    with observer.track_step(
        "web_research_shop.retriever", "web_research_shop", "retriever"
    ) as step:
        # Simulate work
        time.sleep(0.15)
        step.record_tokens(prompt_tokens=500, completion_tokens=200)

    # Simulate step 3: Context augmentation
    with observer.track_step(
        "web_research_shop.augmenter", "web_research_shop", "augmenter"
    ) as step:
        # Simulate work
        time.sleep(0.08)
        step.record_tokens(prompt_tokens=1500, completion_tokens=0)

    # Simulate step 4: Response generation
    with observer.track_step(
        "web_research_shop.generator", "web_research_shop", "generator"
    ) as step:
        # Simulate work
        time.sleep(0.2)
        step.record_tokens(prompt_tokens=2000, completion_tokens=800)

    # Simulate step 5: Quality validation
    with observer.track_step(
        "web_research_shop.validator", "web_research_shop", "validator"
    ) as step:
        # Simulate work
        time.sleep(0.05)
        step.record_tokens(prompt_tokens=100, completion_tokens=20)

    # Build final result
    return observer.build_result(
        ok=True,
        data={
            "output": "This is a comprehensive response to the research query...",
            "citations": ["source1.com", "source2.com"],
            "confidence": 0.95,
        },
    )


def demo_pipeline_result(result: PipelineResult) -> None:
    """Demonstrate PipelineResult observability."""
    print_section("4. Pipeline Result Observability")

    if result.tokens:
        pass

    if result.estimated_cost_usd:
        pass

    for _i, step in enumerate(result.step_results, 1):
        if step.tokens:
            pass


def demo_metrics_access() -> None:
    """Demonstrate metrics access."""
    print_section("5. Metrics Access")

    try:
        # Import metrics module
        metrics_module = import_module_from_path(
            "sibyl.runtime.pipeline.metrics",
            str(Path(__file__).parent.parent / "sibyl" / "runtime" / "pipeline" / "metrics.py"),
        )

        collector = metrics_module.get_metrics_collector()
        counters = collector.get_counters()

        if not counters:
            pass
        else:
            for _key, _value in sorted(counters.items()):
                pass

    except Exception:
        logging.debug("Failed to access metrics - feature may not be available")


def main() -> None:
    """Run the observability demonstration."""
    print_header("SIBYL OBSERVABILITY DEMONSTRATION (TRACK-P4)")

    # Run demos
    demo_token_usage()
    demo_pricing()
    result = demo_pipeline_observer()
    demo_pipeline_result(result)
    demo_metrics_access()

    # Final summary
    print_header("DEMONSTRATION COMPLETE")


if __name__ == "__main__":
    main()

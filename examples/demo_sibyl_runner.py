#!/usr/bin/env python3
"""
Demo script showing how to use the Sibyl Runner plugin foundation.

This demonstrates the canonical way for external tools (Opencode, Claude Code,
SDKs, etc.) to execute Sibyl pipelines.

Run:
    python examples/demo_sibyl_runner.py
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from plugins.common.sibyl_runner import run_pipeline, validate_pipeline_result

# Path to example workspace
PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE_PATH = (
    PROJECT_ROOT / "examples" / "companies" / "northwind_analytics" / "config" / "workspace.yaml"
)


def demo_basic_usage() -> None:
    """Demo 1: Basic pipeline execution."""

    result = run_pipeline(
        workspace_path=str(WORKSPACE_PATH),
        pipeline_name="explain_dashboard",
        params={"dashboard_name": "Revenue Overview", "audience": "new product manager"},
    )

    if result["status"] == "success":
        pass
    else:
        pass


def demo_error_handling() -> None:
    """Demo 2: Error handling with missing workspace."""

    run_pipeline(workspace_path="/nonexistent/workspace.yaml", pipeline_name="any_pipeline")


def demo_result_validation() -> None:
    """Demo 3: Result validation."""

    result = run_pipeline(
        workspace_path=str(WORKSPACE_PATH),
        pipeline_name="explain_dashboard",
        params={"dashboard_name": "Customer Health Dashboard"},
    )

    validate_pipeline_result(result)

    if result["status"] == "success":
        pass
    else:
        pass


def demo_multiple_pipelines() -> None:
    """Demo 4: Running multiple pipelines sequentially."""

    pipelines = [
        ("explain_dashboard", {"dashboard_name": "Revenue Overview"}),
        (
            "generate_release_notes",
            {
                "version": "v2.1.0",
                "release_date": "2024-10-15",
                "feature_keywords": ["alerts", "anomaly detection"],
            },
        ),
    ]

    results = []
    for pipeline_name, params in pipelines:
        result = run_pipeline(
            workspace_path=str(WORKSPACE_PATH), pipeline_name=pipeline_name, params=params
        )
        results.append(result)

    sum(1 for r in results if r["status"] == "success")


def main() -> None:
    """Run all demos."""

    # Run demos
    demo_basic_usage()
    demo_error_handling()
    demo_result_validation()
    demo_multiple_pipelines()


if __name__ == "__main__":
    main()

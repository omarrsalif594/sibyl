#!/usr/bin/env python3
"""
Demo: Using sibyl_runner to execute pipelines from external tools

This script demonstrates how external plugins, SDKs, and tools should use
the sibyl_runner API to execute Sibyl pipelines.

Run from project root:
    python examples/plugins/demo_sibyl_runner.py
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    """Demonstrate sibyl_runner usage patterns."""

    # Import sibyl_runner
    try:
        from plugins.common.sibyl_runner import (  # noqa: PLC0415 - optional dependency
            run_pipeline,
            validate_pipeline_result,
        )

    except ImportError:
        return 1

    # Example workspaces
    northwind_workspace = (
        PROJECT_ROOT / "examples/companies/northwind_analytics/config/workspace.yaml"
    )

    if not northwind_workspace.exists():
        return 1

    # Example 1: Simple pipeline execution

    result = run_pipeline(
        workspace_path=str(northwind_workspace),
        pipeline_name="explain_dashboard",
        params={"dashboard_name": "Revenue Overview", "audience": "new product manager"},
    )

    if result["status"] == "success":
        pass
    else:
        pass

    # Example 2: Error handling

    result = run_pipeline(
        workspace_path="/nonexistent/workspace.yaml", pipeline_name="any_pipeline"
    )

    assert result["status"] == "error", "Should return error status"
    assert "not found" in result["error"].lower(), "Should mention file not found"

    # Example 3: Result validation

    # Create sample results

    # Example 4: Multiple pipelines

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

    for _i, (pipeline_name, params) in enumerate(pipelines, 1):
        result = run_pipeline(
            workspace_path=str(northwind_workspace), pipeline_name=pipeline_name, params=params
        )

    # Summary

    return 0


if __name__ == "__main__":
    sys.exit(main())

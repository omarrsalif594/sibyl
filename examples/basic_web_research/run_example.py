#!/usr/bin/env python3
"""Basic web research example using Sibyl.

This script demonstrates:
- Loading a workspace configuration
- Building providers from workspace
- Creating and using a workspace runtime
- Running a pipeline programmatically
- Handling results (success and error cases)
- Accessing trace IDs for debugging

Usage:
    # Run with default settings
    python run_example.py

    # Run with custom workspace
    python run_example.py --workspace /path/to/workspace.yaml

    # Run with custom parameters
    python run_example.py --param query="What is Python?" --param top_k=10

    # Run with verbose output
    python run_example.py --verbose
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sibyl.config.workspace_loader import WorkspaceLoadError, load_workspace
from sibyl.runtime import PipelineResult, WorkspaceRuntime, build_providers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def print_header(title: str) -> None:
    """Print a formatted header."""


def print_section(title: str) -> None:
    """Print a formatted section header."""


async def run_research_pipeline(
    workspace_path: str,
    pipeline_name: str = "simple_search",
    params: dict[str, Any] | None = None,
    verbose: bool = False,
) -> int:
    """Run a research pipeline and display results.

    Args:
        workspace_path: Path to workspace YAML file
        pipeline_name: Name of pipeline to execute
        params: Pipeline parameters
        verbose: Enable verbose output

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if params is None:
        params = {}

    # Set default query if not provided
    if "query" not in params:
        params["query"] = "What is Sibyl AI orchestration?"

    print_header("Sibyl Basic Web Research Example")

    try:
        # Step 1: Load workspace configuration
        workspace = load_workspace(workspace_path)

        if verbose:
            pass

        # Step 2: Build providers
        providers = build_providers(workspace)

        len(providers._providers)

        # Step 3: Initialize workspace runtime
        runtime = WorkspaceRuntime(workspace, providers)

        len(runtime.shops)

        # Step 4: Run pipeline

        print_section("Pipeline Execution")

        result: PipelineResult = await runtime.run_pipeline_v2(pipeline_name, **params)

        # Step 5: Handle results
        if result.ok:
            # Success path

            # Display main results
            if "last_result" in result.data:
                last_result = result.data["last_result"]

                if isinstance(last_result, str):
                    # Print string results with indentation
                    for _line in last_result.split("\n"):
                        pass
                elif isinstance(last_result, (dict, list)):
                    # Print JSON results
                    pass
                else:
                    pass

            # Display additional context (if verbose)
            if verbose:
                exclude_keys = {
                    "pipeline_name",
                    "pipeline_shop",
                    "last_result",
                    "success",
                }
                other_data = {k: v for k, v in result.data.items() if k not in exclude_keys}

                if other_data:
                    pass

            # Display metrics
            if result.metrics and verbose:
                pass

            print_header("Example completed successfully!")
            return 0

        # Error path

        # Display error details (if available)
        if result.error.details:
            # Filter out sensitive information
            {k: v for k, v in result.error.details.items() if k not in {"stack_trace", "exception"}}

        # Show stack trace in verbose mode
        if verbose and "stack_trace" in result.error.details:
            pass

        return 1

    except WorkspaceLoadError:
        return 1

    except Exception:
        if verbose:
            logger.exception("Unexpected error during example execution")
        return 1


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Sibyl Basic Web Research Example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings
  python run_example.py

  # Run with custom workspace
  python run_example.py --workspace /path/to/workspace.yaml

  # Run with custom parameters
  python run_example.py --param query="What is Python?"

  # Run with verbose output
  python run_example.py --verbose
        """,
    )

    parser.add_argument(
        "--workspace",
        "-w",
        default="example_workspace.yaml",
        help="Path to workspace YAML file (default: example_workspace.yaml)",
    )

    parser.add_argument(
        "--pipeline",
        "-p",
        default="simple_search",
        help="Pipeline name to execute (default: simple_search)",
    )

    parser.add_argument(
        "--param",
        action="append",
        help="Pipeline parameter in format key=value (can be used multiple times)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Parse parameters
    params = {}
    if args.param:
        for param in args.param:
            if "=" not in param:
                return 1

            key, value = param.split("=", 1)

            # Try to parse as JSON for complex values
            try:
                params[key] = json.loads(value)
            except json.JSONDecodeError:
                # If not JSON, use as string
                params[key] = value

    # Run the example
    return asyncio.run(
        run_research_pipeline(
            workspace_path=args.workspace,
            pipeline_name=args.pipeline,
            params=params,
            verbose=args.verbose,
        )
    )


if __name__ == "__main__":
    sys.exit(main())

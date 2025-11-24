#!/usr/bin/env python3
"""Golden Path: Web Research Pipeline Example

This is THE reference implementation for using Sibyl. It demonstrates:
- Loading the production workspace configuration
- Building providers from the workspace
- Creating and using the WorkspaceRuntime
- Running both flagship pipelines (web_research and summarize_url)
- Proper error handling and result processing
- Observability with trace IDs

This example uses config/workspaces/prod_web_research.yaml - the flagship
workspace configuration that serves as the template for all Sibyl deployments.

Usage:
    # Run with default examples
    python run_web_research.py

    # Run specific pipeline
    python run_web_research.py --pipeline web_research --query "What is RAG?"

    # Run with custom workspace
    python run_web_research.py --workspace /path/to/workspace.yaml

    # Run with verbose logging
    python run_web_research.py --verbose
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

from sibyl.runtime.pipeline.workspace_runtime import WorkspaceRuntime
from sibyl.runtime.providers.registry import build_providers
from sibyl.workspace.loader import WorkspaceLoadError, load_workspace

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


async def run_web_research_example(
    workspace_path: str,
    verbose: bool = False,
) -> int:
    """Run the web research pipeline example.

    Args:
        workspace_path: Path to workspace YAML file
        verbose: Enable verbose output

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print_header("Sibyl Golden Path: Web Research")

    try:
        # Step 1: Load workspace configuration
        print_section("Step 1: Load Workspace Configuration")

        workspace = load_workspace(workspace_path)

        if verbose:
            for _shop_name in workspace.shops:
                pass
            for _pipeline_name in workspace.pipelines:
                pass

        # Step 2: Build providers
        print_section("Step 2: Build Providers")

        providers = build_providers(workspace)

        providers.list_providers()

        # Step 3: Create workspace runtime
        print_section("Step 3: Initialize Workspace Runtime")

        runtime = WorkspaceRuntime(workspace, providers)

        # Step 4: Run web_research pipeline
        print_section("Step 4: Execute 'web_research' Pipeline")

        query = "What is Retrieval Augmented Generation (RAG) in AI?"

        try:
            result = await runtime.run_pipeline(
                "web_research", query=query, top_k=10, include_citations=True
            )

            if result.get("success"):
                if "last_result" in result:
                    response = result["last_result"]
                    if isinstance(response, str):
                        pass
                    else:
                        pass

                if verbose:
                    pass

            else:
                return 1

        except Exception:
            if verbose:
                logger.exception("Detailed error:")
            return 1

        # Step 5: Run summarize_url pipeline
        print_section("Step 5: Execute 'summarize_url' Pipeline")

        # For demo purposes, we'll simulate a URL input
        # In production, this would fetch actual URL content
        demo_url = "https://example.com/article"

        try:
            result = await runtime.run_pipeline("summarize_url", url=demo_url, max_length=500)

            if result.get("success"):
                if "last_result" in result:
                    summary = result["last_result"]
                    if isinstance(summary, str):
                        pass
                    else:
                        pass

                if verbose:
                    pass

            else:
                return 1

        except Exception:
            if verbose:
                logger.exception("Detailed error:")
            return 1

        # Success!
        print_header("Golden Path Example Completed Successfully!")

        return 0

    except WorkspaceLoadError:
        return 1

    except Exception:
        if verbose:
            logger.exception("Detailed error:")
        return 1


async def run_single_pipeline(
    workspace_path: str,
    pipeline_name: str,
    params: dict[str, Any],
    verbose: bool = False,
) -> int:
    """Run a single pipeline with custom parameters.

    Args:
        workspace_path: Path to workspace YAML file
        pipeline_name: Name of pipeline to execute
        params: Pipeline parameters
        verbose: Enable verbose output

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print_header(f"Running Pipeline: {pipeline_name}")

    try:
        # Load workspace
        workspace = load_workspace(workspace_path)

        # Build providers
        providers = build_providers(workspace)

        # Create runtime
        runtime = WorkspaceRuntime(workspace, providers)

        # Run pipeline

        result = await runtime.run_pipeline(pipeline_name, **params)

        if result.get("success"):
            if "last_result" in result:
                output = result["last_result"]
                if isinstance(output, str):
                    pass
                else:
                    pass

            if verbose:
                pass

            return 0

        return 1

    except Exception:
        if verbose:
            logger.exception("Detailed error:")
        return 1


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Sibyl Golden Path: Web Research Example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full golden path demo
  python run_web_research.py

  # Run specific pipeline
  python run_web_research.py --pipeline web_research --query "What is AI?"

  # Run with custom workspace
  python run_web_research.py --workspace /path/to/workspace.yaml

  # Run with verbose output
  python run_web_research.py --verbose
        """,
    )

    parser.add_argument(
        "--workspace",
        "-w",
        default="../../config/workspaces/prod_web_research.yaml",
        help="Path to workspace YAML file",
    )

    parser.add_argument(
        "--pipeline",
        "-p",
        help="Specific pipeline to run (default: run both demo pipelines)",
    )

    parser.add_argument(
        "--query",
        help="Query for web_research pipeline",
    )

    parser.add_argument(
        "--url",
        help="URL for summarize_url pipeline",
    )

    parser.add_argument(
        "--param",
        action="append",
        help="Additional pipeline parameter (format: key=value)",
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

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Resolve workspace path
    workspace_path = Path(args.workspace)
    if not workspace_path.is_absolute():
        workspace_path = Path(__file__).parent / workspace_path
    workspace_path = workspace_path.resolve()

    # Parse additional parameters
    params = {}
    if args.param:
        for param in args.param:
            if "=" not in param:
                return 1
            key, value = param.split("=", 1)
            try:
                params[key] = json.loads(value)
            except json.JSONDecodeError:
                params[key] = value

    # Run specific pipeline or full demo
    if args.pipeline:
        # Build parameters based on pipeline
        if args.pipeline == "web_research":
            params["query"] = args.query or "What is Retrieval Augmented Generation?"
        elif args.pipeline == "summarize_url":
            params["url"] = args.url or "https://example.com"

        return asyncio.run(
            run_single_pipeline(
                str(workspace_path),
                args.pipeline,
                params,
                args.verbose,
            )
        )
    # Run full golden path demo
    return asyncio.run(
        run_web_research_example(
            str(workspace_path),
            args.verbose,
        )
    )


if __name__ == "__main__":
    sys.exit(main())

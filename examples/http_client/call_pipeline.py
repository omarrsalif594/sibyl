#!/usr/bin/env python3
"""Example script for calling Sibyl pipelines via HTTP API.

This demonstrates how to use the HTTP API to execute pipelines programmatically
using the Python requests library.

Usage:
    python call_pipeline.py

Prerequisites:
    pip install requests

Note:
    Make sure the HTTP server is running:
    sibyl http serve --workspace config/workspaces/example.yaml --port 8000
"""

import sys
from typing import Any

import requests

# API configuration
API_BASE_URL = "http://localhost:8000"
API_TIMEOUT = 60  # seconds


def list_pipelines() -> dict[str, Any]:
    """List all available pipelines.

    Returns:
        Response containing pipeline names
    """
    url = f"{API_BASE_URL}/pipelines"

    response = requests.get(url, timeout=API_TIMEOUT)
    response.raise_for_status()

    return response.json()


def get_pipeline_info(pipeline_name: str) -> dict[str, Any]:
    """Get information about a specific pipeline.

    Args:
        pipeline_name: Name of the pipeline

    Returns:
        Pipeline metadata
    """
    url = f"{API_BASE_URL}/pipelines/{pipeline_name}"

    response = requests.get(url, timeout=API_TIMEOUT)
    response.raise_for_status()

    return response.json()


def execute_pipeline(pipeline_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Execute a pipeline with parameters.

    Args:
        pipeline_name: Name of the pipeline to execute
        params: Pipeline parameters

    Returns:
        Pipeline execution result
    """
    url = f"{API_BASE_URL}/pipelines/{pipeline_name}"

    response = requests.post(url, json={"params": params}, timeout=API_TIMEOUT)

    # Handle different status codes
    if response.status_code == 200:  # noqa: PLR2004
        return response.json()
    if response.status_code in {400, 404}:
        sys.exit(1)
    elif response.status_code == 500:  # noqa: PLR2004
        response.json()
        sys.exit(1)
    elif response.status_code == 504:  # noqa: PLR2004
        sys.exit(1)
    else:
        response.raise_for_status()
    return None


def check_health() -> dict[str, Any]:
    """Check workspace health status.

    Returns:
        Health check response
    """
    url = f"{API_BASE_URL}/health/workspace"

    response = requests.get(url, timeout=5)
    response.raise_for_status()

    return response.json()


def main() -> None:
    """Main example demonstrating HTTP API usage."""
    try:
        # Check health
        check_health()

        # List pipelines
        pipelines_response = list_pipelines()

        if not pipelines_response.get("pipelines"):
            return

        # Get info about first pipeline
        pipeline_name = pipelines_response["pipelines"][0]
        get_pipeline_info(pipeline_name)

        # Example 1: Execute web_research pipeline (if available)
        if "web_research" in pipelines_response["pipelines"]:
            execute_pipeline(
                pipeline_name="web_research",
                params={"query": "What is artificial intelligence?", "top_k": 5},
            )

        # Example 2: Execute summarize_url pipeline (if available)
        if "summarize_url" in pipelines_response["pipelines"]:
            execute_pipeline(
                pipeline_name="summarize_url",
                params={
                    "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
                    "max_length": 200,
                },
            )

    except requests.exceptions.ConnectionError:
        sys.exit(1)
    except requests.exceptions.Timeout:
        sys.exit(1)
    except requests.exceptions.HTTPError:
        sys.exit(1)
    except Exception:
        import traceback  # noqa: PLC0415 - can be moved to top

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

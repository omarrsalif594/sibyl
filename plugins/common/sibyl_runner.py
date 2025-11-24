"""
Sibyl Runner - Core plugin foundation.

This module provides the foundational functionality for running Sibyl pipelines
from external integrations. It serves as the bridge between external tools
(like Opencode, CLI commands, etc.) and the Sibyl workspace runtime.

Key Features:
- Load workspace configuration from YAML files
- Execute pipelines with typed parameters
- Handle errors gracefully with clear messaging
- Support both sync and async execution patterns
- Provide structured results for external consumption

Example:
    >>> from plugins.common.sibyl_runner import run_pipeline
    >>> result = run_pipeline(
    ...     workspace_path="examples/companies/northwind_analytics/config/workspace.yaml",
    ...     pipeline_name="revenue_analysis",
    ...     params={"question": "Why is revenue down?"}
    ... )
    >>> print(result["status"])  # "success"
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PipelineExecutionError(Exception):
    """Raised when pipeline execution fails."""


class WorkspaceLoadError(Exception):
    """Raised when workspace configuration cannot be loaded."""


def run_pipeline(
    workspace_path: str | Path,
    pipeline_name: str,
    params: dict[str, Any] | None = None,
    timeout: int | None = 300,
) -> dict[str, Any]:
    """
    Execute a Sibyl pipeline synchronously.

    This is the main entry point for external integrations to run Sibyl pipelines.
    It handles workspace loading, pipeline execution, and error handling.

    Args:
        workspace_path: Path to the workspace YAML configuration file
        pipeline_name: Name of the pipeline to execute (as defined in pipelines.yaml)
        params: Dictionary of pipeline parameters (optional)
        timeout: Maximum execution time in seconds (default: 300)

    Returns:
        Dictionary with execution results:
        {
            "status": "success" | "error",
            "pipeline": str,
            "workspace": str,
            "result": Any,  # Pipeline output (only on success)
            "error": str,   # Error message (only on error)
            "duration_ms": int
        }

    Raises:
        WorkspaceLoadError: If workspace cannot be loaded
        PipelineExecutionError: If pipeline execution fails

    Example:
        >>> result = run_pipeline(
        ...     workspace_path="examples/companies/northwind_analytics/config/workspace.yaml",
        ...     pipeline_name="revenue_analysis",
        ...     params={"question": "Why is revenue down in Q3?", "time_period": "2024-Q3"}
        ... )
        >>> if result["status"] == "success":
        ...     print(result["result"])
    """
    import time  # noqa: PLC0415

    start_time = time.time()

    params = params or {}
    workspace_path = Path(workspace_path)

    logger.info("Running pipeline '%s' from workspace '%s'", pipeline_name, workspace_path)

    # Check file existence before trying to import/load
    if not workspace_path.exists():
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Workspace file not found: {workspace_path}"
        logger.error(error_msg)
        return {
            "status": "error",
            "pipeline": pipeline_name,
            "workspace": str(workspace_path),
            "error": error_msg,
            "duration_ms": duration_ms,
        }

    try:
        # Import here to avoid circular imports
        from sibyl.runtime.convenience import load_workspace_runtime  # noqa: PLC0415

        # Load workspace and create runtime
        runtime = load_workspace_runtime(workspace_path)

        # Execute pipeline asynchronously
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, create a new loop
            import concurrent.futures  # noqa: PLC0415

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    _run_async_pipeline, runtime, pipeline_name, params, timeout
                )
                pipeline_result = future.result()
        else:
            # Use the existing event loop
            pipeline_result = loop.run_until_complete(
                _run_pipeline_with_timeout(runtime, pipeline_name, params, timeout)
            )

        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "status": "success",
            "pipeline": pipeline_name,
            "workspace": str(workspace_path),
            "result": pipeline_result,
            "duration_ms": duration_ms,
        }

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Pipeline execution failed: {e!s}"
        logger.exception(error_msg)
        return {
            "status": "error",
            "pipeline": pipeline_name,
            "workspace": str(workspace_path),
            "error": error_msg,
            "duration_ms": duration_ms,
        }


def _run_async_pipeline(runtime, pipeline_name: Any, params: Any, timeout: Any) -> Any:
    """Helper to run async pipeline in a new event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            _run_pipeline_with_timeout(runtime, pipeline_name, params, timeout)
        )
    finally:
        loop.close()


async def _run_pipeline_with_timeout(runtime, pipeline_name: Any, params: Any, timeout: Any) -> Any:
    """Execute pipeline with timeout."""
    try:
        return await asyncio.wait_for(
            runtime.run_pipeline(pipeline_name, **params), timeout=timeout
        )
    except TimeoutError:
        msg = f"Pipeline '{pipeline_name}' timed out after {timeout}s"
        raise PipelineExecutionError(msg) from None


def load_pipeline_config(config_path: str | Path) -> dict[str, Any]:
    """
    Load a YAML configuration file (workspace or mapping config).

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Dictionary with parsed configuration

    Raises:
        WorkspaceLoadError: If configuration cannot be loaded

    Example:
        >>> config = load_pipeline_config("plugins/opencode/opencode_sibyl_example.yaml")
        >>> print(config["commands"].keys())
    """
    import yaml  # noqa: PLC0415

    config_path = Path(config_path)

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        logger.info("Loaded configuration from %s", config_path)
        return config
    except FileNotFoundError:
        msg = f"Configuration file not found: {config_path}"
        raise WorkspaceLoadError(msg) from None
    except yaml.YAMLError as e:
        msg = f"Invalid YAML in {config_path}: {e}"
        raise WorkspaceLoadError(msg) from None
    except Exception as e:
        msg = f"Failed to load {config_path}: {e}"
        raise WorkspaceLoadError(msg) from e


def validate_pipeline_result(result: dict[str, Any]) -> bool:
    """
    Validate that a pipeline result has the expected structure.

    Args:
        result: Result dictionary from run_pipeline()

    Returns:
        True if valid, False otherwise

    Example:
        >>> result = run_pipeline(...)
        >>> if validate_pipeline_result(result):
        ...     print("Pipeline executed successfully")
    """
    if not isinstance(result, dict):
        return False

    required_keys = {"status", "pipeline", "workspace", "duration_ms"}
    if not required_keys.issubset(result.keys()):
        return False

    if result["status"] not in ("success", "error"):
        return False

    if result["status"] == "success" and "result" not in result:
        return False

    return not (result["status"] == "error" and "error" not in result)


__all__ = [
    "PipelineExecutionError",
    "WorkspaceLoadError",
    "load_pipeline_config",
    "run_pipeline",
    "validate_pipeline_result",
]

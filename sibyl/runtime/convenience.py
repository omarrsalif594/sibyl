"""
Convenience API for Sibyl workspace runtime.

This module provides a simplified API for creating and running Sibyl workspaces
without requiring manual provider setup or configuration loading.

Example:
    from sibyl.runtime import load_workspace_runtime

    # One-line workspace setup
    runtime = load_workspace_runtime("config/workspaces/example_local.yaml")

    # Execute pipeline
    result = await runtime.run_pipeline("web_research_pipeline", query="What is Sibyl?")

This is equivalent to:
    from sibyl.workspace import load_workspace
    from sibyl.runtime import build_providers, WorkspaceRuntime

    workspace = load_workspace("config/workspaces/example_local.yaml")
    providers = build_providers(workspace)
    runtime = WorkspaceRuntime(workspace, providers)
"""

from pathlib import Path

from sibyl.runtime.pipeline.workspace_runtime import WorkspaceRuntime
from sibyl.runtime.providers.registry import build_providers
from sibyl.workspace import load_workspace


def load_workspace_runtime(path: str | Path) -> WorkspaceRuntime:
    """
    Load a workspace configuration and create a ready-to-use runtime.

    This convenience function combines workspace loading, provider building,
    and runtime creation into a single call.

    Args:
        path: Path to the workspace YAML configuration file

    Returns:
        WorkspaceRuntime instance ready to execute pipelines

    Raises:
        WorkspaceLoadError: If the workspace configuration is invalid
        ProviderBuildError: If provider initialization fails

    Example:
        >>> from sibyl.runtime import load_workspace_runtime
        >>> runtime = load_workspace_runtime("config/workspaces/example_local.yaml")
        >>> result = await runtime.run_pipeline("my_pipeline", query="test")
    """
    workspace = load_workspace(path)
    providers = build_providers(workspace)
    return WorkspaceRuntime(workspace, providers)


__all__ = [
    "load_workspace_runtime",
]

"""
Sibyl runtime: the execution brain.

This module provides the STABLE PUBLIC API for executing Sibyl pipelines,
including workspace management, provider registry, and workflow orchestration.

The runtime is the "brain" of Sibyl that:
- Manages pipeline execution
- Coordinates providers (LLM, embeddings, vector store, MCP)
- Tracks metrics and results
- Orchestrates workflows

Stability: STABLE - This is part of the public API with semantic versioning guarantees.
Breaking changes will only occur in major version releases.

Example:
    from sibyl.runtime import WorkspaceRuntime, build_providers
    from sibyl.workspace import load_workspace

    # Load workspace and create runtime
    workspace = load_workspace("config/workspaces/example.yaml")
    providers = build_providers(workspace)
    runtime = WorkspaceRuntime(workspace, providers)

    # Execute pipeline
    result = await runtime.run_pipeline("my_pipeline", query="test")

    # Handle results
    if result.ok:
        print(f"Success: {result.data}")
    else:
        print(f"Error: {result.error.message}")

Components:
- WorkspaceRuntime: Main execution engine
- PipelineResult, PipelineStatus, PipelineError: Result types
- ProviderRegistry, build_providers: Provider management
- RuntimeMetricsCollector: Metrics collection
"""

# Pipeline execution
# Re-export convenience function
from sibyl.runtime.convenience import load_workspace_runtime
from sibyl.runtime.pipeline.metrics import RuntimeMetricsCollector, get_metrics_collector
from sibyl.runtime.pipeline.result import PipelineError, PipelineResult, PipelineStatus
from sibyl.runtime.pipeline.workspace_runtime import WorkspaceRuntime
from sibyl.runtime.providers.factories import (
    create_embeddings_provider,
    create_llm_provider,
    create_vector_store_provider,
)

# Provider management
from sibyl.runtime.providers.registry import ProviderRegistry, build_providers

__all__ = [
    "PipelineError",
    "PipelineResult",
    "PipelineStatus",
    # Provider management
    "ProviderRegistry",
    "RuntimeMetricsCollector",
    # Pipeline execution
    "WorkspaceRuntime",
    "build_providers",
    "create_embeddings_provider",
    "create_llm_provider",
    "create_vector_store_provider",
    "get_metrics_collector",
    # Convenience
    "load_workspace_runtime",
]

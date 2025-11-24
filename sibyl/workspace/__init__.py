"""
Workspace configuration models and loader.

This module provides the STABLE PUBLIC API for workspace configuration
schema and loading functionality.

Stability: STABLE - This is part of the public API with semantic versioning guarantees.
Breaking changes will only occur in major version releases.

Example:
    from sibyl.workspace import WorkspaceSettings, load_workspace

    # Load workspace from YAML
    workspace = load_workspace("config/workspaces/example.yaml")

    # Access configuration
    llm_config = workspace.providers.llm["default"]

    # Validate workspace without loading
    validate_workspace_file("config/workspaces/example.yaml")

    # Get workspace info
    info = get_workspace_info("config/workspaces/example.yaml")
    print(f"Workspace: {info['name']}, Version: {info['version']}")
"""

from .loader import (
    WorkspaceLoadError,
    get_workspace_info,
    load_workspace,
    load_workspace_dict,
    validate_workspace_file,
)
from .schema import (
    EmbeddingsProviderConfig,
    LLMProviderConfig,
    MCPConfig,
    MCPProviderConfig,
    MCPToolConfig,
    PipelineConfig,
    PipelineStepConfig,
    ProvidersConfig,
    ShopConfig,
    VectorStoreConfig,
    WorkspaceSettings,
)

__all__ = [
    "EmbeddingsProviderConfig",
    "LLMProviderConfig",
    "MCPConfig",
    "MCPProviderConfig",
    "MCPToolConfig",
    "PipelineConfig",
    "PipelineStepConfig",
    "ProvidersConfig",
    "ShopConfig",
    "VectorStoreConfig",
    "WorkspaceLoadError",
    # Schema classes
    "WorkspaceSettings",
    "get_workspace_info",
    # Loader functions
    "load_workspace",
    "load_workspace_dict",
    "validate_workspace_file",
]

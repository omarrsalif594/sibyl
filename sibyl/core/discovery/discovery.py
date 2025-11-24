"""Discovery APIs for exploring workspace capabilities.

This module provides APIs to discover available MCP providers, tools,
artifact types, and other workspace capabilities.

Example:
    from sibyl.core.discovery import WorkspaceDiscovery
    from sibyl.workspace import load_workspace

    workspace = load_workspace("config/workspaces/example.yaml")
    discovery = WorkspaceDiscovery(workspace)

    # List all MCP providers
    providers = discovery.list_mcp_providers()
    for provider in providers:
        print(f"{provider['name']}: {provider['endpoint']}")

    # List tools for a provider
    tools = discovery.list_mcp_tools("my_provider")
    for tool in tools:
        print(f"  {tool['name']}: {tool['description']}")

    # Get artifact types
    artifacts = discovery.list_artifact_types()
"""

import logging
from dataclasses import dataclass
from typing import Any

from sibyl.workspace.schema import WorkspaceSettings

logger = logging.getLogger(__name__)


@dataclass
class ProviderInfo:
    """Information about an MCP provider.

    Attributes:
        name: Provider name
        transport: Transport type (http, stdio)
        endpoint: Provider endpoint or command
        tools: List of available tools
        timeout_s: Timeout in seconds
    """

    name: str
    transport: str
    endpoint: str
    tools: list[str]
    timeout_s: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "transport": self.transport,
            "endpoint": self.endpoint,
            "tools": self.tools,
            "timeout_s": self.timeout_s,
        }


@dataclass
class ToolInfo:
    """Information about an MCP tool.

    Attributes:
        name: Tool name
        provider: Provider name
        description: Tool description
        input_schema: JSON schema for tool inputs
    """

    name: str
    provider: str
    description: str
    input_schema: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "provider": self.provider,
            "description": self.description,
            "input_schema": self.input_schema,
        }


@dataclass
class ShopInfo:
    """Information about a shop.

    Attributes:
        name: Shop name
        techniques: Mapping of logical names to technique references
        config: Shop configuration
    """

    name: str
    techniques: dict[str, str]
    config: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "techniques": self.techniques,
            "config": self.config,
        }


@dataclass
class ArtifactTypeInfo:
    """Information about an artifact type.

    Attributes:
        name: Artifact type name
        module: Module path
        description: Description of the artifact type
        fields: List of field names
    """

    name: str
    module: str
    description: str
    fields: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "module": self.module,
            "description": self.description,
            "fields": self.fields,
        }


class WorkspaceDiscovery:
    """Discovery API for workspace capabilities.

    This class provides methods to explore and discover:
    - Available MCP providers and their tools
    - Shops and techniques
    - Artifact types
    - Pipelines and their capabilities

    Attributes:
        workspace: Workspace configuration
    """

    def __init__(self, workspace: WorkspaceSettings) -> None:
        """Initialize discovery API.

        Args:
            workspace: Workspace configuration
        """
        self.workspace = workspace

    def list_mcp_providers(self) -> list[ProviderInfo]:
        """List all MCP providers in the workspace.

        Returns:
            List of ProviderInfo objects
        """
        providers = []

        for name, config in self.workspace.providers.mcp.items():
            endpoint = config.url if config.transport == "http" else " ".join(config.command)
            providers.append(
                ProviderInfo(
                    name=name,
                    transport=config.transport,
                    endpoint=endpoint,
                    tools=config.tools,
                    timeout_s=config.timeout_s,
                )
            )

        return providers

    def get_mcp_provider(self, provider_name: str) -> ProviderInfo | None:
        """Get information about a specific MCP provider.

        Args:
            provider_name: Name of the provider

        Returns:
            ProviderInfo or None if not found
        """
        if provider_name not in self.workspace.providers.mcp:
            return None

        config = self.workspace.providers.mcp[provider_name]
        endpoint = config.url if config.transport == "http" else " ".join(config.command)

        return ProviderInfo(
            name=provider_name,
            transport=config.transport,
            endpoint=endpoint,
            tools=config.tools,
            timeout_s=config.timeout_s,
        )

    def list_mcp_tools(self, provider_name: str | None = None) -> list[ToolInfo]:
        """List MCP tools, optionally filtered by provider.

        Args:
            provider_name: Optional provider name to filter by

        Returns:
            List of ToolInfo objects
        """
        tools = []

        # If provider specified, only list its tools
        if provider_name:
            if provider_name not in self.workspace.providers.mcp:
                logger.warning("Provider '%s' not found", provider_name)
                return []

            config = self.workspace.providers.mcp[provider_name]
            for tool_name in config.tools:
                tools.append(
                    ToolInfo(
                        name=tool_name,
                        provider=provider_name,
                        description="",  # Would need to query provider for this
                        input_schema=None,
                    )
                )
        else:
            # List all tools from all providers
            for prov_name, config in self.workspace.providers.mcp.items():
                for tool_name in config.tools:
                    tools.append(
                        ToolInfo(
                            name=tool_name,
                            provider=prov_name,
                            description="",
                            input_schema=None,
                        )
                    )

        return tools

    def list_shops(self) -> list[ShopInfo]:
        """List all shops in the workspace.

        Returns:
            List of ShopInfo objects
        """
        shops = []

        for name, config in self.workspace.shops.items():
            shops.append(
                ShopInfo(
                    name=name,
                    techniques=config.techniques,
                    config=config.config,
                )
            )

        return shops

    def get_shop(self, shop_name: str) -> ShopInfo | None:
        """Get information about a specific shop.

        Args:
            shop_name: Name of the shop

        Returns:
            ShopInfo or None if not found
        """
        if shop_name not in self.workspace.shops:
            return None

        config = self.workspace.shops[shop_name]
        return ShopInfo(
            name=shop_name,
            techniques=config.techniques,
            config=config.config,
        )

    def list_pipelines(self) -> list[dict[str, Any]]:
        """List all pipelines in the workspace.

        Returns:
            List of pipeline information dictionaries
        """
        pipelines = []

        for name, config in self.workspace.pipelines.items():
            pipelines.append(
                {
                    "name": name,
                    "shop": config.shop,
                    "description": config.description,
                    "entrypoint": config.entrypoint,
                    "num_steps": len(config.steps),
                    "timeout_s": config.timeout_s,
                }
            )

        return pipelines

    def get_pipeline(self, pipeline_name: str) -> dict[str, Any] | None:
        """Get detailed information about a pipeline.

        Args:
            pipeline_name: Name of the pipeline

        Returns:
            Pipeline information dictionary or None if not found
        """
        if pipeline_name not in self.workspace.pipelines:
            return None

        config = self.workspace.pipelines[pipeline_name]

        # Extract step information
        steps = []
        for i, step in enumerate(config.steps):
            step_info = {
                "index": i,
                "use": step.use,
                "shop": step.shop,
                "condition": step.condition,
                "timeout_s": step.timeout_s,
            }

            # Add MCP-specific fields
            if step.shop == "mcp":
                step_info["provider"] = step.provider
                step_info["tool"] = step.tool

            steps.append(step_info)

        return {
            "name": pipeline_name,
            "shop": config.shop,
            "description": config.description,
            "entrypoint": config.entrypoint,
            "timeout_s": config.timeout_s,
            "num_steps": len(config.steps),
            "steps": steps,
        }

    def list_artifact_types(self) -> list[ArtifactTypeInfo]:
        """List available artifact types.

        Returns:
            List of ArtifactTypeInfo objects
        """
        artifacts = []

        # Import artifact modules and introspect
        try:
            from sibyl.core.artifacts import (
                ASTArtifact,
                GraphArtifact,
                PollableJobHandle,
                SolverResultArtifact,
            )

            # PollableJobHandle
            artifacts.append(
                ArtifactTypeInfo(
                    name="PollableJobHandle",
                    module="sibyl.core.artifacts.job_handle",
                    description="Handle for long-running jobs with automatic polling",
                    fields=["provider", "job_id", "job_type", "status_tool", "result_tool"],
                )
            )

            # SolverResultArtifact
            artifacts.append(
                ArtifactTypeInfo(
                    name="SolverResultArtifact",
                    module="sibyl.core.artifacts.solver",
                    description="Result from constraint solver execution",
                    fields=["status", "solution", "objective_value", "solve_time_ms"],
                )
            )

            # GraphArtifact
            artifacts.append(
                ArtifactTypeInfo(
                    name="GraphArtifact",
                    module="sibyl.core.artifacts.graph",
                    description="Graph data with nodes and edges",
                    fields=["nodes", "edges", "graph_type", "metadata"],
                )
            )

            # ASTArtifact
            artifacts.append(
                ArtifactTypeInfo(
                    name="ASTArtifact",
                    module="sibyl.core.artifacts.ast",
                    description="Abstract syntax tree for code analysis",
                    fields=["root", "language", "source_file"],
                )
            )

        except ImportError as e:
            logger.warning("Could not import artifacts: %s", e)

        return artifacts

    def search_tools(self, query: str) -> list[ToolInfo]:
        """Search for tools matching a query string.

        Args:
            query: Search query (matches tool name or provider name)

        Returns:
            List of matching ToolInfo objects
        """
        query_lower = query.lower()
        matching_tools = []

        for tool in self.list_mcp_tools():
            if query_lower in tool.name.lower() or query_lower in tool.provider.lower():
                matching_tools.append(tool)

        return matching_tools

    def get_workspace_summary(self) -> dict[str, Any]:
        """Get a summary of workspace capabilities.

        Returns:
            Dictionary with workspace summary
        """
        return {
            "name": self.workspace.name,
            "version": self.workspace.version,
            "description": self.workspace.description,
            "providers": {
                "mcp": len(self.workspace.providers.mcp),
                "llm": len(self.workspace.providers.llm) if self.workspace.providers.llm else 0,
                "embeddings": len(self.workspace.providers.embeddings)
                if self.workspace.providers.embeddings
                else 0,
                "vector_store": len(self.workspace.providers.vector_store)
                if self.workspace.providers.vector_store
                else 0,
            },
            "shops": len(self.workspace.shops),
            "pipelines": len(self.workspace.pipelines),
            "mcp_tools": len(self.list_mcp_tools()),
        }

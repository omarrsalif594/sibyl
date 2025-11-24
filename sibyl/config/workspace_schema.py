"""Workspace configuration schema using Pydantic v2.

This module defines the schema for Sibyl workspace configurations, which serve
as the single source of truth for:
- Providers (LLM, embeddings, vector store, external MCPs)
- Shops (RAG, AI generation, workflow, infrastructure, agents)
- Pipelines (named workflows that chain techniques)
- MCP tools (which pipelines are exposed as tools)

Example:
    from sibyl.config.workspace_schema import WorkspaceSettings
    from sibyl.config.workspace_loader import load_workspace

    # Load workspace configuration
    workspace = load_workspace("config/workspaces/example_local.yaml")

    # Access provider configurations
    llm_config = workspace.providers.llm["default"]
    print(f"Using model: {llm_config.model}")

    # Access shop techniques
    rag_shop = workspace.shops["rag"]
    chunker = rag_shop.techniques["chunker"]

    # Access pipeline definitions
    pipeline = workspace.pipelines["web_research_pipeline"]
    print(f"Pipeline entrypoint: {pipeline.entrypoint}")
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from sibyl.workspace.schema import BudgetConfig


class LLMProviderConfig(BaseModel):
    """Configuration for a Language Model provider.

    Attributes:
        provider: Provider name (e.g., "openai", "anthropic", "local")
        model: Model identifier (e.g., "gpt-4", "claude-3-opus")
        api_key_env: Optional environment variable name containing API key
        base_url: Optional base URL for API endpoint
        max_tokens: Optional maximum tokens for completion
        temperature: Optional temperature for sampling
    """

    provider: str = Field(..., description="Provider name (openai, anthropic, local)")
    model: str = Field(..., description="Model identifier")
    api_key_env: str | None = Field(None, description="Environment variable for API key")
    base_url: str | None = Field(None, description="Base URL for API endpoint")
    max_tokens: int | None = Field(None, description="Maximum tokens for completion")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="Sampling temperature")


class EmbeddingsProviderConfig(BaseModel):
    """Configuration for an embeddings provider.

    Attributes:
        provider: Provider name (e.g., "openai", "local_sentence_transformer")
        model: Model identifier (e.g., "text-embedding-ada-002", "all-MiniLM-L6-v2")
        api_key_env: Optional environment variable name containing API key
        dimension: Optional embedding dimension
    """

    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model identifier")
    api_key_env: str | None = Field(None, description="Environment variable for API key")
    dimension: int | None = Field(None, gt=0, description="Embedding dimension")


class VectorStoreConfig(BaseModel):
    """Configuration for a vector store.

    Attributes:
        kind: Vector store type (e.g., "duckdb", "qdrant", "faiss")
        dsn: Data source name or connection string
        collection_name: Optional collection/table name
        distance_metric: Optional distance metric (e.g., "cosine", "euclidean")
    """

    kind: str = Field(..., description="Vector store type (duckdb, qdrant, faiss)")
    dsn: str = Field(..., description="Data source name or connection string")
    collection_name: str | None = Field(None, description="Collection or table name")
    distance_metric: str | None = Field(
        "cosine", description="Distance metric (cosine, euclidean, dot)"
    )


class MCPToolArtifactMapping(BaseModel):
    """Artifact type mapping for an MCP tool.

    Configures auto-conversion of MCP tool responses to typed artifacts.

    Attributes:
        artifact_type: Target artifact type name (e.g., "GraphMetricsArtifact")
        detect_heuristic: Optional heuristic for automatic detection (e.g., "has_pagerank_key")
        provider_hint: Optional hint passed to artifact factory (e.g., "networkx")

    Example:
        artifact_mappings:
          pagerank:
            artifact_type: GraphMetricsArtifact
            provider_hint: networkx
          chunk_file:
            artifact_type: ChunkArtifact
            provider_hint: chunkhound
    """

    artifact_type: str = Field(..., description="Target artifact type name")
    detect_heuristic: str | None = Field(
        None, description="Optional heuristic for automatic detection"
    )
    provider_hint: str | None = Field(
        None, description="Optional provider hint for artifact factory"
    )


class MCPProviderConfig(BaseModel):
    """Configuration for an external MCP provider.

    Supports both HTTP and stdio transport types for communicating with
    MCP servers.

    Attributes:
        transport: Transport type ("http" or "stdio")
        url: URL for HTTP transport (required if transport="http")
        command: Command array for stdio transport (required if transport="stdio")
        tools: List of tool names to expose from this MCP
        timeout_s: Timeout in seconds for operations
        auth: Optional authentication configuration
        artifact_mappings: Optional tool-to-artifact type mappings for auto-conversion

    Example (HTTP):
        mcp:
          my_service:
            transport: http
            url: http://localhost:6000
            tools: [search, summarize]
            timeout_s: 30

    Example (Stdio):
        mcp:
          local_tool:
            transport: stdio
            command: [python, -m, my_mcp_server]
            tools: [process, analyze]
            timeout_s: 30

    Example (With Artifact Mappings):
        mcp:
          networkx:
            transport: http
            url: http://localhost:8001
            tools: [pagerank, betweenness_centrality]
            artifact_mappings:
              pagerank:
                artifact_type: GraphMetricsArtifact
                provider_hint: networkx
              betweenness_centrality:
                artifact_type: GraphMetricsArtifact
                provider_hint: networkx
    """

    transport: str = Field(..., description="Transport type (http, stdio)")
    url: str | None = Field(None, description="URL for HTTP transport")
    command: list[str] | None = Field(None, description="Command for stdio transport")
    tools: list[str] = Field(default_factory=list, description="Tool names to expose")
    timeout_s: int = Field(30, ge=1, description="Timeout in seconds")
    auth: dict[str, str] | None = Field(None, description="Authentication configuration")
    artifact_mappings: dict[str, MCPToolArtifactMapping] | None = Field(
        None, description="Tool-to-artifact type mappings for auto-conversion"
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate transport-specific fields after initialization."""
        if self.transport == "http" and not self.url:
            msg = "url is required when transport is 'http'"
            raise ValueError(msg)
        if self.transport == "stdio" and not self.command:
            msg = "command is required when transport is 'stdio'"
            raise ValueError(msg)
        if self.transport not in ["http", "stdio"]:
            msg = f"Invalid transport type: {self.transport}. Must be 'http' or 'stdio'"
            raise ValueError(msg)


class DocumentSourceConfig(BaseModel):
    """Configuration for a document source provider.

    Document sources provide access to documents from various backends
    (filesystem, S3, Confluence, etc.) using a unified interface.

    Attributes:
        type: Source type (e.g., "filesystem_markdown", "s3", "confluence")
        config: Implementation-specific configuration parameters

    Example (Filesystem):
        document_sources:
          docs_local:
            type: filesystem_markdown
            config:
              root: ./docs
              pattern: "**/*.md"
              recursive: true

    Example (S3):
        document_sources:
          docs_s3:
            type: s3
            config:
              bucket: my-docs-bucket
              prefix: docs/
              region: us-east-1
    """

    type: str = Field(..., description="Source type (filesystem_markdown, s3, etc)")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Implementation-specific configuration"
    )


class SQLProviderConfig(BaseModel):
    """Configuration for a SQL database provider.

    SQL providers enable querying relational databases for experiments,
    metadata, or other structured data.

    Attributes:
        type: SQL provider type (e.g., "sqlite", "postgres", "mysql")
        dsn: Optional data source name / connection string
        config: Implementation-specific configuration parameters

    Example (SQLite):
        sql:
          experiments:
            type: sqlite
            config:
              path: ./data/experiments.db

    Example (PostgreSQL):
        sql:
          warehouse:
            type: postgres
            dsn: postgresql://user:pass@localhost:5432/dbname
            config:
              pool_size: 10
              timeout: 30
    """

    type: str = Field(..., description="SQL provider type (sqlite, postgres, etc)")
    dsn: str | None = Field(None, description="Data source name / connection string")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Implementation-specific configuration"
    )


class ProvidersConfig(BaseModel):
    """Configuration for all providers.

    Attributes:
        llm: Dictionary of LLM provider configurations (name -> config)
        embeddings: Dictionary of embeddings provider configurations
        vector_store: Dictionary of vector store configurations
        mcp: Dictionary of external MCP provider configurations
        document_sources: Dictionary of document source provider configurations
        sql: Dictionary of SQL provider configurations
    """

    llm: dict[str, LLMProviderConfig] = Field(default_factory=dict, description="LLM providers")
    embeddings: dict[str, EmbeddingsProviderConfig] = Field(
        default_factory=dict, description="Embeddings providers"
    )
    vector_store: dict[str, VectorStoreConfig] = Field(
        default_factory=dict, description="Vector stores"
    )
    mcp: dict[str, MCPProviderConfig] = Field(
        default_factory=dict, description="External MCP providers"
    )
    document_sources: dict[str, DocumentSourceConfig] = Field(
        default_factory=dict, description="Document source providers"
    )
    sql: dict[str, SQLProviderConfig] = Field(
        default_factory=dict, description="SQL database providers"
    )


class ShopConfig(BaseModel):
    """Configuration for a shop (collection of techniques).

    Shops organize techniques by domain (e.g., RAG, AI generation, workflow).
    Each shop defines mappings from technique names to implementation aliases.

    Attributes:
        techniques: Mapping of technique name to implementation alias
                   (e.g., {"chunker": "rag_pipeline.chunking:semantic"})
        config: Optional shop-specific configuration
    """

    techniques: dict[str, str] = Field(
        default_factory=dict, description="Technique name to implementation mapping"
    )
    config: dict[str, Any] | None = Field(None, description="Shop-specific configuration")


class PipelineStepConfig(BaseModel):
    """Configuration for a single pipeline step.

    Supports two types of steps:
    1. Shop technique steps: use="shop.technique" (e.g., "rag.chunker")
    2. MCP tool steps: shop="mcp", provider="provider_name", tool="tool_name"

    Attributes:
        use: Reference to a shop technique (e.g., "rag.chunker")
        shop: Shop name (for technique steps) or "mcp" (for MCP tool steps)
        provider: MCP provider name (required when shop="mcp")
        tool: MCP tool name (required when shop="mcp")
        params: Parameters to pass to MCP tool (used when shop="mcp")
        config: Optional step-specific configuration (for technique steps)
        condition: Optional condition for step execution
        timeout_s: Optional step timeout in seconds
        budget: Optional step-level budget

    Example (technique step):
        steps:
          - use: rag.chunker
            config:
              chunk_size: 512

    Example (MCP tool step):
        steps:
          - shop: mcp
            provider: my_mcp_provider
            tool: search
            params:
              query: "test"
              limit: 10
    """

    use: str | None = Field(None, description="Reference to shop technique (e.g., rag.chunker)")
    shop: str | None = Field(None, description="Shop name or 'mcp' for MCP tools")
    provider: str | None = Field(None, description="MCP provider name (for shop='mcp')")
    tool: str | None = Field(None, description="MCP tool name (for shop='mcp')")
    params: dict[str, Any] | None = Field(None, description="Parameters for MCP tool")
    config: dict[str, Any] | None = Field(None, description="Step-specific configuration")
    condition: str | None = Field(None, description="Condition for step execution")
    timeout_s: int | None = Field(None, ge=1, description="Step timeout in seconds")
    budget: BudgetConfig | None = Field(None, description="Step-level budget")

    def model_post_init(self, __context: Any) -> None:
        """Validate step configuration after initialization."""
        # Check that either 'use' or 'shop=mcp' is specified
        is_technique_step = self.use is not None
        is_mcp_step = self.shop == "mcp"

        if not is_technique_step and not is_mcp_step:
            msg = (
                "Step must specify either 'use' (for technique step) or "
                "'shop: mcp' with 'provider' and 'tool' (for MCP tool step)"
            )
            raise ValueError(msg)

        if is_technique_step and is_mcp_step:
            msg = (
                "Step cannot specify both 'use' and 'shop: mcp'. "
                "Use 'use' for techniques or 'shop: mcp' for MCP tools."
            )
            raise ValueError(msg)

        # Validate MCP step has required fields
        if is_mcp_step:
            if not self.provider:
                msg = "MCP step requires 'provider' field"
                raise ValueError(msg)
            if not self.tool:
                msg = "MCP step requires 'tool' field"
                raise ValueError(msg)


class PipelineConfig(BaseModel):
    """Configuration for a pipeline (workflow of techniques).

    Pipelines define sequences of technique invocations that accomplish
    higher-level tasks. They can be exposed as MCP tools.

    Attributes:
        shop: Shop that owns this pipeline (provides default context)
        entrypoint: Entry point for pipeline execution (e.g., "research.run")
        steps: List of pipeline steps to execute in sequence
        description: Optional pipeline description
        timeout_s: Optional timeout in seconds
    """

    shop: str = Field(..., description="Shop that owns this pipeline")
    entrypoint: str = Field(..., description="Entry point for execution")
    steps: list[PipelineStepConfig] = Field(..., description="Pipeline steps")
    description: str | None = Field(None, description="Pipeline description")
    timeout_s: int | None = Field(None, ge=1, description="Timeout in seconds")


class MCPToolConfig(BaseModel):
    """Configuration for an MCP tool that exposes a pipeline.

    Attributes:
        name: Tool name (exposed to MCP clients)
        description: Tool description (for MCP clients)
        pipeline: Pipeline name to invoke
        input_schema: Optional JSON schema for tool inputs
    """

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    pipeline: str = Field(..., description="Pipeline name to invoke")
    input_schema: dict[str, Any] | None = Field(None, description="JSON schema for inputs")


class MCPConfig(BaseModel):
    """Configuration for MCP tool exposure.

    Attributes:
        tools: List of MCP tool configurations
        server_name: Optional MCP server name
        server_version: Optional MCP server version
    """

    tools: list[MCPToolConfig] = Field(default_factory=list, description="MCP tools")
    server_name: str | None = Field(None, description="MCP server name")
    server_version: str | None = Field(None, description="MCP server version")


class WorkspaceSettings(BaseModel):
    """Complete workspace configuration.

    This is the top-level configuration object that contains all workspace
    settings including providers, shops, pipelines, and MCP tool definitions.

    Attributes:
        name: Workspace name
        description: Optional workspace description
        version: Optional workspace configuration version
        providers: Provider configurations
        shops: Shop configurations (technique collections)
        pipelines: Pipeline configurations (workflows)
        mcp: MCP tool exposure configuration

    Example:
        workspace = WorkspaceSettings(
            name="my-workspace",
            description="Local RAG demo",
            providers=ProvidersConfig(...),
            shops={"rag": ShopConfig(...)},
            pipelines={"research": PipelineConfig(...)},
            mcp=MCPConfig(...)
        )
    """

    name: str = Field(..., description="Workspace name")
    description: str | None = Field(None, description="Workspace description")
    version: str | None = Field("1.0", description="Configuration version")
    providers: ProvidersConfig = Field(..., description="Provider configurations")
    shops: dict[str, ShopConfig] = Field(default_factory=dict, description="Shop configurations")
    pipelines: dict[str, PipelineConfig] = Field(
        default_factory=dict, description="Pipeline configurations"
    )
    mcp: MCPConfig = Field(default_factory=MCPConfig, description="MCP configuration")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "local-rag-demo",
                "description": "Local RAG and web research demo",
                "version": "1.0",
                "providers": {
                    "llm": {
                        "default": {
                            "provider": "openai",
                            "model": "gpt-4",
                            "api_key_env": "OPENAI_API_KEY",
                        }
                    },
                    "embeddings": {
                        "default": {
                            "provider": "local_sentence_transformer",
                            "model": "all-MiniLM-L6-v2",
                        }
                    },
                    "vector_store": {
                        "default": {
                            "kind": "duckdb",
                            "dsn": "duckdb://./data/vector_store.duckdb",
                        }
                    },
                },
                "shops": {
                    "rag": {
                        "techniques": {
                            "chunker": "rag_pipeline.chunking:semantic",
                            "retriever": "rag_pipeline.retrieval:semantic_search",
                        }
                    }
                },
                "pipelines": {
                    "web_research": {
                        "shop": "ai_generation",
                        "entrypoint": "research.run",
                        "steps": [{"use": "rag.chunker"}, {"use": "rag.retriever"}],
                    }
                },
                "mcp": {
                    "tools": [
                        {
                            "name": "web_research",
                            "description": "Research a topic on the web",
                            "pipeline": "web_research",
                        }
                    ]
                },
            }
        }
    )

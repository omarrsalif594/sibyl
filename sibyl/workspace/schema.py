"""Workspace configuration schema using Pydantic v2.

This module defines the schema for Sibyl workspace configurations, which serve
as the single source of truth for:
- Providers (LLM, embeddings, vector store, external MCPs)
- Shops (RAG, AI generation, workflow, infrastructure, agents)
- Pipelines (named workflows that chain techniques)
- MCP tools (which pipelines are exposed as tools)

Example:
    from sibyl.workspace import WorkspaceSettings, load_workspace

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


class BudgetConfig(BaseModel):
    """Configuration for budget limits on cost, tokens, and requests.

    Budgets can be specified at global (workspace), pipeline, or step level
    to prevent unbounded resource usage and cost explosions.

    Attributes:
        max_cost_usd: Optional maximum cost in USD
        max_tokens: Optional maximum number of tokens (input + output)
        max_requests: Optional maximum number of LLM requests
    """

    max_cost_usd: float | None = Field(None, ge=0.0, description="Maximum cost in USD")
    max_tokens: int | None = Field(None, ge=0, description="Maximum total tokens (input + output)")
    max_requests: int | None = Field(None, ge=0, description="Maximum number of LLM requests")


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
    """

    transport: str = Field(..., description="Transport type (http, stdio)")
    url: str | None = Field(None, description="URL for HTTP transport")
    command: list[str] | None = Field(None, description="Command for stdio transport")
    tools: list[str] = Field(default_factory=list, description="Tool names to expose")
    timeout_s: int = Field(30, ge=1, description="Timeout in seconds")
    auth: dict[str, str] | None = Field(None, description="Authentication configuration")

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


class ProvidersConfig(BaseModel):
    """Configuration for all providers.

    Attributes:
        llm: Dictionary of LLM provider configurations (name -> config)
        embeddings: Dictionary of embeddings provider configurations
        vector_store: Dictionary of vector store configurations
        mcp: Dictionary of external MCP provider configurations
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


class LoopConfig(BaseModel):
    """Configuration for loop control flow (C1.1).

    Supports three loop types:
    1. for_each: Iterate over a collection
    2. while: Loop while condition is true
    3. Combination: for_each with additional while condition

    Attributes:
        for_each: Template expression that evaluates to a collection
        var: Variable name to bind each item to (default: "item")
        while_condition: Optional while condition (evaluated each iteration)
        max_iterations: Maximum iterations before break (default: 10)
        steps: Steps to execute in each iteration
        break_on: Optional condition to break loop early

    Example (for_each):
        loop:
          for_each: "{{ context.results }}"
          var: "item"
          max_iterations: 10
          steps:
            - use: ai_generation.process

    Example (while):
        loop:
          while_condition: "{{ context.counter < 5 }}"
          max_iterations: 10
          steps:
            - use: ai_generation.increment
    """

    for_each: str | None = Field(None, description="Template expression for collection to iterate")
    var: str = Field("item", description="Variable name for loop item")
    while_condition: str | None = Field(None, description="While condition (template expression)")
    max_iterations: int = Field(10, ge=1, le=1000, description="Maximum iterations")
    steps: list["PipelineStepConfig"] = Field(..., description="Steps to execute in loop")
    break_on: str | None = Field(None, description="Condition to break loop early")

    def model_post_init(self, __context: Any) -> None:
        """Validate loop configuration."""
        if not self.for_each and not self.while_condition:
            msg = "Loop must specify either 'for_each' or 'while_condition'"
            raise ValueError(msg)


class ParallelConfig(BaseModel):
    """Configuration for parallel execution (C1.2).

    Executes multiple steps concurrently and collects results.

    Attributes:
        steps: Steps to execute in parallel
        gather: Variable name to store results dict (default: "parallel_results")
        fail_fast: Stop on first error (default: True)
        timeout_s: Optional timeout for all parallel steps

    Example:
        parallel:
          gather: "analysis_results"
          fail_fast: true
          steps:
            - name: "networkx"
              shop: mcp
              provider: mcp_nlp
              tool: analyze_graph
            - name: "ast_scan"
              shop: mcp
              provider: mcp_ast
              tool: scan_patterns
    """

    steps: list["PipelineStepConfig"] = Field(
        ..., min_length=1, description="Steps to execute in parallel"
    )
    gather: str = Field("parallel_results", description="Variable name for results dict")
    fail_fast: bool = Field(True, description="Stop on first error")
    timeout_s: int | None = Field(None, ge=1, description="Timeout for all parallel steps")

    def model_post_init(self, __context: Any) -> None:
        """Validate parallel configuration."""
        if len(self.steps) < 2:
            msg = "Parallel execution requires at least 2 steps"
            raise ValueError(msg)


class CatchBlock(BaseModel):
    """Configuration for a catch block in try/catch/finally (C1.3).

    Attributes:
        when: Condition to match (template expression)
        steps: Steps to execute if condition matches
    """

    when: str = Field(..., description="Condition to match error (template expression)")
    steps: list["PipelineStepConfig"] = Field(..., description="Steps to execute on error match")


class TryConfig(BaseModel):
    """Configuration for try/catch/finally error handling (C1.3).

    Attributes:
        steps: Steps to try executing
        catch: List of catch blocks (evaluated in order)
        finally_steps: Steps to always execute (even on error)

    Example:
        try:
          steps:
            - shop: mcp
              provider: solver
              tool: solve
          catch:
            - when: "{{ error.type == 'UNSAT' }}"
              steps:
                - shop: mcp
                  provider: solver
                  tool: relax_constraints
            - when: "{{ error.type == 'Timeout' }}"
              steps:
                - use: ai_generation.log_timeout
          finally:
            - use: ai_generation.cleanup
    """

    steps: list["PipelineStepConfig"] = Field(..., description="Steps to try")
    catch: list[CatchBlock] | None = Field(None, description="Catch blocks")
    finally_steps: list["PipelineStepConfig"] | None = Field(None, description="Finally steps")


class PipelineStepConfig(BaseModel):
    """Configuration for a single pipeline step.

    Supports five types of steps:
    1. Shop technique steps: use="shop.technique" (e.g., "rag.chunker")
    2. MCP tool steps: shop="mcp", provider="provider_name", tool="tool_name"
    3. Loop steps: loop={...}
    4. Parallel steps: parallel={...}
    5. Try/catch/finally steps: try_block={...}

    Attributes:
        name: Optional step name (used in parallel execution)
        use: Reference to a shop technique (e.g., "rag.chunker")
        shop: Shop name (for technique steps) or "mcp" (for MCP tool steps)
        provider: MCP provider name (required when shop="mcp")
        tool: MCP tool name (required when shop="mcp")
        params: Parameters to pass to MCP tool (used when shop="mcp")
        config: Optional step-specific configuration (for technique steps)
        condition: Optional condition for step execution
        timeout_s: Optional step timeout in seconds
        budget: Optional step-level budget
        loop: Loop configuration (C1.1)
        parallel: Parallel execution configuration (C1.2)
        try_block: Try/catch/finally configuration (C1.3)
        retry: Retry configuration (reuse existing retry infrastructure)

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

    Example (loop):
        steps:
          - loop:
              for_each: "{{ context.items }}"
              var: "item"
              steps:
                - use: rag.process

    Example (parallel):
        steps:
          - parallel:
              steps:
                - name: "task1"
                  use: rag.analyze
                - name: "task2"
                  use: rag.summarize
    """

    name: str | None = Field(None, description="Step name (for parallel execution)")
    use: str | None = Field(None, description="Reference to shop technique (e.g., rag.chunker)")
    shop: str | None = Field(None, description="Shop name or 'mcp' for MCP tools")
    provider: str | None = Field(None, description="MCP provider name (for shop='mcp')")
    tool: str | None = Field(None, description="MCP tool name (for shop='mcp')")
    params: dict[str, Any] | None = Field(None, description="Parameters for MCP tool")
    config: dict[str, Any] | None = Field(None, description="Step-specific configuration")
    condition: str | None = Field(None, description="Condition for step execution")
    timeout_s: int | None = Field(None, ge=1, description="Timeout in seconds for this step")
    budget: BudgetConfig | None = Field(None, description="Budget limits for this step")
    loop: LoopConfig | None = Field(None, description="Loop configuration (C1.1)")
    parallel: ParallelConfig | None = Field(
        None, description="Parallel execution configuration (C1.2)"
    )
    try_block: TryConfig | None = Field(None, description="Try/catch/finally configuration (C1.3)")
    retry: dict[str, Any] | None = Field(None, description="Retry configuration")

    def model_post_init(self, __context: Any) -> None:
        """Validate step configuration after initialization."""
        # Check mutually exclusive step types
        step_types = []
        if self.use is not None:
            step_types.append("technique")
        if self.shop == "mcp":
            step_types.append("mcp")
        if self.loop is not None:
            step_types.append("loop")
        if self.parallel is not None:
            step_types.append("parallel")
        if self.try_block is not None:
            step_types.append("try")

        if len(step_types) == 0:
            msg = (
                "Step must specify one of: 'use' (technique), 'shop: mcp' (MCP tool), "
                "'loop' (loop), 'parallel' (parallel execution), or 'try_block' (error handling)"
            )
            raise ValueError(msg)

        if len(step_types) > 1:
            msg = (
                f"Step cannot specify multiple types: {', '.join(step_types)}. "
                "Choose one: technique, MCP tool, loop, parallel, or try."
            )
            raise ValueError(msg)

        # Validate MCP step has required fields
        if self.shop == "mcp":
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
        budget: Optional budget limits for this pipeline
    """

    shop: str = Field(..., description="Shop that owns this pipeline")
    entrypoint: str = Field(..., description="Entry point for execution")
    steps: list[PipelineStepConfig] = Field(..., description="Pipeline steps")
    description: str | None = Field(None, description="Pipeline description")
    timeout_s: int | None = Field(None, ge=1, description="Timeout in seconds")
    budget: BudgetConfig | None = Field(None, description="Budget limits for this pipeline")


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


class StateConfig(BaseModel):
    """Configuration for state and session management.

    Controls persistence and tracking of:
    - External resource handles (collections, workflows, forecasts)
    - Session state with checkpoints
    - Pipeline execution state

    Attributes:
        enabled: Whether state persistence is enabled
        backend: State persistence backend (default: "duckdb")
        db_path: Path to state database file
        auto_checkpoint: Whether to automatically checkpoint sessions
        track_external_resources: Whether to track external MCP resources
        track_sessions: Whether to track MCP sessions
        cleanup_on_shutdown: Whether to cleanup tracked resources on shutdown
    """

    enabled: bool = Field(True, description="Enable state persistence")
    backend: str = Field("duckdb", description="State persistence backend")
    db_path: str = Field("./data/sibyl_state.duckdb", description="Path to state database")
    auto_checkpoint: bool = Field(False, description="Automatically checkpoint sessions on updates")
    track_external_resources: bool = Field(True, description="Track external MCP resources")
    track_sessions: bool = Field(True, description="Track MCP sessions")
    cleanup_on_shutdown: bool = Field(False, description="Cleanup tracked resources on shutdown")


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
        budget: Optional global budget limits for the workspace
        state: Optional state and session management configuration

    Example:
        workspace = WorkspaceSettings(
            name="my-workspace",
            description="Local RAG demo",
            providers=ProvidersConfig(...),
            shops={"rag": ShopConfig(...)},
            pipelines={"research": PipelineConfig(...)},
            mcp=MCPConfig(...),
            budget=BudgetConfig(max_cost_usd=10.0),
            state=StateConfig(enabled=True)
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
    budget: BudgetConfig | None = Field(None, description="Global budget limits")
    state: StateConfig | None = Field(
        default_factory=StateConfig, description="State management configuration"
    )

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

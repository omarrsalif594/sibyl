"""
REST API for Sibyl pipelines and core services.

Exposes:
- Pipeline execution endpoints
- Pipeline metadata
- Health check
- Graph traversal
- Entity search

Security Features:
- Input validation via Pydantic schemas
- Type checking and size limits
- Clear error messages
- Parameterized queries (no SQL injection)
"""

import logging
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Path, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from sibyl.api.health import router as health_router
from sibyl.framework.container import create_core_container
from sibyl.server.openai_facade import router as openai_router
from sibyl.server.schemas import (
    ErrorResponse,
    GraphTraverseRequest,
    SearchEntitiesRequest,
    ValidationErrorDetail,
    ValidationErrorResponse,
    validate_pipeline_input,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sibyl API",
    description="Sibyl Pipeline Execution and Core Services API with Input Validation",
    version="2.1",
)

container = create_core_container()

app.include_router(health_router)
app.include_router(openai_router)

# Global workspace runtime (set via init_workspace)
_workspace_runtime: Any | None = None


# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Any:
    """Handle Pydantic validation errors with detailed messages.

    Returns HTTP 400 with validation error details.
    """
    errors = []
    for error in exc.errors():
        errors.append(
            ValidationErrorDetail(
                field=".".join(str(loc) for loc in error["loc"]),
                message=error["msg"],
                type=error["type"],
            )
        )

    logger.warning(
        f"Validation error on {request.method} {request.url.path}: {exc}", extra={"errors": errors}
    )

    response = ValidationErrorResponse(
        message="Invalid input parameters. Please check the request and try again.", details=errors
    )

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=response.dict())


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> Any:
    """Handle HTTP exceptions with consistent error format."""
    logger.warning(
        "HTTP error on %s %s: %s - %s",
        request.method,
        request.url.path,
        exc.status_code,
        exc.detail,
    )

    # If detail is already a dict (from error responses), use it as-is
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    # Otherwise, format as ErrorResponse
    response = ErrorResponse(error=f"HTTP {exc.status_code}", message=str(exc.detail))

    return JSONResponse(status_code=exc.status_code, content=response.dict())


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> Any:
    """Handle unexpected errors with safe error messages.

    Returns HTTP 500 without exposing internal details.
    """
    logger.exception("Unexpected error on %s %s: %s", request.method, request.url.path, exc)

    response = ErrorResponse(
        error="Internal Server Error",
        message="An unexpected error occurred. Please try again later.",
    )

    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response.dict())


def init_workspace(workspace_path: str) -> None:
    """Initialize the API with a workspace configuration.

    This must be called before the API can handle pipeline requests.

    Args:
        workspace_path: Path to workspace YAML file
    """
    global _workspace_runtime

    from sibyl.runtime.pipeline import WorkspaceRuntime
    from sibyl.runtime.providers import build_providers
    from sibyl.server.openai_facade import init_facade
    from sibyl.workspace import load_workspace

    try:
        from sibyl.techniques.infrastructure.llm.router import LLMRouter  # optional dependency
        from sibyl.techniques.infrastructure.providers.registry import (
            ProviderRegistry,
        )  # optional dependency

    except ImportError:
        # Fallback if imports fail
        LLMRouter = None
        ProviderRegistry = None

    logger.info("Loading workspace from: %s", workspace_path)
    workspace = load_workspace(workspace_path)

    logger.info("Building providers...")
    providers = build_providers(workspace)

    logger.info("Initializing runtime...")
    _workspace_runtime = WorkspaceRuntime(workspace, providers)

    # Initialize OpenAI facade with router and registry
    # Note: This is a basic initialization. In production, you would configure
    # the router and registry with proper settings from the workspace
    if LLMRouter and ProviderRegistry:
        try:
            # Get provider registry if available
            provider_registry = getattr(providers, "registry", None)
            if not provider_registry:
                # Try to create one from workspace config
                provider_registry = ProviderRegistry(workspace.dict())

            # Create LLM router with workspace config
            router_config = workspace.dict() if hasattr(workspace, "dict") else {}
            llm_router = LLMRouter(router_config, provider_registry)

            # Initialize facade
            init_facade(
                llm_router=llm_router, provider_registry=provider_registry, config=router_config
            )
            logger.info("OpenAI facade initialized successfully")
        except Exception as e:
            logger.warning(
                "Failed to initialize OpenAI facade: %s. Facade endpoints will be unavailable.", e
            )
    else:
        logger.info("OpenAI facade dependencies not available, skipping initialization")

    logger.info("Workspace '%s' initialized successfully", workspace.name)


def get_runtime() -> Any:
    """Get the workspace runtime, raising an error if not initialized.

    Returns:
        WorkspaceRuntime instance

    Raises:
        HTTPException: If workspace not initialized
    """
    if _workspace_runtime is None:
        raise HTTPException(
            status_code=503,
            detail="Workspace not initialized. Server must be started with workspace configuration.",
        )
    return _workspace_runtime


# =============================================================================
# Pipeline API Models
# =============================================================================


class PipelineExecutionRequest(BaseModel):
    """Request model for pipeline execution."""

    params: dict[str, Any] = Field(
        default_factory=dict, description="Pipeline parameters as key-value pairs"
    )


class PipelineExecutionResponse(BaseModel):
    """Response model for pipeline execution."""

    ok: bool = Field(..., description="True if pipeline succeeded")
    status: str = Field(..., description="Execution status (success, error, timeout)")
    trace_id: str = Field(..., description="Trace ID for log correlation")
    pipeline_name: str = Field(..., description="Name of executed pipeline")
    duration_ms: float | None = Field(None, description="Execution duration in milliseconds")
    data: dict[str, Any] | None = Field(None, description="Pipeline result data (on success)")
    error: dict[str, Any] | None = Field(None, description="Error information (on failure)")
    start_time: str | None = Field(None, description="Pipeline start time (ISO format)")
    end_time: str | None = Field(None, description="Pipeline end time (ISO format)")


class PipelineInfo(BaseModel):
    """Model for pipeline metadata."""

    name: str = Field(..., description="Pipeline name")
    shop: str = Field(..., description="Shop that owns this pipeline")
    description: str | None = Field(None, description="Pipeline description")
    entrypoint: str = Field(..., description="Entry point for execution")
    num_steps: int = Field(..., description="Number of pipeline steps")
    timeout_s: int | None = Field(None, description="Pipeline timeout in seconds")
    steps: list[str] = Field(..., description="List of step references")


class PipelineListResponse(BaseModel):
    """Response model for listing pipelines."""

    pipelines: list[str] = Field(..., description="List of pipeline names")
    count: int = Field(..., description="Number of pipelines")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Health status")
    workspace: str | None = Field(None, description="Workspace name")
    pipelines: int | None = Field(None, description="Number of pipelines")


# =============================================================================
# Core API Models (existing)
# =============================================================================


class TraverseResponse(BaseModel):
    entity_id: str
    direction: str
    max_depth: int
    nodes: list[str]


class SearchResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]


@app.get("/health")
async def health() -> dict[str, Any]:
    """Simple health check with provider stats."""
    stats = {
        "status": "ok",
        "providers": [],
    }
    for provider in container.health_check():
        stats["providers"].append(
            {
                "name": provider.name,
                "healthy": provider.healthy,
                "message": provider.message,
                "details": provider.details or {},
            }
        )
    return stats


def _bfs_traverse(entity_id: str, direction: str, max_depth: int) -> list[str]:
    graph = container.get_graph_provider()
    if max_depth < 0:
        raise HTTPException(status_code=400, detail="max_depth must be non-negative")

    visited = set()
    queue = [(entity_id, 0)]
    collected: list[str] = []

    while queue:
        current, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        neighbors = (
            graph.neighbors(current, direction=direction) if hasattr(graph, "neighbors") else []
        )
        for neighbor in neighbors:
            if neighbor in visited:
                continue
            visited.add(neighbor)
            collected.append(neighbor)
            queue.append((neighbor, depth + 1))
    return collected


@app.get("/graph/traverse", response_model=TraverseResponse)
async def traverse_graph(
    entity_id: str = Query(..., min_length=1, max_length=256),
    direction: str = Query("both", pattern="^(in|out|both)$"),
    max_depth: int = Query(3, ge=0, le=10),
):
    """Traverse neighbors of an entity in the generic graph.

    Security:
    - entity_id: 1-256 characters (prevents empty values and oversized IDs)
    - direction: Must be 'in', 'out', or 'both'
    - max_depth: 0-10 (prevents resource exhaustion from deep traversal)
    """
    # Validate request (FastAPI automatic validation + explicit schema check)
    request = GraphTraverseRequest(
        entity_id=entity_id.strip(), direction=direction, max_depth=max_depth
    )

    # Execute traversal
    nodes = _bfs_traverse(request.entity_id, request.direction, request.max_depth)

    return {
        "entity_id": request.entity_id,
        "direction": request.direction,
        "max_depth": request.max_depth,
        "nodes": nodes,
    }


@app.get("/search/entities", response_model=SearchResponse)
async def search_entities(
    q: str = Query(..., min_length=1, max_length=1000), top_k: int = Query(10, ge=1, le=100)
):
    """Semantic entity search using the generic index.

    Security:
    - q: 1-1000 characters (prevents empty queries and oversized input)
    - top_k: 1-100 (prevents resource exhaustion from large result sets)
    """
    # Validate request (FastAPI automatic validation + explicit schema check)
    request = SearchEntitiesRequest(query=q.strip(), top_k=top_k)

    index = container.get_entity_index()
    if index is None:
        raise HTTPException(
            status_code=503, detail="Entity index disabled. Please check server configuration."
        )

    results = index.search(request.query, top_k=request.top_k)
    formatted = [r.__dict__ for r in results]
    return {"query": request.query, "results": formatted}


# =============================================================================
# Pipeline Endpoints
# =============================================================================


@app.post("/pipelines/{pipeline_name}", response_model=PipelineExecutionResponse)
async def execute_pipeline(
    pipeline_name: str = Path(..., min_length=1, max_length=256),
    request: PipelineExecutionRequest = Body(...),
):
    """Execute a pipeline with parameters.

    Args:
        pipeline_name: Name of the pipeline to execute (1-256 characters)
        request: Pipeline execution request with parameters

    Returns:
        Pipeline execution result with observability data

    Raises:
        HTTPException: 400 for validation errors, 404 if pipeline not found,
                      500 for execution errors, 504 for timeouts

    Security:
    - pipeline_name: 1-256 characters (prevents empty names and oversized input)
    - params: Validated against pipeline-specific schema (if available)
    """
    runtime = get_runtime()

    # Sanitize pipeline name
    pipeline_name = pipeline_name.strip()

    # Check if pipeline exists
    pipeline_info = runtime.get_pipeline_info(pipeline_name)
    if pipeline_info is None:
        available_pipelines = runtime.list_pipelines()
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline '{pipeline_name}' not found. Available: {available_pipelines}",
        )

    # Validate input parameters against pipeline schema (if available)
    try:
        validated_input = validate_pipeline_input(pipeline_name, **request.params)
        validated_params = validated_input.dict()
        logger.info("Input validation passed for pipeline '%s'", pipeline_name)
    except ValueError as e:
        # No schema defined for this pipeline, use raw params
        logger.debug("No schema for pipeline '%s', skipping validation: %s", pipeline_name, e)
        validated_params = request.params
    except ValidationError as e:
        # Validation failed
        logger.warning("Input validation failed for pipeline '%s': %s", pipeline_name, e)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Validation Error",
                "message": f"Invalid input parameters for pipeline '{pipeline_name}'",
                "details": e.errors(),
            },
        ) from e

    try:
        # Execute pipeline with validated parameters
        result = await runtime.run_pipeline_v2(pipeline_name, **validated_params)

        # Convert to response model
        response_data = {
            "ok": result.ok,
            "status": result.status.value,
            "trace_id": result.trace_id,
            "pipeline_name": result.pipeline_name,
            "duration_ms": result.duration_ms,
            "start_time": result.start_time,
            "end_time": result.end_time,
        }

        if result.ok:
            response_data["data"] = result.data
        else:
            response_data["error"] = result.error.to_dict() if result.error else None

        # Return appropriate HTTP status based on result
        if result.ok:
            return response_data
        if result.status.value == "timeout":
            # Return 504 for timeouts
            raise HTTPException(status_code=504, detail=response_data)
        # Return 500 for other errors
        raise HTTPException(status_code=500, detail=response_data)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.exception("Unexpected error executing pipeline: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "status": "error",
                "error": {"type": "InternalServerError", "message": str(e)},
            },
        ) from e


@app.get("/pipelines", response_model=PipelineListResponse)
async def list_pipelines() -> Any:
    """List all available pipelines in the workspace.

    Returns:
        List of pipeline names
    """
    runtime = get_runtime()
    pipelines = runtime.list_pipelines()

    return {"pipelines": pipelines, "count": len(pipelines)}


@app.get("/pipelines/{pipeline_name}", response_model=PipelineInfo)
async def get_pipeline_info(pipeline_name: str) -> Any:
    """Get detailed information about a specific pipeline.

    Args:
        pipeline_name: Name of the pipeline

    Returns:
        Pipeline metadata including steps and configuration

    Raises:
        HTTPException: 404 if pipeline not found
    """
    runtime = get_runtime()
    pipeline_info = runtime.get_pipeline_info(pipeline_name)

    if pipeline_info is None:
        available_pipelines = runtime.list_pipelines()
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline '{pipeline_name}' not found. Available: {available_pipelines}",
        )

    return pipeline_info


@app.get("/health/workspace", response_model=HealthResponse)
async def workspace_health() -> Any:
    """Check workspace health and return metadata.

    Returns:
        Workspace health status
    """
    if _workspace_runtime is None:
        return {"status": "not_initialized", "workspace": None, "pipelines": None}

    return {
        "status": "ok",
        "workspace": _workspace_runtime.workspace.name,
        "pipelines": len(_workspace_runtime.list_pipelines()),
    }

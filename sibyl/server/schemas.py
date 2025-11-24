"""Request and response schemas for Sibyl server endpoints.

This module provides Pydantic models for input validation across all
external entrypoints: MCP, HTTP API, and CLI.

Security Features:
- Type validation (str, int, bool, URL)
- Size limits (min/max length, min/max value)
- Format validation (URL, email, etc.)
- Field constraints (regex patterns, allowed values)
- Automatic error messages for invalid input

Example:
    from sibyl.server.schemas import WebResearchRequest

    # Valid request
    request = WebResearchRequest(query="What is AI?", top_k=5)

    # Invalid request (will raise ValidationError)
    request = WebResearchRequest(query="", top_k=1000)  # Empty query, top_k too large
"""

from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
)

# =============================================================================
# Pipeline Request Schemas
# =============================================================================


class WebResearchRequest(BaseModel):
    """Request schema for web_research pipeline.

    This pipeline conducts comprehensive web research by:
    1. Processing the query
    2. Retrieving relevant documents
    3. Augmenting with context
    4. Generating a response with citations

    Security Constraints:
    - query: 1-2000 characters (prevents empty queries and DoS)
    - top_k: 1-100 results (prevents resource exhaustion)
    - include_citations: boolean only

    Example:
        request = WebResearchRequest(
            query="What are the benefits of RAG systems?",
            top_k=15,
            include_citations=True
        )
    """

    query: Annotated[
        str, StringConstraints(min_length=1, max_length=2000, strip_whitespace=True)
    ] = Field(
        ...,
        description="The research query or question",
        examples=["What are the latest developments in AI?"],
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of documents to retrieve (default: 10, range: 1-100)",
    )
    include_citations: bool = Field(
        default=True, description="Include source citations in response (default: true)"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class SummarizeUrlRequest(BaseModel):
    """Request schema for summarize_url pipeline.

    This pipeline fetches content from a URL and generates a concise summary.

    Security Constraints:
    - url: Must be valid HTTP/HTTPS URL (prevents local file access, other protocols)
    - max_length: 50-5000 tokens (prevents empty summaries and resource exhaustion)

    Example:
        request = SummarizeUrlRequest(
            url="https://example.com/article",
            max_length=500
        )
    """

    url: HttpUrl = Field(
        ...,
        description="The URL to fetch and summarize (must be HTTP/HTTPS)",
        examples=["https://example.com/article"],
    )
    max_length: int = Field(
        default=500,
        ge=50,
        le=5000,
        description="Maximum summary length in tokens (default: 500, range: 50-5000)",
    )

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: HttpUrl) -> HttpUrl:
        """Ensure URL uses HTTP or HTTPS scheme only.

        This prevents:
        - file:// URLs (local file access)
        - ftp:// URLs (FTP access)
        - javascript: URLs (XSS)
        - data: URLs (data injection)
        """
        if v.scheme not in ("http", "https"):
            msg = f"URL scheme must be http or https, got: {v.scheme}"
            raise ValueError(msg)
        return v


# =============================================================================
# CLI Parameter Schemas
# =============================================================================


class PipelineRunParams(BaseModel):
    """Validated parameters for CLI pipeline execution.

    This schema validates parameters passed via --param arguments.

    Example:
        params = PipelineRunParams(
            query="test query",
            top_k=5,
            url="https://example.com"
        )
    """

    # Allow arbitrary parameters (will be validated by pipeline schema)
    model_config = ConfigDict(
        extra="allow",
        str_strip_whitespace=True,
    )


# =============================================================================
# HTTP API Schemas
# =============================================================================


class HealthCheckResponse(BaseModel):
    """Response schema for health check endpoint."""

    status: str = Field(..., description="Health status (ok, degraded, error)")
    providers: list = Field(default_factory=list, description="Provider health status")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "providers": [
                        {"name": "llm", "healthy": True, "message": "OK"},
                        {"name": "vector_store", "healthy": True, "message": "OK"},
                    ],
                }
            ]
        }
    )


class GraphTraverseRequest(BaseModel):
    """Request schema for graph traversal endpoint."""

    entity_id: Annotated[str, StringConstraints(min_length=1, max_length=256)] = Field(
        ..., description="Entity ID to start traversal from"
    )
    direction: str = Field(default="both", description="Traversal direction (in, out, both)")
    max_depth: int = Field(
        default=3, ge=0, le=10, description="Maximum traversal depth (default: 3, range: 0-10)"
    )

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        """Validate direction is one of allowed values."""
        allowed = {"in", "out", "both"}
        if v not in allowed:
            msg = f"direction must be one of {allowed}, got: {v}"
            raise ValueError(msg)
        return v


class SearchEntitiesRequest(BaseModel):
    """Request schema for entity search endpoint."""

    query: Annotated[
        str, StringConstraints(min_length=1, max_length=1000, strip_whitespace=True)
    ] = Field(..., description="Search query")
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of results to return (default: 10, range: 1-100)",
    )


# =============================================================================
# Error Response Schemas
# =============================================================================


class ValidationErrorDetail(BaseModel):
    """Detail for a single validation error."""

    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """Response schema for validation errors (HTTP 400)."""

    error: str = Field(default="Validation Error", description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: list[ValidationErrorDetail] = Field(
        default_factory=list, description="Detailed validation errors"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": "Validation Error",
                    "message": "Invalid input parameters",
                    "details": [
                        {
                            "field": "query",
                            "message": "ensure this value has at least 1 characters",
                            "type": "value_error.any_str.min_length",
                        }
                    ],
                }
            ]
        }
    )


class ErrorResponse(BaseModel):
    """Generic error response schema."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    trace_id: str | None = Field(None, description="Trace ID for debugging")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": "PipelineExecutionError",
                    "message": "Pipeline execution failed: technique not found",
                    "trace_id": "abc123-def456",
                }
            ]
        }
    )


# =============================================================================
# Helper Functions
# =============================================================================


def validate_pipeline_input(pipeline_name: str, **kwargs) -> BaseModel:
    """Validate pipeline input against appropriate schema.

    Args:
        pipeline_name: Name of the pipeline
        **kwargs: Input parameters to validate

    Returns:
        Validated Pydantic model

    Raises:
        ValueError: If pipeline_name is not recognized
        pydantic.ValidationError: If input validation fails

    Example:
        validated = validate_pipeline_input("web_research", query="test", top_k=5)
    """
    schema_map = {
        "web_research": WebResearchRequest,
        "summarize_url": SummarizeUrlRequest,
    }

    if pipeline_name not in schema_map:
        msg = f"Unknown pipeline '{pipeline_name}'. Available pipelines: {list(schema_map.keys())}"
        raise ValueError(msg)

    schema = schema_map[pipeline_name]
    return schema(**kwargs)


__all__ = [
    "ErrorResponse",
    "GraphTraverseRequest",
    "HealthCheckResponse",
    "PipelineRunParams",
    "SearchEntitiesRequest",
    "SummarizeUrlRequest",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
    "WebResearchRequest",
    "validate_pipeline_input",
]

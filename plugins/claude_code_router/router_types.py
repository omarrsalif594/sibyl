"""
Router type definitions for Claude Code Router.

This module defines the core types used for config-driven routing:
- RouteRequest: The incoming routing request with question, tags, and context
- RouteDecision: The routing decision with target and parameters
- RouterConfig: The configuration structure for routing rules
"""

from typing import Literal

from pydantic import BaseModel, Field


class RouteRequest(BaseModel):
    """
    A request to route a question to an appropriate target.

    This is the input to the routing engine. No LLM analysis is performed
    on the request - routing is purely based on the provided tags and context.

    Attributes:
        question: The user's question or prompt
        tags: Optional list of tags for rule matching (e.g., ["analytics", "ml"])
        context: Optional context dictionary with metadata like:
            - repo_path: Path to repository
            - file_list: List of relevant files
            - workspace: Workspace identifier
            - Any other metadata for future rule extensions

    Example:
        >>> request = RouteRequest(
        ...     question="What are the top customers by revenue?",
        ...     tags=["analytics"],
        ...     context={"workspace": "northwind"}
        ... )
    """

    question: str = Field(..., description="The question or prompt to route")
    tags: list[str] | None = Field(
        default=None, description="Tags for rule matching (e.g., ['analytics', 'ml'])"
    )
    context: dict | None = Field(
        default=None, description="Additional context (repo_path, file_list, workspace, etc.)"
    )


class RouteDecision(BaseModel):
    """
    The routing decision made by the router engine.

    This describes where to send the request and with what parameters.
    No automatic decisions are made - this is purely the result of
    matching config rules.

    Attributes:
        target: Where to route the request:
            - "sibyl_pipeline": Route to a Sibyl workspace pipeline
            - "remote_llm": Route to a remote LLM (future extension)
            - "local_specialist": Route to a local specialist (future extension)
            - "noop": No routing, do nothing
        workspace: Optional path to Sibyl workspace YAML file
        pipeline: Optional pipeline name within the workspace
        specialist_id: Optional identifier for a local specialist
        params: Optional additional parameters for the target

    Example:
        >>> decision = RouteDecision(
        ...     target="sibyl_pipeline",
        ...     workspace="examples/companies/northwind_analytics/config/workspace.yaml",
        ...     pipeline="northwind_summary",
        ...     params={"temperature": 0.1}
        ... )
    """

    target: Literal["sibyl_pipeline", "remote_llm", "local_specialist", "noop"] = Field(
        ..., description="The routing target"
    )
    workspace: str | None = Field(
        default=None, description="Path to workspace YAML (for sibyl_pipeline target)"
    )
    pipeline: str | None = Field(
        default=None, description="Pipeline name within workspace (for sibyl_pipeline target)"
    )
    specialist_id: str | None = Field(
        default=None, description="Specialist identifier (for local_specialist target)"
    )
    params: dict | None = Field(default=None, description="Additional parameters for the target")


class RouteRule(BaseModel):
    """
    A single routing rule in the configuration.

    Rules are evaluated in order until a match is found.

    Attributes:
        name: Human-readable name for the rule
        when_tags: Tags that must be present for this rule to match
            - Empty list matches as a fallback (no tags required)
            - Non-empty list requires at least one tag to overlap
        route: The RouteDecision to return if this rule matches

    Example:
        >>> rule = RouteRule(
        ...     name="analytics_via_sibyl",
        ...     when_tags=["analytics"],
        ...     route=RouteDecision(
        ...         target="sibyl_pipeline",
        ...         workspace="examples/companies/northwind_analytics/config/workspace.yaml",
        ...         pipeline="northwind_summary"
        ...     )
        ... )
    """

    name: str = Field(..., description="Human-readable rule name")
    when_tags: list[str] = Field(
        ..., description="Tags that trigger this rule (empty list = fallback)"
    )
    route: RouteDecision = Field(..., description="The route decision for this rule")


class RouterConfig(BaseModel):
    """
    Complete router configuration with all rules.

    Rules are evaluated in the order they appear. The first matching
    rule wins. It's recommended to put specific rules first and a
    fallback rule (with empty when_tags) last.

    Attributes:
        rules: List of routing rules

    Example:
        >>> config = RouterConfig(
        ...     rules=[
        ...         RouteRule(
        ...             name="analytics_via_sibyl",
        ...             when_tags=["analytics"],
        ...             route=RouteDecision(target="sibyl_pipeline", workspace="...")
        ...         ),
        ...         RouteRule(
        ...             name="default_fallback",
        ...             when_tags=[],
        ...             route=RouteDecision(target="remote_llm")
        ...         )
        ...     ]
        ... )
    """

    rules: list[RouteRule] = Field(..., description="Ordered list of routing rules")

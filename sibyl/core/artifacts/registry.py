"""Artifact Registry for MCP Auto-Conversion.

This module provides a registry for mapping MCP tool outputs to typed artifacts,
enabling automatic conversion from raw dict responses to structured artifact classes.

The registry supports:
- Explicit mappings via workspace configuration
- Heuristic-based detection for common patterns
- Provider-specific factory methods
- Graceful fallback to raw dict when conversion fails

Example:
    from sibyl.core.artifacts.registry import ArtifactRegistry, convert_mcp_response

    # Register artifact factories
    registry = ArtifactRegistry()

    # Convert MCP response to artifact
    mcp_result = {"pagerank": {"node_a": 0.25, "node_b": 0.15}}
    artifact = convert_mcp_response(
        response=mcp_result,
        tool_name="pagerank",
        provider="networkx",
        artifact_type="GraphMetricsArtifact"
    )
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ArtifactMapping:
    """Mapping configuration for MCP tool to artifact conversion.

    Attributes:
        artifact_type: Target artifact class name
        factory: Factory function that creates artifact from response
        provider_hint: Optional provider hint for factory method
        detect_heuristic: Optional function to detect if response matches this type
    """

    artifact_type: str
    factory: Callable[[dict[str, Any], str], Any]
    provider_hint: str | None = None
    detect_heuristic: Callable[[dict[str, Any]], bool] | None = None


class ArtifactRegistry:
    """Registry for MCP tool output to artifact type mappings.

    This registry maintains mappings between MCP tool names and artifact factories,
    enabling automatic conversion of raw MCP responses to typed artifacts.

    The registry supports three levels of mapping:
    1. Explicit tool-level mappings from workspace config
    2. Provider-level defaults for common patterns
    3. Heuristic-based detection for unknown tools

    Example:
        registry = ArtifactRegistry()

        # Register a mapping
        registry.register_mapping(
            artifact_type="GraphMetricsArtifact",
            factory=GraphMetricsArtifact.from_mcp_response,
            provider_hint="networkx"
        )

        # Get factory for a tool
        factory = registry.get_factory("pagerank", provider="networkx")
        if factory:
            artifact = factory(mcp_response, "networkx")
    """

    def __init__(self) -> None:
        """Initialize artifact registry."""
        self._mappings: dict[str, ArtifactMapping] = {}
        self._provider_defaults: dict[str, str] = {}
        self._register_builtin_mappings()
        logger.debug("Initialized ArtifactRegistry with builtin mappings")

    def _register_builtin_mappings(self) -> None:
        """Register built-in artifact mappings for common MCP tools.

        This provides sensible defaults for well-known MCPs without requiring
        explicit configuration. Workspace config can override these defaults.
        """
        # Import artifact classes
        try:
            from sibyl.core.artifacts import (  # plugin registration
                ASTArtifact,
                ChunkArtifact,
                GraphArtifact,
                GraphMetricsArtifact,
                PatternArtifact,
                SolverResultArtifact,
                TimeSeriesArtifact,
            )

            # GraphMetricsArtifact - NetworkX tools
            self.register_mapping(
                artifact_type="GraphMetricsArtifact",
                factory=GraphMetricsArtifact.from_mcp_response,
                detect_heuristic=self._detect_graph_metrics,
            )

            # ChunkArtifact - ChunkHound tools
            self.register_mapping(
                artifact_type="ChunkArtifact",
                factory=ChunkArtifact.from_mcp_response,
                detect_heuristic=self._detect_chunk,
            )

            # PatternArtifact - In-Memoria tools
            self.register_mapping(
                artifact_type="PatternArtifact",
                factory=PatternArtifact.from_mcp_response,
                detect_heuristic=self._detect_pattern,
            )

            # TimeSeriesArtifact - Chronulus tools
            self.register_mapping(
                artifact_type="TimeSeriesArtifact",
                factory=TimeSeriesArtifact.from_mcp_response,
                detect_heuristic=self._detect_timeseries,
            )

            # GraphArtifact - Graphiti tools
            self.register_mapping(
                artifact_type="GraphArtifact",
                factory=GraphArtifact.from_mcp_response,
                detect_heuristic=self._detect_graph,
            )

            # SolverResultArtifact - MCP Solver tools
            self.register_mapping(
                artifact_type="SolverResultArtifact",
                factory=SolverResultArtifact.from_mcp_response,
                detect_heuristic=self._detect_solver_result,
            )

            # ASTArtifact - AST server tools
            self.register_mapping(
                artifact_type="ASTArtifact",
                factory=ASTArtifact.from_mcp_response,
                detect_heuristic=self._detect_ast,
            )

            # Provider-level defaults
            self._provider_defaults = {
                "networkx": "GraphMetricsArtifact",
                "chunkhound": "ChunkArtifact",
                "in_memoria": "PatternArtifact",
                "chronulus": "TimeSeriesArtifact",
                "graphiti": "GraphArtifact",
                "mcp_solver": "SolverResultArtifact",
                "ast_server": "ASTArtifact",
                "oxc_parser": "ASTArtifact",
            }

            logger.debug("Registered %s builtin artifact mappings", len(self._mappings))

        except ImportError as e:
            logger.warning("Could not import artifact classes: %s", e)

    def register_mapping(
        self,
        artifact_type: str,
        factory: Callable[[dict[str, Any], str], Any],
        provider_hint: str | None = None,
        detect_heuristic: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        """Register an artifact mapping.

        Args:
            artifact_type: Target artifact class name
            factory: Factory function that creates artifact from response
            provider_hint: Optional provider hint for factory method
            detect_heuristic: Optional heuristic function to detect response type
        """
        mapping = ArtifactMapping(
            artifact_type=artifact_type,
            factory=factory,
            provider_hint=provider_hint,
            detect_heuristic=detect_heuristic,
        )
        self._mappings[artifact_type] = mapping
        logger.debug("Registered artifact mapping: %s", artifact_type)

    def get_factory(
        self, tool_name: str, provider: str, artifact_type: str | None = None
    ) -> Callable[[dict[str, Any], str], Any] | None:
        """Get artifact factory for a tool.

        Looks up factory in the following order:
        1. Explicit artifact_type if provided
        2. Provider-level default
        3. Returns None if no mapping found

        Args:
            tool_name: MCP tool name
            provider: MCP provider name
            artifact_type: Optional explicit artifact type

        Returns:
            Factory function or None if no mapping found
        """
        # Try explicit artifact_type first
        if artifact_type and artifact_type in self._mappings:
            return self._mappings[artifact_type].factory

        # Try provider default
        if provider in self._provider_defaults:
            default_type = self._provider_defaults[provider]
            if default_type in self._mappings:
                return self._mappings[default_type].factory

        # No mapping found
        return None

    def detect_artifact_type(
        self, response: dict[str, Any], tool_name: str, provider: str
    ) -> str | None:
        """Detect artifact type from response using heuristics.

        Runs detection heuristics for all registered artifact types to find
        the best match for the given response.

        Args:
            response: MCP tool response
            tool_name: MCP tool name
            provider: MCP provider name

        Returns:
            Detected artifact type name or None
        """
        # Check provider defaults first
        if provider in self._provider_defaults:
            default_type = self._provider_defaults[provider]
            if default_type in self._mappings:
                mapping = self._mappings[default_type]
                # Verify with heuristic if available
                if mapping.detect_heuristic is None or mapping.detect_heuristic(response):
                    return default_type

        # Run heuristics for all mappings
        for artifact_type, mapping in self._mappings.items():
            if mapping.detect_heuristic and mapping.detect_heuristic(response):
                logger.debug("Detected artifact type %s for tool %s", artifact_type, tool_name)
                return artifact_type

        return None

    # Heuristic detection functions

    @staticmethod
    def _detect_graph_metrics(response: dict[str, Any]) -> bool:
        """Detect GraphMetricsArtifact response."""
        # Look for common graph metric keys
        metric_keys = {
            "pagerank",
            "betweenness_centrality",
            "closeness_centrality",
            "degree_centrality",
            "eigenvector_centrality",
            "clustering_coefficient",
            "communities",
            "scores",
            "ranked_nodes",
        }
        return any(key in response for key in metric_keys)

    @staticmethod
    def _detect_chunk(response: dict[str, Any]) -> bool:
        """Detect ChunkArtifact response."""
        # Look for chunk-specific keys
        chunk_keys = {"chunk_id", "chunk_type", "content", "start_line", "end_line"}
        has_chunk_keys = len(chunk_keys.intersection(response.keys())) >= 3

        # Or nested chunks array
        has_chunks_array = "chunks" in response and isinstance(response["chunks"], list)

        return has_chunk_keys or has_chunks_array

    @staticmethod
    def _detect_pattern(response: dict[str, Any]) -> bool:
        """Detect PatternArtifact response."""
        # Look for pattern-specific keys
        pattern_keys = {"pattern", "pattern_name", "category", "confidence", "code_examples"}
        has_pattern_keys = len(pattern_keys.intersection(response.keys())) >= 2

        # Or nested patterns array
        has_patterns_array = "patterns" in response and isinstance(response["patterns"], list)

        return has_pattern_keys or has_patterns_array

    @staticmethod
    def _detect_timeseries(response: dict[str, Any]) -> bool:
        """Detect TimeSeriesArtifact response."""
        # Look for time series keys
        ts_keys = {"forecast", "predictions", "data", "timestamps", "values", "frequency"}
        return len(ts_keys.intersection(response.keys())) >= 2

    @staticmethod
    def _detect_graph(response: dict[str, Any]) -> bool:
        """Detect GraphArtifact response."""
        # Look for graph structure keys
        graph_keys = {"nodes", "edges", "facts", "graph_type"}
        has_graph_keys = "nodes" in response or ("facts" in response and "entities" in response)
        return has_graph_keys or len(graph_keys.intersection(response.keys())) >= 2

    @staticmethod
    def _detect_solver_result(response: dict[str, Any]) -> bool:
        """Detect SolverResultArtifact response."""
        # Look for solver result keys
        solver_keys = {"status", "solution", "objective_value", "solve_time_ms", "statistics"}
        has_status = "status" in response and isinstance(response.get("status"), str)
        return has_status and len(solver_keys.intersection(response.keys())) >= 2

    @staticmethod
    def _detect_ast(response: dict[str, Any]) -> bool:
        """Detect ASTArtifact response."""
        # Look for AST keys
        ast_keys = {"ast", "root", "tree", "language", "source_file"}
        has_ast_keys = "ast" in response or "root" in response or "tree" in response
        return has_ast_keys or len(ast_keys.intersection(response.keys())) >= 2


# Global singleton registry
_global_registry = None


def get_registry() -> ArtifactRegistry:
    """Get the global artifact registry.

    Returns:
        Global ArtifactRegistry singleton
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ArtifactRegistry()
    return _global_registry


def convert_mcp_response(
    response: dict[str, Any],
    tool_name: str,
    provider: str,
    artifact_type: str | None = None,
    auto_detect: bool = True,
) -> Any | dict[str, Any]:
    """Convert MCP response to typed artifact.

    This is the main entry point for auto-conversion. It handles:
    1. Explicit artifact_type if provided
    2. Auto-detection if enabled
    3. Graceful fallback to raw dict on errors

    Args:
        response: Raw MCP tool response
        tool_name: MCP tool name
        provider: MCP provider name
        artifact_type: Optional explicit artifact type
        auto_detect: Whether to attempt auto-detection (default True)

    Returns:
        Typed artifact instance or raw dict on failure

    Example:
        # Explicit type
        artifact = convert_mcp_response(
            response={"pagerank": {...}},
            tool_name="pagerank",
            provider="networkx",
            artifact_type="GraphMetricsArtifact"
        )

        # Auto-detect
        artifact = convert_mcp_response(
            response={"chunk_id": "func_123", ...},
            tool_name="chunk_file",
            provider="chunkhound"
        )
    """
    registry = get_registry()

    # Try explicit artifact type first
    if artifact_type:
        factory = registry.get_factory(tool_name, provider, artifact_type)
        if factory:
            try:
                artifact = factory(response, provider)
                logger.info(
                    f"Converted MCP response to {artifact_type} "
                    f"(tool={tool_name}, provider={provider})"
                )
                return artifact
            except Exception as e:
                logger.warning(
                    f"Failed to convert to {artifact_type}: {e}. Falling back to raw dict."
                )
                return response

    # Try auto-detection
    if auto_detect:
        detected_type = registry.detect_artifact_type(response, tool_name, provider)
        if detected_type:
            factory = registry.get_factory(tool_name, provider, detected_type)
            if factory:
                try:
                    artifact = factory(response, provider)
                    logger.info(
                        f"Auto-detected and converted to {detected_type} "
                        f"(tool={tool_name}, provider={provider})"
                    )
                    return artifact
                except Exception as e:
                    logger.warning(
                        f"Failed to auto-convert to {detected_type}: {e}. Falling back to raw dict."
                    )
                    return response

    # No conversion - return raw dict
    logger.debug(
        f"No artifact mapping found for tool={tool_name}, provider={provider}. Returning raw dict."
    )
    return response

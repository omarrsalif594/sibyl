"""Cross-MCP Wiring Helpers for Common Workflows (GAP-INT-002).

This module provides helper functions for wiring together multiple MCP tools
in common patterns, particularly for artifact-based workflows.

Key patterns:
- Graphiti → NetworkX: Build graph, analyze metrics, annotate back
- ChunkHound → RAG: Extract chunks, convert to RAG format
- Pattern workflows: In-Memoria → analysis → recommendations

Example:
    from sibyl.core.transformers.cross_mcp import graphiti_to_networkx

    # Convert Graphiti search results to NetworkX graph
    nodes = [{"id": "node1", "name": "Service A"}, ...]
    facts = [{"source": "node1", "target": "node2", "type": "calls"}, ...]

    graph_artifact = graphiti_to_networkx(nodes, facts)
    # Now can pass to NetworkX MCP tools
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def graphiti_to_networkx(
    nodes: list[dict[str, Any]], facts: list[dict[str, Any]], graph_type: str = "directed"
) -> "GraphArtifact":
    """Convert Graphiti search results to GraphArtifact for NetworkX analysis.

    This helper bridges Graphiti (temporal knowledge graph) with NetworkX
    (graph algorithms), enabling workflows like:
    1. Search entities/facts in Graphiti
    2. Convert to GraphArtifact
    3. Analyze with NetworkX PageRank/centrality
    4. Annotate Graphiti nodes with metrics

    Args:
        nodes: List of Graphiti nodes (entities)
        facts: List of Graphiti facts (relationships)
        graph_type: Graph type ("directed" or "undirected")

    Returns:
        GraphArtifact compatible with NetworkX MCP tools

    Example:
        # From Graphiti search
        graphiti_result = await graphiti.search_nodes(query="microservices")
        nodes = graphiti_result.get("nodes", [])
        facts = graphiti_result.get("facts", [])

        # Convert to NetworkX format
        graph = graphiti_to_networkx(nodes, facts)

        # Analyze with NetworkX
        metrics = await networkx.pagerank(graph=graph.to_networkx())
    """
    from sibyl.core.artifacts import Edge, GraphArtifact, GraphType, Node

    # Convert nodes
    graph_nodes = []
    for node in nodes:
        graph_nodes.append(
            Node(
                id=node.get("id", node.get("uuid", str(node))),
                type=node.get("type", node.get("entity_type", "node")),
                properties={
                    k: v for k, v in node.items() if k not in {"id", "uuid", "type", "entity_type"}
                },
            )
        )

    # Convert facts to edges
    graph_edges = []
    for fact in facts:
        # Graphiti facts have source/target or from/to
        source = fact.get("source", fact.get("from", fact.get("source_id")))
        target = fact.get("target", fact.get("to", fact.get("target_id")))

        if source and target:
            graph_edges.append(
                Edge(
                    source=str(source),
                    target=str(target),
                    type=fact.get("type", fact.get("relation_type", "related")),
                    properties={
                        k: v
                        for k, v in fact.items()
                        if k not in {"source", "target", "from", "to", "type", "relation_type"}
                    },
                )
            )

    # Determine graph type
    g_type = GraphType.UNDIRECTED if graph_type.lower() == "undirected" else GraphType.DIRECTED

    logger.info(
        f"Converted Graphiti results to GraphArtifact: "
        f"{len(graph_nodes)} nodes, {len(graph_edges)} edges"
    )

    return GraphArtifact(
        nodes=graph_nodes,
        edges=graph_edges,
        graph_type=g_type,
        metadata={"source": "graphiti", "conversion": "cross_mcp_helper"},
    )


def networkx_metrics_to_annotations(
    metrics_artifact: "GraphMetricsArtifact", node_id_field: str = "id"
) -> dict[str, dict[str, float]]:
    """Convert NetworkX metrics to Graphiti node annotations.

    This helper enables the reverse flow: analyze graph with NetworkX,
    then annotate Graphiti nodes with computed metrics.

    Args:
        metrics_artifact: GraphMetricsArtifact from NetworkX analysis
        node_id_field: Field name for node IDs in Graphiti

    Returns:
        Dictionary mapping node IDs to annotation properties

    Example:
        # Analyze with NetworkX
        metrics = await networkx.pagerank(graph=graph_artifact.to_networkx())

        # Convert to annotations
        annotations = networkx_metrics_to_annotations(metrics)

        # Update Graphiti nodes
        for node_id, props in annotations.items():
            await graphiti.update_node(
                node_id=node_id,
                properties=props
            )
    """
    from sibyl.core.artifacts import GraphMetricsArtifact

    if not isinstance(metrics_artifact, GraphMetricsArtifact):
        msg = f"Expected GraphMetricsArtifact, got {type(metrics_artifact)}"
        raise TypeError(msg)

    annotations = {}
    for node in metrics_artifact.ranked_nodes:
        annotations[node.node_id] = {
            f"{metrics_artifact.algorithm}_score": node.score,
            f"{metrics_artifact.algorithm}_rank": node.rank,
            "metric_type": metrics_artifact.metric_type.value,
        }

        # Add community if available
        community_id = metrics_artifact.get_community_membership(node.node_id)
        if community_id is not None:
            annotations[node.node_id]["community_id"] = community_id

    logger.info(
        f"Generated annotations for {len(annotations)} nodes using {metrics_artifact.algorithm}"
    )

    return annotations


def chunkhound_to_rag_chunks(
    chunk_artifacts: list["ChunkArtifact"],
    include_context: bool = True,
    max_chunk_size: int | None = None,
) -> list[dict[str, Any]]:
    """Convert ChunkHound artifacts to RAG-compatible chunk format.

    This helper enables cAST-aware chunking integration with Sibyl RAG,
    leveraging ChunkHound's +4.3 Recall@5 improvement.

    Args:
        chunk_artifacts: List of ChunkArtifact instances from ChunkHound
        include_context: Whether to include docstrings/context in chunk text
        max_chunk_size: Optional maximum chunk size (truncate if exceeded)

    Returns:
        List of RAG-compatible chunk dictionaries

    Example:
        # Chunk with ChunkHound
        chunkhound_result = await chunkhound.chunk_file(file_path="src/utils.py")
        chunks = [ChunkArtifact.from_mcp_response(c) for c in chunkhound_result["chunks"]]

        # Convert to RAG format
        rag_chunks = chunkhound_to_rag_chunks(chunks)

        # Ingest into RAG
        await rag_system.ingest_chunks(rag_chunks)
    """
    from sibyl.core.artifacts import ChunkArtifact

    rag_chunks = []
    for chunk in chunk_artifacts:
        if not isinstance(chunk, ChunkArtifact):
            msg = f"Expected ChunkArtifact, got {type(chunk)}"
            raise TypeError(msg)

        # Use built-in to_rag_chunk method
        rag_chunk = chunk.to_rag_chunk()

        # Apply max_chunk_size if specified
        if max_chunk_size and len(rag_chunk["text"]) > max_chunk_size:
            rag_chunk["text"] = rag_chunk["text"][:max_chunk_size]
            rag_chunk["metadata"]["truncated"] = True

        rag_chunks.append(rag_chunk)

    logger.info("Converted %s ChunkHound artifacts to RAG format", len(rag_chunks))

    return rag_chunks


def pattern_to_recommendations(
    pattern_artifacts: list["PatternArtifact"],
    min_confidence: float = 0.7,
    min_frequency: int = 5,
    max_recommendations: int = 10,
) -> list[dict[str, Any]]:
    """Convert In-Memoria patterns to actionable recommendations.

    This helper transforms learned patterns into structured recommendations
    for code review, refactoring, or development guidance.

    Args:
        pattern_artifacts: List of PatternArtifact instances from In-Memoria
        min_confidence: Minimum confidence threshold for recommendations
        min_frequency: Minimum frequency threshold
        max_recommendations: Maximum number of recommendations to return

    Returns:
        List of recommendation dictionaries

    Example:
        # Learn patterns with In-Memoria
        inmemoria_result = await inmemoria.detect_patterns(directory="src/")
        patterns = [PatternArtifact.from_mcp_response(p) for p in inmemoria_result["patterns"]]

        # Generate recommendations
        recommendations = pattern_to_recommendations(patterns)

        # Present to developer
        for rec in recommendations:
            print(f"{rec['pattern']}: {rec['recommendation']}")
    """
    from sibyl.core.artifacts import PatternArtifact

    recommendations = []

    for pattern in pattern_artifacts:
        if not isinstance(pattern, PatternArtifact):
            msg = f"Expected PatternArtifact, got {type(pattern)}"
            raise TypeError(msg)

        # Filter by confidence and frequency
        if not pattern.is_high_confidence(threshold=min_confidence):
            continue
        if not pattern.is_frequent(min_frequency=min_frequency):
            continue

        # Generate recommendation
        recommendation = {
            "pattern": pattern.pattern_name,
            "category": pattern.category.value,
            "confidence": pattern.confidence,
            "frequency": pattern.frequency,
            "recommendation": _generate_recommendation_text(pattern),
            "examples": pattern.get_top_examples(n=3),
            "files": pattern.similar_files[:5],  # Top 5 files
        }

        recommendations.append(recommendation)

    # Sort by confidence * frequency (importance score)
    recommendations.sort(key=lambda r: r["confidence"] * r["frequency"], reverse=True)

    # Limit to max_recommendations
    recommendations = recommendations[:max_recommendations]

    logger.info(
        f"Generated {len(recommendations)} recommendations from {len(pattern_artifacts)} patterns"
    )

    return recommendations


def _generate_recommendation_text(pattern: "PatternArtifact") -> str:
    """Generate recommendation text from pattern.

    Args:
        pattern: PatternArtifact instance

    Returns:
        Human-readable recommendation text
    """
    category = pattern.category.value

    if category == "naming":
        return (
            f"Consistently use '{pattern.pattern_name}' naming convention. "
            f"Found in {pattern.frequency} occurrences across {len(pattern.similar_files)} files."
        )
    if category == "architectural":
        return (
            f"Follow '{pattern.pattern_name}' architectural pattern. "
            f"This pattern is well-established in your codebase with {pattern.confidence:.0%} confidence."
        )
    if category == "coding_convention":
        return (
            f"Adopt '{pattern.pattern_name}' coding convention. "
            f"Observed in {len(pattern.similar_files)} files with high consistency."
        )
    if category == "api_usage":
        return (
            f"Use '{pattern.pattern_name}' API usage pattern. "
            f"This is the standard approach in your codebase ({pattern.frequency} uses)."
        )
    if category == "error_handling":
        return (
            f"Apply '{pattern.pattern_name}' error handling pattern. "
            f"Consistently used with {pattern.confidence:.0%} confidence."
        )
    return (
        f"Consider applying '{pattern.pattern_name}' pattern. "
        f"Detected with {pattern.confidence:.0%} confidence in {pattern.frequency} locations."
    )


def timeseries_to_forecast_summary(
    timeseries_artifact: "TimeSeriesArtifact", horizon_points: int = 10
) -> dict[str, Any]:
    """Convert Chronulus time series to concise forecast summary.

    This helper extracts key insights from time series forecasts for
    decision-making and reporting.

    Args:
        timeseries_artifact: TimeSeriesArtifact from Chronulus
        horizon_points: Number of future points to include in summary

    Returns:
        Dictionary with forecast summary

    Example:
        # Forecast with Chronulus
        chronulus_result = await chronulus.forecast(data=historical_data)
        forecast = TimeSeriesArtifact.from_mcp_response(chronulus_result, "chronulus")

        # Get summary
        summary = timeseries_to_forecast_summary(forecast)
        print(f"Trend: {summary['trend']}, Peak: {summary['peak_value']} at {summary['peak_time']}")
    """
    from sibyl.core.artifacts import TimeSeriesArtifact

    if not isinstance(timeseries_artifact, TimeSeriesArtifact):
        msg = f"Expected TimeSeriesArtifact, got {type(timeseries_artifact)}"
        raise TypeError(msg)

    # Get recent and forecast data
    df = timeseries_artifact.data
    if len(df) == 0:
        return {"error": "Empty time series data"}

    # Calculate summary statistics
    recent_data = df.tail(horizon_points)

    summary = {
        "frequency": timeseries_artifact.frequency.value,
        "points_count": len(df),
        "recent_mean": float(recent_data["value"].mean()),
        "recent_std": float(recent_data["value"].std()),
        "trend": _detect_trend(recent_data["value"].tolist()),
        "peak_value": float(df["value"].max()),
        "peak_time": str(df.loc[df["value"].idxmax(), "timestamp"]),
        "min_value": float(df["value"].min()),
        "min_time": str(df.loc[df["value"].idxmin(), "timestamp"]),
    }

    # Add confidence intervals if available
    if timeseries_artifact.confidence_intervals is not None:
        ci = timeseries_artifact.confidence_intervals.tail(horizon_points)
        summary["confidence_range"] = {
            "lower": float(ci["lower"].mean()),
            "upper": float(ci["upper"].mean()),
        }

    logger.info("Generated forecast summary: trend=%s", summary["trend"])

    return summary


def _detect_trend(values: list[float]) -> str:
    """Detect trend direction from values.

    Args:
        values: List of numeric values

    Returns:
        Trend direction: "increasing", "decreasing", or "stable"
    """
    if len(values) < 2:
        return "stable"

    # Simple linear regression slope
    n = len(values)
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(values) / n

    numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return "stable"

    slope = numerator / denominator

    # Classify trend
    if slope > 0.1:
        return "increasing"
    if slope < -0.1:
        return "decreasing"
    return "stable"

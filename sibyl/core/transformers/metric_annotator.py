"""Metric annotators for enriching GraphArtifact with GraphMetricsArtifact data.

This module provides transformers that take GraphMetricsArtifact (from NetworkX
analysis) and annotate GraphArtifact nodes and edges with the computed metrics,
enabling rich graph visualization and downstream analysis.

Key features:
- Annotate nodes with PageRank, centrality, clustering scores
- Annotate nodes with community membership
- Add edge weights based on node metrics
- Support multiple metric types simultaneously
- Preserve original graph structure

Example:
    from sibyl.core.artifacts import GraphArtifact, GraphMetricsArtifact
    from sibyl.core.transformers.metric_annotator import (
        annotate_graph_with_metric_artifact,
        annotate_with_communities
    )

    # Get graph and compute metrics
    graph = GraphArtifact.from_graphiti_search(nodes, facts)
    nx_graph = graph.to_networkx()
    import networkx as nx
    pr = nx.pagerank(nx_graph)

    # Create metrics artifact
    metrics = GraphMetricsArtifact.from_networkx_result(
        scores=pr,
        algorithm="pagerank"
    )

    # Annotate graph
    annotated_graph = annotate_graph_with_metric_artifact(graph, metrics)

    # Nodes now have PageRank scores
    for node in annotated_graph.nodes:
        print(f"{node.id}: {node.properties['pagerank']:.4f}")
"""

from copy import deepcopy
from typing import Any

from sibyl.core.artifacts import (
    GraphArtifact,
    GraphMetricsArtifact,
    MetricType,
    Node,
)


def annotate_graph_with_metric_artifact(
    graph: GraphArtifact,
    metrics: GraphMetricsArtifact,
    metric_prefix: str | None = None,
    overwrite_existing: bool = True,
) -> GraphArtifact:
    """Annotate graph nodes with scores from GraphMetricsArtifact.

    This is the main transformer for enriching graphs with computed metrics.
    It adds metric scores and ranks as node properties.

    Args:
        graph: GraphArtifact to annotate
        metrics: GraphMetricsArtifact with computed scores
        metric_prefix: Optional prefix for metric property names (e.g., "nx_")
        overwrite_existing: If True, overwrite existing properties with same name

    Returns:
        New GraphArtifact with annotated nodes

    Example:
        # Single metric
        pagerank_metrics = GraphMetricsArtifact.from_networkx_result(
            scores=nx.pagerank(nx_graph),
            algorithm="pagerank"
        )
        annotated = annotate_graph_with_metric_artifact(graph, pagerank_metrics)

        # With prefix to avoid conflicts
        annotated = annotate_graph_with_metric_artifact(
            graph,
            metrics,
            metric_prefix="nx_"
        )
        # Adds properties: nx_pagerank, nx_pagerank_rank
    """
    # Determine property names
    metric_name = metrics.algorithm
    if metric_prefix:
        score_key = f"{metric_prefix}{metric_name}"
        rank_key = f"{metric_prefix}{metric_name}_rank"
    else:
        score_key = metric_name
        rank_key = f"{metric_name}_rank"

    # Create new nodes with added metrics
    new_nodes = []
    for node in graph.nodes:
        # Deep copy node to avoid mutation
        new_properties = deepcopy(node.properties)

        # Check if we should overwrite
        if not overwrite_existing:
            if score_key in new_properties or rank_key in new_properties:
                # Skip this node
                new_nodes.append(Node(node.id, node.type, new_properties))
                continue

        # Add score
        score = metrics.get_node_score(node.id)
        if score != 0.0:  # Only add if node has a score
            new_properties[score_key] = score

        # Add rank
        rank = metrics.get_node_rank(node.id)
        if rank is not None:
            new_properties[rank_key] = rank

        new_nodes.append(Node(node.id, node.type, new_properties))

    # Create new graph
    new_metadata = {
        **graph.metadata,
        "annotated_metrics": [*graph.metadata.get("annotated_metrics", []), metric_name],
    }

    return GraphArtifact(
        nodes=new_nodes,
        edges=graph.edges,  # Edges unchanged
        graph_type=graph.graph_type,
        metadata=new_metadata,
    )


def annotate_with_communities(
    graph: GraphArtifact, metrics: GraphMetricsArtifact, community_prefix: str = "community_"
) -> GraphArtifact:
    """Annotate graph nodes with community membership from GraphMetricsArtifact.

    Adds community ID and size as node properties.

    Args:
        graph: GraphArtifact to annotate
        metrics: GraphMetricsArtifact with community detection results
        community_prefix: Prefix for community properties

    Returns:
        New GraphArtifact with community annotations

    Raises:
        ValueError: If metrics artifact has no community data

    Example:
        # Detect communities
        communities = nx.community.louvain_communities(nx_graph)
        metrics = GraphMetricsArtifact.from_networkx_result(
            scores={},  # No node scores
            algorithm="louvain",
            metric_type=MetricType.COMMUNITY_DETECTION,
            communities=[list(c) for c in communities]
        )

        # Annotate graph
        annotated = annotate_with_communities(graph, metrics)

        # Nodes now have: community_id, community_size
        for node in annotated.nodes:
            cid = node.properties.get("community_id")
            if cid is not None:
                print(f"{node.id} belongs to community {cid}")
    """
    if not metrics.communities:
        msg = (
            "GraphMetricsArtifact has no community data. "
            "Use metric_type=COMMUNITY_DETECTION when creating artifact."
        )
        raise ValueError(msg)

    # Build node -> community mapping
    node_to_community = {}
    community_sizes = {}

    for community in metrics.communities:
        cid = community.community_id
        size = community.size
        community_sizes[cid] = size

        for node_id in community.nodes:
            node_to_community[node_id] = cid

    # Create new nodes with community info
    new_nodes = []
    for node in graph.nodes:
        new_properties = deepcopy(node.properties)

        cid = node_to_community.get(node.id)
        if cid is not None:
            new_properties[f"{community_prefix}id"] = cid
            new_properties[f"{community_prefix}size"] = community_sizes[cid]

        new_nodes.append(Node(node.id, node.type, new_properties))

    # Create new graph
    new_metadata = {
        **graph.metadata,
        "has_communities": True,
        "community_count": len(metrics.communities),
    }

    return GraphArtifact(
        nodes=new_nodes, edges=graph.edges, graph_type=graph.graph_type, metadata=new_metadata
    )


def annotate_with_multiple_metrics(
    graph: GraphArtifact, metrics_list: list[GraphMetricsArtifact], metric_prefix: str | None = None
) -> GraphArtifact:
    """Annotate graph with multiple metric artifacts.

    Convenience function for applying multiple metrics at once.

    Args:
        graph: GraphArtifact to annotate
        metrics_list: List of GraphMetricsArtifact instances
        metric_prefix: Optional prefix for all metric properties

    Returns:
        New GraphArtifact with all metrics annotated

    Example:
        # Compute multiple metrics
        pagerank = GraphMetricsArtifact.from_networkx_result(
            nx.pagerank(nx_graph), "pagerank"
        )
        centrality = GraphMetricsArtifact.from_networkx_result(
            nx.betweenness_centrality(nx_graph), "betweenness_centrality"
        )

        # Annotate with all metrics
        annotated = annotate_with_multiple_metrics(
            graph,
            [pagerank, centrality]
        )

        # Nodes have both metrics
        for node in annotated.nodes:
            print(f"{node.id}:")
            print(f"  PageRank: {node.properties.get('pagerank')}")
            print(f"  Centrality: {node.properties.get('betweenness_centrality')}")
    """
    result = graph

    for metrics in metrics_list:
        # Check if it's a community metric
        if metrics.metric_type == MetricType.COMMUNITY_DETECTION and metrics.communities:
            result = annotate_with_communities(result, metrics)
        else:
            result = annotate_graph_with_metric_artifact(
                result, metrics, metric_prefix=metric_prefix
            )

    return result


def extract_metric_summary(
    graph: GraphArtifact, metric_names: list[str] | None = None
) -> dict[str, Any]:
    """Extract summary statistics for annotated metrics.

    Useful for understanding metric distributions across the graph.

    Args:
        graph: Annotated GraphArtifact
        metric_names: Optional list of metric names to summarize (all if None)

    Returns:
        Dictionary with summary statistics per metric

    Example:
        # After annotating
        annotated = annotate_graph_with_metric_artifact(graph, pagerank_metrics)

        # Get summary
        summary = extract_metric_summary(annotated, ["pagerank"])
        print(f"PageRank stats: {summary['pagerank']}")
        # Output: {"min": 0.01, "max": 0.45, "mean": 0.15, "count": 10}
    """
    # Collect all metric names if not specified
    if metric_names is None:
        metric_names = set()
        for node in graph.nodes:
            for key in node.properties:
                if not key.endswith("_rank"):  # Skip rank properties
                    metric_names.add(key)
        metric_names = list(metric_names)

    summary = {}

    for metric_name in metric_names:
        values = []
        for node in graph.nodes:
            value = node.properties.get(metric_name)
            if value is not None and isinstance(value, (int, float)):
                values.append(value)

        if values:
            summary[metric_name] = {
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
                "count": len(values),
                "total_nodes": len(graph.nodes),
                "coverage": len(values) / len(graph.nodes),
            }

    return summary


def rank_nodes_by_metric(
    graph: GraphArtifact, metric_name: str, top_k: int | None = None
) -> list[tuple[Node, float]]:
    """Rank nodes by a specific metric from annotated graph.

    Args:
        graph: Annotated GraphArtifact
        metric_name: Name of metric to rank by
        top_k: Optional limit on number of results

    Returns:
        List of (Node, score) tuples sorted by score (descending)

    Example:
        # Get top 5 nodes by PageRank
        top_nodes = rank_nodes_by_metric(annotated_graph, "pagerank", top_k=5)
        for node, score in top_nodes:
            print(f"{node.id}: {score:.4f}")
    """
    # Collect nodes with this metric
    node_scores = []
    for node in graph.nodes:
        score = node.properties.get(metric_name)
        if score is not None and isinstance(score, (int, float)):
            node_scores.append((node, score))

    # Sort by score descending
    node_scores.sort(key=lambda x: x[1], reverse=True)

    # Apply top_k limit
    if top_k:
        node_scores = node_scores[:top_k]

    return node_scores


def filter_graph_by_metric(
    graph: GraphArtifact,
    metric_name: str,
    min_value: float | None = None,
    max_value: float | None = None,
    top_k: int | None = None,
) -> GraphArtifact:
    """Filter graph to keep only nodes meeting metric criteria.

    Useful for focusing on high-importance nodes.

    Args:
        graph: Annotated GraphArtifact
        metric_name: Name of metric to filter by
        min_value: Optional minimum metric value
        max_value: Optional maximum metric value
        top_k: Optional keep only top K nodes

    Returns:
        New GraphArtifact with filtered nodes and edges

    Example:
        # Keep only high PageRank nodes
        filtered = filter_graph_by_metric(
            annotated_graph,
            "pagerank",
            min_value=0.05  # Only nodes with PR > 0.05
        )

        # Or keep top 10
        filtered = filter_graph_by_metric(
            annotated_graph,
            "pagerank",
            top_k=10
        )
    """
    # Rank nodes
    ranked_nodes = rank_nodes_by_metric(graph, metric_name)

    # Apply filters
    filtered_nodes = []
    for node, score in ranked_nodes:
        if min_value is not None and score < min_value:
            continue
        if max_value is not None and score > max_value:
            continue
        filtered_nodes.append(node)

    # Apply top_k
    if top_k:
        filtered_nodes = filtered_nodes[:top_k]

    # Build set of kept node IDs
    kept_node_ids = {node.id for node in filtered_nodes}

    # Filter edges to only those connecting kept nodes
    filtered_edges = [
        edge
        for edge in graph.edges
        if edge.source in kept_node_ids and edge.target in kept_node_ids
    ]

    return GraphArtifact(
        nodes=filtered_nodes,
        edges=filtered_edges,
        graph_type=graph.graph_type,
        metadata={
            **graph.metadata,
            "filtered_by": metric_name,
            "original_node_count": len(graph.nodes),
            "filtered_node_count": len(filtered_nodes),
        },
    )


__all__ = [
    "annotate_graph_with_metric_artifact",
    "annotate_with_communities",
    "annotate_with_multiple_metrics",
    "extract_metric_summary",
    "filter_graph_by_metric",
    "rank_nodes_by_metric",
]

"""Graph transformation utilities for cross-MCP workflows.

This module provides utilities for transforming graph data between different
representations, particularly for Graphiti → NetworkX analysis pipelines.

Most heavy lifting is done by GraphArtifact from sibyl.core.artifacts.graph.
This module adds convenience utilities for common transformation patterns.

Example:
    from sibyl.core.artifacts import GraphArtifact
    from sibyl.core.transformers.graph import annotate_graph_with_metrics, extract_top_nodes
    import networkx as nx

    # Step 1: Convert Graphiti results to graph
    graph = GraphArtifact.from_graphiti_search(nodes_result, facts_result)

    # Step 2: Analyze with NetworkX
    nx_graph = graph.to_networkx()
    pagerank = nx.pagerank(nx_graph)
    centrality = nx.betweenness_centrality(nx_graph)

    # Step 3: Annotate graph with metrics
    annotated = annotate_graph_with_metrics(
        graph,
        {
            "pagerank": pagerank,
            "betweenness_centrality": centrality
        }
    )

    # Step 4: Extract top nodes
    top_nodes = extract_top_nodes(annotated, "pagerank", top_k=5)
    for node in top_nodes:
        print(f"{node.id}: PageRank={node.properties['pagerank']:.4f}")
"""

from copy import deepcopy
from typing import Any

from sibyl.core.artifacts.graph import GraphArtifact, Node


def annotate_graph_with_metrics(
    graph: GraphArtifact, metrics: dict[str, dict[str, Any]]
) -> GraphArtifact:
    """Add NetworkX metric results as node annotations.

    This function takes a GraphArtifact and NetworkX metric results, and returns
    a new GraphArtifact with the metrics added to node properties. This enables
    pipelines that run NetworkX analysis and then use the enriched graph downstream.

    The function is immutable - it returns a new GraphArtifact rather than modifying
    the input graph.

    Args:
        graph: GraphArtifact to annotate
        metrics: Dict mapping metric names to node->value dicts.
                 Each metric is a dict where keys are node IDs and values are metric scores.
                 Example:
                 {
                     "pagerank": {"node1": 0.5, "node2": 0.3},
                     "betweenness_centrality": {"node1": 0.2, "node2": 0.8}
                 }

    Returns:
        New GraphArtifact with updated node properties. Each metric is added as a
        property with the metric name as key.

    Raises:
        ValueError: If metrics dict is empty or contains invalid structure

    Example:
        # Run NetworkX analysis
        graph = GraphArtifact.from_graphiti_search(nodes, facts)
        nx_graph = graph.to_networkx()

        import networkx as nx
        pagerank = nx.pagerank(nx_graph)
        centrality = nx.betweenness_centrality(nx_graph)
        clustering = nx.clustering(nx_graph)

        # Add all metrics to graph
        annotated = annotate_graph_with_metrics(
            graph,
            {
                "pagerank": pagerank,
                "betweenness_centrality": centrality,
                "clustering_coefficient": clustering
            }
        )

        # Access metrics from nodes
        for node in annotated.nodes:
            print(f"{node.id}:")
            print(f"  PageRank: {node.properties.get('pagerank', 'N/A')}")
            print(f"  Centrality: {node.properties.get('betweenness_centrality', 'N/A')}")

    Note:
        - Nodes not in metric results will not have that metric added
        - Existing properties are preserved
        - If a property with the metric name already exists, it will be overwritten
    """
    if not metrics:
        msg = "Metrics dict cannot be empty"
        raise ValueError(msg)

    # Validate metrics structure
    for metric_name, metric_values in metrics.items():
        if not isinstance(metric_values, dict):
            msg = (
                f"Metric '{metric_name}' must be a dict mapping node IDs to values, "
                f"got {type(metric_values).__name__}"
            )
            raise TypeError(msg)

    # Create new nodes with added metrics
    new_nodes = []
    for node in graph.nodes:
        # Deep copy node to avoid mutation
        new_node = Node(id=node.id, type=node.type, properties=deepcopy(node.properties))

        # Add metrics for this node
        for metric_name, metric_values in metrics.items():
            if node.id in metric_values:
                new_node.properties[metric_name] = metric_values[node.id]

        new_nodes.append(new_node)

    # Return new graph with updated nodes
    return GraphArtifact(
        nodes=new_nodes,
        edges=graph.edges,  # Edges unchanged
        graph_type=graph.graph_type,
        metadata={**graph.metadata, "annotated_metrics": list(metrics.keys())},
    )


def extract_top_nodes(graph: GraphArtifact, metric_name: str, top_k: int = 10) -> list[Node]:
    """Extract top K nodes by a specific metric.

    This function sorts nodes by a metric value and returns the top K nodes.
    Useful for extracting most important/central nodes after NetworkX analysis.

    Args:
        graph: GraphArtifact with metric annotations (from annotate_graph_with_metrics)
        metric_name: Name of metric to sort by. Must exist in node.properties for at least one node.
        top_k: Number of top nodes to return. Default is 10.

    Returns:
        List of top K nodes sorted by metric value in descending order.
        If fewer than K nodes have the metric, returns all nodes with the metric.
        Returns empty list if no nodes have the metric.

    Raises:
        ValueError: If metric_name is empty or top_k is non-positive

    Example:
        # After annotating graph with PageRank
        annotated = annotate_graph_with_metrics(
            graph,
            {"pagerank": nx.pagerank(nx_graph)}
        )

        # Get top 5 nodes by PageRank
        top_nodes = extract_top_nodes(annotated, "pagerank", top_k=5)

        print("Top 5 nodes by PageRank:")
        for i, node in enumerate(top_nodes, 1):
            score = node.properties["pagerank"]
            print(f"{i}. {node.id}: {score:.4f}")

    Example with multiple metrics:
        # Get top nodes by different metrics
        top_by_pagerank = extract_top_nodes(graph, "pagerank", 5)
        top_by_centrality = extract_top_nodes(graph, "betweenness_centrality", 5)

        # Compare results
        pagerank_ids = {n.id for n in top_by_pagerank}
        centrality_ids = {n.id for n in top_by_centrality}
        overlap = pagerank_ids & centrality_ids
        print(f"Overlap between top 5 PageRank and Centrality: {overlap}")
    """
    if not metric_name:
        msg = "metric_name cannot be empty"
        raise ValueError(msg)

    if top_k <= 0:
        msg = f"top_k must be positive, got {top_k}"
        raise ValueError(msg)

    # Filter nodes that have the metric
    nodes_with_metric = [node for node in graph.nodes if metric_name in node.properties]

    if not nodes_with_metric:
        # No nodes have this metric - return empty list
        return []

    # Sort by metric value (descending)
    sorted_nodes = sorted(nodes_with_metric, key=lambda n: n.properties[metric_name], reverse=True)

    # Return top K
    return sorted_nodes[:top_k]


def merge_graph_artifacts(*graphs: GraphArtifact, deduplicate_nodes: bool = True) -> GraphArtifact:
    """Merge multiple GraphArtifacts into a single graph.

    This utility is useful when combining results from multiple Graphiti searches
    or merging subgraphs from different sources.

    Args:
        *graphs: Variable number of GraphArtifact instances to merge
        deduplicate_nodes: If True, merge nodes with the same ID (keeping first occurrence's properties).
                          If False, keep all nodes (may result in duplicate IDs).
                          Default is True.

    Returns:
        New GraphArtifact containing all nodes and edges from input graphs.
        Graph type is taken from the first graph.
        Metadata is merged (later graphs override earlier ones for duplicate keys).

    Raises:
        ValueError: If no graphs provided or graphs have incompatible types

    Example:
        # Search multiple entity types
        graph1 = GraphArtifact.from_graphiti_search(
            search_nodes(query="users"),
            search_facts(query="user relationships")
        )

        graph2 = GraphArtifact.from_graphiti_search(
            search_nodes(query="services"),
            search_facts(query="service dependencies")
        )

        # Merge into single graph
        combined = merge_graph_artifacts(graph1, graph2)

        # Analyze combined graph
        nx_graph = combined.to_networkx()
        communities = nx.community.louvain_communities(nx_graph)

    Note:
        - All graphs must have the same graph_type (DIRECTED or UNDIRECTED)
        - Edge deduplication is not performed - duplicate edges will be kept
        - Node properties from first occurrence are kept when deduplicating
    """
    if not graphs:
        msg = "At least one graph must be provided"
        raise ValueError(msg)

    if len(graphs) == 1:
        # Single graph - return copy
        return GraphArtifact(
            nodes=list(graphs[0].nodes),
            edges=list(graphs[0].edges),
            graph_type=graphs[0].graph_type,
            metadata=deepcopy(graphs[0].metadata),
        )

    # Verify all graphs have same type
    first_type = graphs[0].graph_type
    for i, g in enumerate(graphs[1:], 1):
        if g.graph_type != first_type:
            msg = (
                f"Graph {i} has type {g.graph_type}, but graph 0 has type {first_type}. "
                f"Cannot merge graphs with different types."
            )
            raise ValueError(msg)

    # Collect all nodes
    all_nodes = []
    seen_node_ids = set()

    for graph in graphs:
        for node in graph.nodes:
            if deduplicate_nodes:
                if node.id not in seen_node_ids:
                    all_nodes.append(node)
                    seen_node_ids.add(node.id)
            else:
                all_nodes.append(node)

    # Collect all edges (no deduplication)
    all_edges = []
    for graph in graphs:
        all_edges.extend(graph.edges)

    # Merge metadata (later graphs override earlier ones)
    merged_metadata = {}
    for graph in graphs:
        merged_metadata.update(graph.metadata)

    merged_metadata["merged_from_count"] = len(graphs)

    return GraphArtifact(
        nodes=all_nodes, edges=all_edges, graph_type=first_type, metadata=merged_metadata
    )


__all__ = [
    "annotate_graph_with_metrics",
    "extract_top_nodes",
    "merge_graph_artifacts",
]

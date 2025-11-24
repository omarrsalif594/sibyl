"""Graph Artifact for graph structure outputs.

This module provides typed artifacts for graph structures from MCP tools like
Graphiti and NetworkX. It enables type-safe graph manipulation and conversion
to standard graph libraries.

Example:
    from sibyl.core.artifacts.graph import GraphArtifact, Node, Edge, GraphType

    # Create from Graphiti search
    graph = GraphArtifact.from_graphiti_search(nodes_result, facts_result)

    # Convert to NetworkX for analysis
    nx_graph = graph.to_networkx()
    import networkx as nx
    pagerank = nx.pagerank(nx_graph)

    # Or convert to adjacency matrix (requires numpy)
    matrix = graph.to_adjacency_matrix()
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass
class Node:
    """Graph node with properties.

    Attributes:
        id: Unique node identifier
        type: Node type (e.g., "entity", "service", "document")
        properties: Additional node properties (arbitrary key-value pairs)

    Example:
        node = Node(
            id="user_123",
            type="user",
            properties={"name": "Alice", "created_at": "2023-01-01"}
        )
    """

    id: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Make node hashable by ID for use in sets and dicts."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Check equality based on ID."""
        if not isinstance(other, Node):
            return NotImplemented
        return self.id == other.id


@dataclass
class Edge:
    """Graph edge with properties.

    Attributes:
        source: Source node ID
        target: Target node ID
        type: Edge type (e.g., "depends_on", "relates_to", "authored_by")
        properties: Additional edge properties (arbitrary key-value pairs)
        weight: Edge weight (default 1.0)

    Example:
        edge = Edge(
            source="service_a",
            target="service_b",
            type="depends_on",
            properties={"since": "2023-01-01"},
            weight=0.8
        )
    """

    source: str
    target: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0


class GraphType(Enum):
    """Graph directionality type."""

    DIRECTED = "directed"
    UNDIRECTED = "undirected"


@dataclass
class GraphArtifact:
    """Artifact for graph structures.

    This artifact provides a typed interface to graph data with conversion
    utilities for NetworkX and adjacency matrices.

    Attributes:
        nodes: List of graph nodes
        edges: List of graph edges
        graph_type: Graph directionality (DIRECTED or UNDIRECTED)
        metadata: Additional graph metadata (source, timestamps, etc.)

    Example:
        graph = GraphArtifact(
            nodes=[
                Node("A", "service"),
                Node("B", "service")
            ],
            edges=[
                Edge("A", "B", "depends_on")
            ],
            graph_type=GraphType.DIRECTED
        )

        nx_graph = graph.to_networkx()
    """

    nodes: list[Node]
    edges: list[Edge]
    graph_type: GraphType
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_networkx(self) -> Any:  # Returns nx.Graph but typed as Any to avoid hard dep
        """Convert to NetworkX graph.

        Creates either a directed or undirected NetworkX graph based on
        the graph_type attribute. Node and edge properties are preserved.

        Returns:
            NetworkX Graph (nx.Graph) or DiGraph (nx.DiGraph) instance

        Raises:
            ImportError: If networkx is not installed

        Example:
            nx_graph = graph.to_networkx()
            import networkx as nx
            pagerank = nx.pagerank(nx_graph)
            centrality = nx.betweenness_centrality(nx_graph)
        """
        try:
            import networkx as nx  # optional dependency

        except ImportError as e:
            msg = (
                "networkx is required for graph conversion. "
                "It should be installed as part of sibyl dependencies. "
                "If missing, install with: pip install networkx"
            )
            raise ImportError(msg) from e

        # Create appropriate graph type
        G = nx.DiGraph() if self.graph_type == GraphType.DIRECTED else nx.Graph()

        # Add nodes with properties
        for node in self.nodes:
            G.add_node(node.id, type=node.type, **node.properties)

        # Add edges with properties
        for edge in self.edges:
            G.add_edge(
                edge.source, edge.target, type=edge.type, weight=edge.weight, **edge.properties
            )

        return G

    def to_adjacency_matrix(self) -> Any:  # Returns np.ndarray but typed as Any
        """Convert to adjacency matrix.

        Creates a numpy adjacency matrix representation of the graph.
        For undirected graphs, the matrix is symmetric.

        Returns:
            numpy.ndarray: Square adjacency matrix (n x n where n = number of nodes)

        Raises:
            ImportError: If numpy is not installed

        Example:
            matrix = graph.to_adjacency_matrix()
            # Use for mathematical graph operations
            eigenvalues = np.linalg.eigvals(matrix)
        """
        try:
            import numpy as np  # optional dependency

        except ImportError as e:
            msg = (
                "numpy is required for adjacency matrix conversion. Install with: pip install numpy"
            )
            raise ImportError(msg) from e

        # Create node ID to index mapping
        node_ids = [node.id for node in self.nodes]
        id_to_idx = {node_id: idx for idx, node_id in enumerate(node_ids)}

        # Create matrix
        n = len(self.nodes)
        matrix = np.zeros((n, n))

        # Fill matrix with edge weights
        for edge in self.edges:
            if edge.source in id_to_idx and edge.target in id_to_idx:
                i = id_to_idx[edge.source]
                j = id_to_idx[edge.target]
                matrix[i, j] = edge.weight

                # For undirected graphs, make symmetric
                if self.graph_type == GraphType.UNDIRECTED:
                    matrix[j, i] = edge.weight

        return matrix

    @classmethod
    def from_graphiti_search(
        cls, nodes_response: dict[str, Any], facts_response: dict[str, Any]
    ) -> "GraphArtifact":
        """Create GraphArtifact from Graphiti search results.

        Graphiti returns nodes and facts (edges) in separate responses.
        This method combines them into a unified graph structure.

        Args:
            nodes_response: Response from Graphiti search_nodes tool
            facts_response: Response from Graphiti search_facts tool

        Returns:
            GraphArtifact instance

        Example:
            # Step 1: Search Graphiti
            nodes_result = await mcp_adapter(
                provider="graphiti",
                tool="search_nodes",
                params={"query": "API services"}
            )

            facts_result = await mcp_adapter(
                provider="graphiti",
                tool="search_facts",
                params={"query": "dependencies"}
            )

            # Step 2: Convert to graph
            graph = GraphArtifact.from_graphiti_search(
                nodes_result,
                facts_result
            )

        Note:
            Graphiti graphs are always directed.
        """
        # Parse nodes
        nodes = []
        for node_data in nodes_response.get("results", []):
            node = Node(
                id=node_data.get("node_id", node_data.get("id", "")),
                type=node_data.get("type", "entity"),
                properties={
                    "name": node_data.get("name"),
                    "summary": node_data.get("summary"),
                    "created_at": node_data.get("created_at"),
                },
            )
            # Remove None values from properties
            node.properties = {k: v for k, v in node.properties.items() if v is not None}
            nodes.append(node)

        # Parse edges (facts)
        edges = []
        for fact_data in facts_response.get("results", []):
            edge = Edge(
                source=fact_data.get("source_node", fact_data.get("source", "")),
                target=fact_data.get("target_node", fact_data.get("target", "")),
                type=fact_data.get("relationship_type", fact_data.get("type", "relates_to")),
                properties={
                    "created_at": fact_data.get("temporal_context", {}).get("created_at"),
                    "fact_id": fact_data.get("fact_id"),
                },
            )
            # Remove None values from properties
            edge.properties = {k: v for k, v in edge.properties.items() if v is not None}
            edges.append(edge)

        return cls(
            nodes=nodes, edges=edges, graph_type=GraphType.DIRECTED, metadata={"source": "graphiti"}
        )

    @classmethod
    def from_mcp_response(cls, response: dict[str, Any]) -> "GraphArtifact":
        """Create GraphArtifact from generic MCP graph response.

        This method handles generic graph responses that have nodes and edges
        in a single response object (unlike Graphiti which separates them).

        Args:
            response: MCP response containing graph data

        Returns:
            GraphArtifact instance

        Example:
            # From generic graph MCP tool
            result = await mcp_adapter(tool="get_graph", ...)
            graph = GraphArtifact.from_mcp_response(result)

        Note:
            Expected response format:
            {
                "nodes": [...],
                "edges": [...],
                "graph_type": "directed" or "undirected"
            }
        """
        # Parse nodes
        nodes = []
        for node_data in response.get("nodes", []):
            node = Node(
                id=node_data.get("id", ""),
                type=node_data.get("type", "node"),
                properties=node_data.get("properties", {}),
            )
            nodes.append(node)

        # Parse edges
        edges = []
        for edge_data in response.get("edges", []):
            edge = Edge(
                source=edge_data.get("source", ""),
                target=edge_data.get("target", ""),
                type=edge_data.get("type", "edge"),
                properties=edge_data.get("properties", {}),
                weight=float(edge_data.get("weight", 1.0)),
            )
            edges.append(edge)

        # Parse graph type
        graph_type_str = response.get("graph_type", "directed").lower()
        graph_type = GraphType.DIRECTED if graph_type_str == "directed" else GraphType.UNDIRECTED

        # Extract metadata
        metadata = {k: v for k, v in response.items() if k not in {"nodes", "edges", "graph_type"}}

        return cls(nodes=nodes, edges=edges, graph_type=graph_type, metadata=metadata)

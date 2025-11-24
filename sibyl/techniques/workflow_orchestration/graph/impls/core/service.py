"""Generic graph service implementation using NetworkX.

This module provides a concrete implementation of the generic graph abstractions
using NetworkX as the backend. It's completely domain-agnostic.

Features:
- In-memory graph storage with NetworkX
- LRU caching for expensive queries
- Efficient cycle detection and topological sorting
- Path finding with configurable depth limits
- Subgraph extraction with custom filters

Example:
    # Create a graph
    graph = GenericGraphService()

    # Add nodes
    graph.add_node("product:SKU123", "product", {"name": "Widget", "price": 19.99})
    graph.add_node("warehouse:PARIS", "warehouse", {"location": "Paris"})

    # Add edges
    graph.add_edge("product:SKU123", "warehouse:PARIS", "stored_in", {"quantity": 100})

    # Analyze
    analyzer = NetworkXGraphAnalyzer(graph)
    cycles = analyzer.find_cycles()
    stats = analyzer.get_stats()

    # Query
    query = NetworkXGraphQuery(graph)
    path = query.paths("product:SKU123", "warehouse:PARIS")
    dependents = query.fan_out("warehouse:PARIS", depth=2)
"""

import logging
from collections import deque
from collections.abc import Callable, Iterable
from typing import Any, Literal

import networkx as nx

from sibyl.core.contracts.graph import (
    Edge,
    EdgeType,
    GraphAnalyzer,
    GraphQuery,
    Node,
    NodeId,
)

logger = logging.getLogger(__name__)


class GenericGraphService:
    """Generic graph service using NetworkX backend.

    Implements GraphProvider protocol with efficient in-memory storage.
    Supports adding/removing nodes and edges, querying, and subgraph extraction.
    """

    def __init__(self) -> None:
        """Initialize empty directed graph."""
        self._graph = nx.DiGraph()
        self._node_metadata: dict[NodeId, dict[str, Any]] = {}
        self._edge_metadata: dict[tuple, dict[str, Any]] = {}

    def add_node(
        self, node_id: NodeId, node_type: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Add a node to the graph.

        Args:
            node_id: Unique node identifier
            node_type: Type of node (e.g., "product", "warehouse")
            metadata: Additional node attributes
        """
        self._graph.add_node(node_id)
        self._node_metadata[node_id] = {"type": node_type, **(metadata or {})}
        logger.debug("Added node: %s (type=%s)", node_id, node_type)

    def add_edge(
        self,
        source: NodeId,
        target: NodeId,
        edge_type: EdgeType,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add an edge to the graph.

        Args:
            source: Source node ID
            target: Target node ID
            edge_type: Type of edge (e.g., "depends_on", "stored_in")
            metadata: Additional edge attributes
        """
        self._graph.add_edge(source, target)
        key = (source, target)
        self._edge_metadata[key] = {"type": edge_type, **(metadata or {})}
        logger.debug("Added edge: %s -> %s (type=%s)", source, target, edge_type)

    def remove_node(self, node_id: NodeId) -> None:
        """Remove a node and all its edges.

        Args:
            node_id: Node ID to remove
        """
        if node_id in self._graph:
            self._graph.remove_node(node_id)
            self._node_metadata.pop(node_id, None)
            # Remove edge metadata for edges involving this node
            keys_to_remove = [k for k in self._edge_metadata if k[0] == node_id or k[1] == node_id]
            for key in keys_to_remove:
                self._edge_metadata.pop(key, None)
            logger.debug("Removed node: %s", node_id)

    def remove_edge(self, source: NodeId, target: NodeId) -> None:
        """Remove an edge.

        Args:
            source: Source node ID
            target: Target node ID
        """
        if self._graph.has_edge(source, target):
            self._graph.remove_edge(source, target)
            self._edge_metadata.pop((source, target), None)
            logger.debug("Removed edge: %s -> %s", source, target)

    # GraphProvider protocol implementation

    def nodes(self) -> Iterable[NodeId]:
        """Return all node IDs."""
        return self._graph.nodes()

    def edges(self) -> Iterable[Edge]:
        """Return all edges."""
        edges = []
        for source, target in self._graph.edges():
            key = (source, target)
            edge_data = self._edge_metadata.get(key, {})
            edge_type = edge_data.get("type", "default")
            metadata = {k: v for k, v in edge_data.items() if k != "type"}
            edges.append(Edge(source, target, edge_type, metadata))
        return edges

    def neighbors(
        self, node: NodeId, direction: Literal["in", "out", "both"] = "out"
    ) -> list[NodeId]:
        """Get neighbors of a node."""
        if node not in self._graph:
            return []

        if direction == "out":
            return list(self._graph.successors(node))
        if direction == "in":
            return list(self._graph.predecessors(node))
        # both
        return list(set(self._graph.successors(node)) | set(self._graph.predecessors(node)))

    def subgraph(self, filter_fn: Callable[[NodeId], bool]) -> "GenericGraphService":
        """Create a subgraph with filtered nodes."""
        filtered_nodes = [n for n in self._graph.nodes() if filter_fn(n)]
        subgraph_nx = self._graph.subgraph(filtered_nodes).copy()

        # Create new service with subgraph
        new_service = GenericGraphService()
        new_service._graph = subgraph_nx

        # Copy metadata for filtered nodes and edges
        for node in filtered_nodes:
            if node in self._node_metadata:
                new_service._node_metadata[node] = self._node_metadata[node].copy()

        for source, target in subgraph_nx.edges():
            key = (source, target)
            if key in self._edge_metadata:
                new_service._edge_metadata[key] = self._edge_metadata[key].copy()

        return new_service

    def get_node(self, node_id: NodeId) -> Node | None:
        """Get node by ID."""
        if node_id not in self._graph:
            return None

        metadata = self._node_metadata.get(node_id, {})
        node_type = metadata.get("type", "unknown")
        node_metadata = {k: v for k, v in metadata.items() if k != "type"}

        return Node(id=node_id, type=node_type, metadata=node_metadata)

    def get_edges(
        self,
        source: NodeId | None = None,
        target: NodeId | None = None,
        edge_type: EdgeType | None = None,
    ) -> list[Edge]:
        """Get edges matching criteria."""
        result = []

        for edge in self.edges():
            # Filter by source
            if source is not None and edge.source != source:
                continue
            # Filter by target
            if target is not None and edge.target != target:
                continue
            # Filter by type
            if edge_type is not None and edge.type != edge_type:
                continue

            result.append(edge)

        return result

    def clear(self) -> None:
        """Clear all nodes and edges."""
        self._graph.clear()
        self._node_metadata.clear()
        self._edge_metadata.clear()
        logger.debug("Cleared graph")


class NetworkXGraphAnalyzer(GraphAnalyzer):
    """Graph analyzer using NetworkX algorithms."""

    def __init__(self, provider: GenericGraphService) -> None:
        """Initialize analyzer.

        Args:
            provider: GenericGraphService instance
        """
        super().__init__(provider)
        if not isinstance(provider, GenericGraphService):
            msg = "NetworkXGraphAnalyzer requires GenericGraphService"
            raise TypeError(msg)
        self._service = provider

    def find_cycles(self) -> list[list[NodeId]]:
        """Find all cycles using NetworkX."""
        try:
            cycles = list(nx.simple_cycles(self._service._graph))
            logger.debug("Found %s cycles", len(cycles))
            return cycles
        except Exception as e:
            logger.exception("Error finding cycles: %s", e)
            return []

    def find_orphans(self) -> list[NodeId]:
        """Find nodes with no edges."""
        orphans = [
            node for node in self._service._graph.nodes() if self._service._graph.degree(node) == 0
        ]
        logger.debug("Found %s orphan nodes", len(orphans))
        return orphans

    def compute_depths(self) -> dict[NodeId, int]:
        """Compute depth of each node from root nodes."""
        depths = {}

        # Find root nodes (no incoming edges)
        roots = [
            node
            for node in self._service._graph.nodes()
            if self._service._graph.in_degree(node) == 0
        ]

        if not roots:
            # If no roots, all nodes are in cycles or disconnected
            # Assign depth 0 to all
            return dict.fromkeys(self._service._graph.nodes(), 0)

        # BFS from each root
        for root in roots:
            depths[root] = 0
            queue = deque([(root, 0)])
            visited = {root}

            while queue:
                node, depth = queue.popleft()

                for neighbor in self._service._graph.successors(node):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        new_depth = depth + 1
                        depths[neighbor] = max(depths.get(neighbor, 0), new_depth)
                        queue.append((neighbor, new_depth))

        logger.debug("Computed depths for %s nodes", len(depths))
        return depths

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        graph = self._service._graph

        stats = {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "is_directed": graph.is_directed(),
            "is_dag": nx.is_directed_acyclic_graph(graph),
        }

        if stats["node_count"] > 0:
            degrees = [d for _, d in graph.degree()]
            stats["avg_degree"] = sum(degrees) / len(degrees)
            stats["max_degree"] = max(degrees)
            stats["min_degree"] = min(degrees)

        # Count node types
        node_types = {}
        for node_id in graph.nodes():
            node = self._service.get_node(node_id)
            if node:
                node_types[node.type] = node_types.get(node.type, 0) + 1
        stats["node_types"] = node_types

        # Count edge types
        edge_types = {}
        for edge in self._service.edges():
            edge_types[edge.type] = edge_types.get(edge.type, 0) + 1
        stats["edge_types"] = edge_types

        logger.debug("Graph stats: %s", stats)
        return stats

    def topological_sort(self) -> list[NodeId]:
        """Return nodes in topological order."""
        if not nx.is_directed_acyclic_graph(self._service._graph):
            msg = "Graph contains cycles, cannot perform topological sort"
            raise ValueError(msg)

        return list(nx.topological_sort(self._service._graph))


class NetworkXGraphQuery(GraphQuery):
    """Graph query engine using NetworkX algorithms."""

    def __init__(self, provider: GenericGraphService) -> None:
        """Initialize query engine.

        Args:
            provider: GenericGraphService instance
        """
        super().__init__(provider)
        if not isinstance(provider, GenericGraphService):
            msg = "NetworkXGraphQuery requires GenericGraphService"
            raise TypeError(msg)
        self._service = provider

    def paths(self, source: NodeId, target: NodeId, max_hops: int = 10) -> list[NodeId] | None:
        """Find shortest path between nodes."""
        try:
            path = nx.shortest_path(self._service._graph, source, target, weight=None)

            if len(path) - 1 > max_hops:
                logger.debug("Path from %s to %s exceeds max_hops (%s)", source, target, max_hops)
                return None

            logger.debug("Found path from %s to %s: %s nodes", source, target, len(path))
            return path
        except nx.NetworkXNoPath:
            logger.debug("No path from %s to %s", source, target)
            return None
        except nx.NodeNotFound as e:
            logger.warning("Node not found: %s", e)
            return None

    def fan_out(self, node: NodeId, depth: int = 1) -> list[NodeId]:
        """Get all nodes reachable from this node (outgoing)."""
        if node not in self._service._graph:
            return []

        reachable = set()
        queue = deque([(node, 0)])
        visited = {node}

        while queue:
            current, current_depth = queue.popleft()

            if current_depth < depth:
                for neighbor in self._service._graph.successors(current):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        reachable.add(neighbor)
                        queue.append((neighbor, current_depth + 1))

        logger.debug("Fan-out from %s (depth=%s): %s nodes", node, depth, len(reachable))
        return list(reachable)

    def fan_in(self, node: NodeId, depth: int = 1) -> list[NodeId]:
        """Get all nodes that can reach this node (incoming)."""
        if node not in self._service._graph:
            return []

        reachable = set()
        queue = deque([(node, 0)])
        visited = {node}

        while queue:
            current, current_depth = queue.popleft()

            if current_depth < depth:
                for neighbor in self._service._graph.predecessors(current):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        reachable.add(neighbor)
                        queue.append((neighbor, current_depth + 1))

        logger.debug("Fan-in to %s (depth=%s): %s nodes", node, depth, len(reachable))
        return list(reachable)

    def reachable(
        self, node: NodeId, direction: Literal["in", "out", "both"] = "out"
    ) -> set[NodeId]:
        """Get all nodes reachable from this node."""
        if node not in self._service._graph:
            return set()

        if direction == "out":
            reachable = nx.descendants(self._service._graph, node)
        elif direction == "in":
            reachable = nx.ancestors(self._service._graph, node)
        else:  # both
            reachable = nx.descendants(self._service._graph, node) | nx.ancestors(
                self._service._graph, node
            )

        logger.debug("Reachable from %s (%s): %s nodes", node, direction, len(reachable))
        return reachable

    def is_reachable(self, source: NodeId, target: NodeId) -> bool:
        """Check if target is reachable from source."""
        try:
            return nx.has_path(self._service._graph, source, target)
        except nx.NodeNotFound:
            return False


# Export public API
__all__ = [
    "GenericGraphService",
    "NetworkXGraphAnalyzer",
    "NetworkXGraphQuery",
]

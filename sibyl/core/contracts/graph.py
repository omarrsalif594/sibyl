"""Generic graph abstraction - domain-agnostic graph operations.

This module provides pure generic graph primitives with NO domain assumptions.
Use terminology: node, entity, dependency, edge - NOT model, table, lineage, upstream/downstream.

Key features:
- Generic node/edge representation
- Graph provider protocol for pluggable backends
- Graph analysis (cycles, orphans, depths)
- Graph queries (paths, fan-out, fan-in)

Example usage:
    # Build a graph
    provider = GenericGraphProvider()
    provider.add_node("product:SKU123", {"type": "product", "name": "Widget"})
    provider.add_node("warehouse:PARIS", {"type": "warehouse", "location": "Paris"})
    provider.add_edge("product:SKU123", "warehouse:PARIS", "stored_in", {})

    # Analyze
    analyzer = GraphAnalyzer(provider)
    cycles = analyzer.find_cycles()
    orphans = analyzer.find_orphans()

    # Query
    query = GraphQuery(provider)
    path = query.paths("product:SKU123", "warehouse:PARIS", max_hops=5)
    dependents = query.fan_out("warehouse:PARIS", depth=2)
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

# Type aliases for clarity
NodeId = str
EdgeType = str


@dataclass(frozen=True)
class Edge:
    """Generic edge connecting two nodes.

    Attributes:
        source: Source node ID
        target: Target node ID
        type: Edge type (e.g., "depends_on", "stored_in", "supplies")
        metadata: Additional edge attributes
    """

    source: NodeId
    target: NodeId
    type: EdgeType
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Node:
    """Generic node in the graph.

    Attributes:
        id: Unique node identifier
        type: Node type (e.g., "product", "warehouse", "supplier")
        metadata: Additional node attributes
    """

    id: NodeId
    type: str
    metadata: dict[str, Any] = field(default_factory=dict)


class GraphProvider(Protocol):
    """Generic graph operations - no domain assumptions.

    This protocol defines the interface for graph storage and basic operations.
    Implementations can use NetworkX, adjacency lists, databases, etc.
    """

    def nodes(self) -> Iterable[NodeId]:
        """Return all node IDs in the graph."""
        ...

    def edges(self) -> Iterable[Edge]:
        """Return all edges in the graph."""
        ...

    def neighbors(
        self, node: NodeId, direction: Literal["in", "out", "both"] = "out"
    ) -> list[NodeId]:
        """Get neighbors of a node.

        Args:
            node: Node ID
            direction: Direction to traverse ("in", "out", "both")

        Returns:
            List of neighbor node IDs
        """
        ...

    def subgraph(self, filter_fn: Callable[[NodeId], bool]) -> "GraphProvider":
        """Create a subgraph containing only nodes matching the filter.

        Args:
            filter_fn: Function that returns True for nodes to include

        Returns:
            New GraphProvider with filtered nodes and their edges
        """
        ...

    def get_node(self, node_id: NodeId) -> Node | None:
        """Get node by ID.

        Args:
            node_id: Node ID

        Returns:
            Node if found, None otherwise
        """
        ...

    def get_edges(
        self,
        source: NodeId | None = None,
        target: NodeId | None = None,
        edge_type: EdgeType | None = None,
    ) -> list[Edge]:
        """Get edges matching criteria.

        Args:
            source: Filter by source node (optional)
            target: Filter by target node (optional)
            edge_type: Filter by edge type (optional)

        Returns:
            List of matching edges
        """
        ...


class GraphAnalyzer(ABC):
    """Generic graph analysis - domain-agnostic algorithms.

    Provides common graph analysis operations like cycle detection,
    orphan finding, depth computation, etc.
    """

    def __init__(self, provider: GraphProvider) -> None:
        """Initialize analyzer with a graph provider.

        Args:
            provider: Graph provider to analyze
        """
        self.provider = provider

    @abstractmethod
    def find_cycles(self) -> list[list[NodeId]]:
        """Find all cycles in the graph.

        Returns:
            List of cycles, where each cycle is a list of node IDs
        """
        ...

    @abstractmethod
    def find_orphans(self) -> list[NodeId]:
        """Find nodes with no incoming or outgoing edges.

        Returns:
            List of orphan node IDs
        """
        ...

    @abstractmethod
    def compute_depths(self) -> dict[NodeId, int]:
        """Compute depth of each node from root nodes.

        Depth is the length of the longest path from any root node.
        Root nodes have depth 0.

        Returns:
            Dictionary mapping node ID to depth
        """
        ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics.

        Returns:
            Dictionary with stats like node_count, edge_count, avg_degree, etc.
        """
        ...

    @abstractmethod
    def topological_sort(self) -> list[NodeId]:
        """Return nodes in topological order.

        Returns:
            List of node IDs in topological order

        Raises:
            ValueError: If graph contains cycles
        """
        ...


class GraphQuery(ABC):
    """Generic graph queries - domain-agnostic traversals.

    Provides path finding, reachability, and traversal operations.
    """

    def __init__(self, provider: GraphProvider) -> None:
        """Initialize query engine with a graph provider.

        Args:
            provider: Graph provider to query
        """
        self.provider = provider

    @abstractmethod
    def paths(self, source: NodeId, target: NodeId, max_hops: int = 10) -> list[NodeId] | None:
        """Find shortest path between two nodes.

        Args:
            source: Source node ID
            target: Target node ID
            max_hops: Maximum path length to search

        Returns:
            List of node IDs forming the path, or None if no path exists
        """
        ...

    @abstractmethod
    def fan_out(self, node: NodeId, depth: int = 1) -> list[NodeId]:
        """Get all nodes reachable from this node (outgoing edges).

        Args:
            node: Starting node ID
            depth: Maximum depth to traverse

        Returns:
            List of reachable node IDs (excluding the starting node)
        """
        ...

    @abstractmethod
    def fan_in(self, node: NodeId, depth: int = 1) -> list[NodeId]:
        """Get all nodes that can reach this node (incoming edges).

        Args:
            node: Target node ID
            depth: Maximum depth to traverse

        Returns:
            List of node IDs that can reach the target (excluding target)
        """
        ...

    @abstractmethod
    def reachable(
        self, node: NodeId, direction: Literal["in", "out", "both"] = "out"
    ) -> set[NodeId]:
        """Get all nodes reachable from this node.

        Args:
            node: Starting node ID
            direction: Direction to traverse

        Returns:
            Set of reachable node IDs (excluding the starting node)
        """
        ...

    @abstractmethod
    def is_reachable(self, source: NodeId, target: NodeId) -> bool:
        """Check if target is reachable from source.

        Args:
            source: Source node ID
            target: Target node ID

        Returns:
            True if target is reachable from source
        """
        ...


# Export public API
__all__ = [
    "Edge",
    "EdgeType",
    "GraphAnalyzer",
    "GraphProvider",
    "GraphQuery",
    "Node",
    "NodeId",
]

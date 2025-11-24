"""Graph technique protocols and shared types.

This module defines the protocol interfaces and data structures for graph operations.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class Node:
    """Graph node."""

    id: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """Graph edge."""

    source: str
    target: str
    label: str = ""
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Graph:
    """Graph data structure."""

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)

    def get_neighbors(self, node_id: str) -> list[str]:
        """Get neighbor node IDs for a given node."""
        neighbors = []
        for edge in self.edges:
            if edge.source == node_id:
                neighbors.append(edge.target)
            elif edge.target == node_id:
                neighbors.append(edge.source)
        return neighbors


@runtime_checkable
class GraphBackend(Protocol):
    """Protocol for graph storage and management."""

    @property
    def name(self) -> str:
        """Backend name for identification."""
        ...

    async def store_graph(self, graph: Graph) -> bool:
        """Store a graph.

        Args:
            graph: Graph to store

        Returns:
            True if successful
        """
        ...

    async def load_graph(self, graph_id: str) -> Graph | None:
        """Load a graph by ID.

        Args:
            graph_id: Graph identifier

        Returns:
            Graph if found, None otherwise
        """
        ...


@runtime_checkable
class GraphAnalyzer(Protocol):
    """Protocol for graph analysis algorithms."""

    @property
    def name(self) -> str:
        """Analyzer name for identification."""
        ...

    async def analyze(self, graph: Graph, config: dict[str, Any]) -> dict[str, Any]:
        """Analyze a graph.

        Args:
            graph: Graph to analyze
            config: Analysis configuration

        Returns:
            Analysis results
        """
        ...

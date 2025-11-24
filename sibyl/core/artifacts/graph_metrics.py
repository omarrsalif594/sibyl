"""Graph Metrics Artifact for graph analysis results.

This module provides typed artifacts for graph metrics computed by NetworkX MCP
and other graph analysis tools. It includes PageRank scores, centrality measures,
community detection results, and other graph metrics.

Example:
    from sibyl.core.artifacts.graph_metrics import GraphMetricsArtifact, RankedNode

    # Create from NetworkX PageRank
    metrics = GraphMetricsArtifact.from_mcp_response(
        response={"pagerank": {"node_a": 0.25, "node_b": 0.15}},
        algorithm="pagerank"
    )

    # Get top nodes
    top_nodes = metrics.get_top_nodes(n=10)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MetricType(Enum):
    """Types of graph metrics."""

    PAGERANK = "pagerank"
    BETWEENNESS_CENTRALITY = "betweenness_centrality"
    CLOSENESS_CENTRALITY = "closeness_centrality"
    DEGREE_CENTRALITY = "degree_centrality"
    EIGENVECTOR_CENTRALITY = "eigenvector_centrality"
    CLUSTERING_COEFFICIENT = "clustering_coefficient"
    COMMUNITY_DETECTION = "community_detection"
    OTHER = "other"


@dataclass
class RankedNode:
    """A node with its metric score and rank.

    Attributes:
        node_id: Node identifier
        score: Metric score (e.g., PageRank value, centrality score)
        rank: Rank position (1 = highest score)
        properties: Additional node properties (type, name, etc.)

    Example:
        node = RankedNode(
            node_id="service_a",
            score=0.25,
            rank=1,
            properties={"type": "api_gateway", "name": "API Gateway"}
        )
    """

    node_id: str
    score: float
    rank: int
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Community:
    """A community (cluster) in a graph.

    Attributes:
        community_id: Community identifier (0-indexed)
        nodes: List of node IDs in this community
        size: Number of nodes in the community
        properties: Additional community properties (modularity, cohesion, etc.)

    Example:
        community = Community(
            community_id=0,
            nodes=["node_a", "node_b", "node_c"],
            size=3,
            properties={"modularity": 0.42}
        )
    """

    community_id: int
    nodes: list[str]
    size: int = field(init=False)
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Calculate size after initialization."""
        self.size = len(self.nodes)


@dataclass
class GraphMetricsArtifact:
    """Artifact for graph analysis metrics.

    This artifact represents computed graph metrics like PageRank, centrality
    measures, or community detection results from NetworkX or similar tools.

    Attributes:
        algorithm: Algorithm name (e.g., "pagerank", "betweenness_centrality")
        metric_type: Type of metric computed
        scores: Dictionary mapping node IDs to their scores
        ranked_nodes: List of nodes sorted by score (highest first)
        communities: Optional list of detected communities
        computation_time_ms: Time taken to compute metrics
        parameters: Algorithm parameters used
        metadata: Additional metadata (graph size, algorithm version, etc.)

    Example:
        metrics = GraphMetricsArtifact(
            algorithm="pagerank",
            metric_type=MetricType.PAGERANK,
            scores={"node_a": 0.25, "node_b": 0.15},
            ranked_nodes=[
                RankedNode("node_a", 0.25, 1),
                RankedNode("node_b", 0.15, 2)
            ],
            computation_time_ms=123,
            parameters={"alpha": 0.85}
        )

        top_nodes = metrics.get_top_nodes(n=5)
    """

    algorithm: str
    metric_type: MetricType
    scores: dict[str, float]
    ranked_nodes: list[RankedNode] = field(default_factory=list)
    communities: list[Community] | None = None
    computation_time_ms: int = 0
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Compute ranked nodes if not provided."""
        if not self.ranked_nodes and self.scores:
            # Sort by score descending
            sorted_items = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
            self.ranked_nodes = [
                RankedNode(node_id=node_id, score=score, rank=rank)
                for rank, (node_id, score) in enumerate(sorted_items, start=1)
            ]

    def get_top_nodes(self, n: int = 10) -> list[RankedNode]:
        """Get top N nodes by score.

        Args:
            n: Number of top nodes to return

        Returns:
            List of top n ranked nodes

        Example:
            top_5 = metrics.get_top_nodes(n=5)
            for node in top_5:
                print(f"{node.rank}. {node.node_id}: {node.score:.4f}")
        """
        return self.ranked_nodes[:n]

    def get_node_score(self, node_id: str, default: float = 0.0) -> float:
        """Get score for a specific node.

        Args:
            node_id: Node identifier
            default: Default value if node not found

        Returns:
            Node's score or default value

        Example:
            score = metrics.get_node_score("node_a")
        """
        return self.scores.get(node_id, default)

    def get_node_rank(self, node_id: str) -> int | None:
        """Get rank for a specific node.

        Args:
            node_id: Node identifier

        Returns:
            Node's rank (1-indexed) or None if not found

        Example:
            rank = metrics.get_node_rank("node_a")
            if rank:
                print(f"Node ranked #{rank}")
        """
        for node in self.ranked_nodes:
            if node.node_id == node_id:
                return node.rank
        return None

    def get_community_membership(self, node_id: str) -> int | None:
        """Get community ID for a specific node.

        Args:
            node_id: Node identifier

        Returns:
            Community ID (0-indexed) or None if not in any community

        Example:
            community_id = metrics.get_community_membership("node_a")
            if community_id is not None:
                print(f"Node belongs to community {community_id}")
        """
        if not self.communities:
            return None

        for community in self.communities:
            if node_id in community.nodes:
                return community.community_id
        return None

    def get_community(self, community_id: int) -> Community | None:
        """Get community by ID.

        Args:
            community_id: Community identifier (0-indexed)

        Returns:
            Community object or None if not found

        Example:
            community = metrics.get_community(0)
            if community:
                print(f"Community has {community.size} nodes")
        """
        if not self.communities:
            return None

        for community in self.communities:
            if community.community_id == community_id:
                return community
        return None

    def summarize_for_llm(self, max_nodes: int = 10, include_communities: bool = True) -> str:
        """Generate LLM-friendly summary of the metrics.

        Creates a concise text summary suitable for inclusion in LLM prompts,
        including top nodes, scores, and community structure.

        Args:
            max_nodes: Maximum number of top nodes to include
            include_communities: Whether to include community information

        Returns:
            Formatted string summary

        Example:
            summary = metrics.summarize_for_llm(max_nodes=5)
            llm_prompt = f"Analyze these metrics:\\n{summary}\\nWhat are the bottlenecks?"
        """
        lines = [
            f"Algorithm: {self.algorithm}",
            f"Metric Type: {self.metric_type.value}",
            f"Total Nodes: {len(self.scores)}",
            f"Computation Time: {self.computation_time_ms}ms",
        ]

        # Add parameters if present
        if self.parameters:
            params_str = ", ".join(f"{k}={v}" for k, v in self.parameters.items())
            lines.append(f"Parameters: {params_str}")

        # Add top nodes
        top_nodes = self.get_top_nodes(max_nodes)
        if top_nodes:
            lines.append(f"\nTop {len(top_nodes)} Nodes:")
            for node in top_nodes:
                lines.append(f"  {node.rank}. {node.node_id}: {node.score:.4f}")

        # Add community information
        if include_communities and self.communities:
            lines.append(f"\nCommunities Detected: {len(self.communities)}")
            for community in sorted(self.communities, key=lambda c: c.size, reverse=True)[:5]:
                lines.append(
                    f"  Community {community.community_id}: "
                    f"{community.size} nodes ({', '.join(community.nodes[:3])}...)"
                )

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize artifact to dictionary.

        Returns:
            Dictionary representation of the artifact

        Example:
            data = metrics.to_dict()
            json.dumps(data)
        """
        result = {
            "algorithm": self.algorithm,
            "metric_type": self.metric_type.value,
            "scores": self.scores,
            "ranked_nodes": [
                {
                    "node_id": node.node_id,
                    "score": node.score,
                    "rank": node.rank,
                    "properties": node.properties,
                }
                for node in self.ranked_nodes
            ],
            "computation_time_ms": self.computation_time_ms,
            "parameters": self.parameters,
            "metadata": self.metadata,
        }

        if self.communities:
            result["communities"] = [
                {
                    "community_id": c.community_id,
                    "nodes": c.nodes,
                    "size": c.size,
                    "properties": c.properties,
                }
                for c in self.communities
            ]

        return result

    @classmethod
    def from_mcp_response(
        cls, response: dict[str, Any], algorithm: str, metric_type: MetricType | None = None
    ) -> "GraphMetricsArtifact":
        """Create GraphMetricsArtifact from MCP response.

        This factory method handles various response formats from graph analysis
        MCP tools like NetworkX, normalizing them to a standard artifact structure.

        Args:
            response: Raw response dictionary from MCP graph analysis tool
            algorithm: Algorithm name (e.g., "pagerank", "betweenness_centrality")
            metric_type: Optional metric type (inferred from algorithm if not provided)

        Returns:
            GraphMetricsArtifact instance

        Example:
            # From NetworkX PageRank
            mcp_result = await mcp_adapter(
                provider="networkx",
                tool="pagerank",
                params={"graph": graph_data}
            )

            metrics = GraphMetricsArtifact.from_mcp_response(
                mcp_result,
                algorithm="pagerank"
            )

            # From community detection
            communities_result = await mcp_adapter(
                provider="networkx",
                tool="community_detection",
                params={"graph": graph_data}
            )

            metrics = GraphMetricsArtifact.from_mcp_response(
                communities_result,
                algorithm="louvain",
                metric_type=MetricType.COMMUNITY_DETECTION
            )

        Note:
            Expected response formats:

            For centrality metrics:
            {
                "pagerank": {"node_a": 0.25, "node_b": 0.15},
                "computation_time_ms": 123,
                "parameters": {"alpha": 0.85}
            }

            For community detection:
            {
                "communities": [
                    ["node_a", "node_b"],
                    ["node_c", "node_d"]
                ],
                "modularity": 0.42
            }
        """
        # Infer metric type from algorithm if not provided
        if metric_type is None:
            algo_lower = algorithm.lower()
            if "pagerank" in algo_lower:
                metric_type = MetricType.PAGERANK
            elif "betweenness" in algo_lower:
                metric_type = MetricType.BETWEENNESS_CENTRALITY
            elif "closeness" in algo_lower:
                metric_type = MetricType.CLOSENESS_CENTRALITY
            elif "degree" in algo_lower:
                metric_type = MetricType.DEGREE_CENTRALITY
            elif "eigenvector" in algo_lower:
                metric_type = MetricType.EIGENVECTOR_CENTRALITY
            elif "clustering" in algo_lower:
                metric_type = MetricType.CLUSTERING_COEFFICIENT
            elif "community" in algo_lower or "louvain" in algo_lower:
                metric_type = MetricType.COMMUNITY_DETECTION
            else:
                metric_type = MetricType.OTHER

        # Extract scores
        # NetworkX often returns results under the algorithm name
        scores = response.get(algorithm, response.get("scores", response.get("results", {})))

        # Handle various response formats
        if not isinstance(scores, dict):
            # Might be wrapped in a "data" field
            scores = response.get("data", {})

        # Still not a dict? Empty scores
        if not isinstance(scores, dict):
            scores = {}

        # Extract computation time
        computation_time_ms = int(response.get("computation_time_ms", 0))

        # Extract parameters
        parameters = response.get("parameters", response.get("params", {}))
        if not isinstance(parameters, dict):
            parameters = {}

        # Extract metadata
        metadata = {}
        for key in ["graph_size", "num_nodes", "num_edges", "version"]:
            if key in response:
                metadata[key] = response[key]

        # Parse communities if present
        communities = None
        if "communities" in response or metric_type == MetricType.COMMUNITY_DETECTION:
            communities = []
            communities_data = response.get("communities", [])

            for i, community_nodes in enumerate(communities_data):
                if isinstance(community_nodes, list):
                    community_props = {}
                    # Extract modularity or other community metrics
                    if "modularity" in response:
                        community_props["modularity"] = response["modularity"]

                    communities.append(
                        Community(community_id=i, nodes=community_nodes, properties=community_props)
                    )

        return cls(
            algorithm=algorithm,
            metric_type=metric_type,
            scores=scores,
            communities=communities,
            computation_time_ms=computation_time_ms,
            parameters=parameters,
            metadata=metadata,
        )

    @classmethod
    def from_networkx_result(
        cls,
        scores: dict[str, float],
        algorithm: str,
        metric_type: MetricType | None = None,
        communities: list[list[str]] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> "GraphMetricsArtifact":
        """Create GraphMetricsArtifact directly from NetworkX results.

        Convenience factory method for when you already have NetworkX results
        in memory (not from MCP).

        Args:
            scores: Dictionary of node scores
            algorithm: Algorithm name
            metric_type: Metric type (inferred if not provided)
            communities: Optional list of communities (each is a list of node IDs)
            parameters: Optional algorithm parameters

        Returns:
            GraphMetricsArtifact instance

        Example:
            import networkx as nx

            # Compute PageRank
            G = nx.karate_club_graph()
            pr = nx.pagerank(G, alpha=0.85)

            # Create artifact
            metrics = GraphMetricsArtifact.from_networkx_result(
                scores=pr,
                algorithm="pagerank",
                parameters={"alpha": 0.85}
            )
        """
        # Parse communities
        parsed_communities = None
        if communities:
            parsed_communities = [
                Community(community_id=i, nodes=list(nodes), properties={})
                for i, nodes in enumerate(communities)
            ]

        return cls(
            algorithm=algorithm,
            metric_type=metric_type or MetricType.OTHER,
            scores=scores,
            communities=parsed_communities,
            parameters=parameters or {},
            metadata={"source": "networkx_direct"},
        )

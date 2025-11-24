"""Cluster-based diversity reranking.

This implementation groups similar items into clusters and selects
diverse representatives from different clusters to maximize coverage
and minimize redundancy.
"""

import re
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.reranking.protocols import RankedItem, RerankingResult


class ClusterBasedReranking:
    """Cluster-based diversity reranking implementation."""

    def __init__(self) -> None:
        self._name = "cluster_based"
        self._description = "Cluster-based diversity reranking using content similarity"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> RerankingResult:
        """Execute cluster-based diversity reranking.

        Args:
            input_data: Dict with 'query', 'items', 'top_k', 'diversity_factor'
            config: Merged configuration

        Returns:
            RerankingResult with diverse reranked items from different clusters
        """
        query: str = input_data.get("query", "")
        items: list[dict[str, Any]] = input_data.get("items", [])
        top_k: int = input_data.get("top_k", 10)
        diversity_factor: float = input_data.get(
            "diversity_factor", config.get("diversity_factor", 0.5)
        )

        if not query or not items:
            return RerankingResult(
                ranked_items=[],
                query=query,
                reranking_method="diversity_rerank:cluster_based",
                total_items=0,
                metadata={"error": "Empty query or no items"},
            )

        # Prepare items with term representations
        processed_items = []
        for idx, item in enumerate(items):
            content = item.get("content", "")
            content_terms = set(self._tokenize(content.lower()))

            processed_items.append(
                {
                    "item": item,
                    "content_terms": content_terms,
                    "original_rank": idx + 1,
                    "cluster_id": None,
                }
            )

        # Cluster items based on similarity
        similarity_threshold = config.get("similarity_threshold", 0.3)
        clusters = self._cluster_items(processed_items, similarity_threshold)

        # Select diverse items from clusters
        selected_items = self._select_from_clusters(
            clusters, processed_items, query, top_k, diversity_factor, config
        )

        # Create ranked items
        ranked_items = []
        for rank, item_data in enumerate(selected_items, start=1):
            item = item_data["item"]
            ranked_items.append(
                RankedItem(
                    id=item.get("id", ""),
                    content=item.get("content", ""),
                    score=float(item_data.get("score", 0.0)),
                    rank=rank,
                    original_rank=item_data["original_rank"],
                    metadata={
                        **item.get("metadata", {}),
                        "cluster_id": item_data["cluster_id"],
                        "original_score": item.get("score", 0.0),
                    },
                )
            )

        return RerankingResult(
            ranked_items=ranked_items,
            query=query,
            reranking_method="diversity_rerank:cluster_based",
            total_items=len(items),
            metadata={
                "top_k": top_k,
                "num_clusters": len(clusters),
                "diversity_factor": diversity_factor,
                "similarity_threshold": similarity_threshold,
                "reranked_items": len(ranked_items),
            },
        )

    def _cluster_items(
        self, items: list[dict[str, Any]], similarity_threshold: float
    ) -> list[list[int]]:
        """Simple clustering using greedy approach based on similarity threshold.

        Returns:
            List of clusters, where each cluster is a list of item indices
        """
        clusters = []
        assigned = set()

        for i, item in enumerate(items):
            if i in assigned:
                continue

            # Start a new cluster with this item
            cluster = [i]
            assigned.add(i)

            # Find similar items to add to this cluster
            for j, other_item in enumerate(items):
                if j in assigned:
                    continue

                similarity = self._calculate_similarity(
                    item["content_terms"], other_item["content_terms"]
                )

                if similarity >= similarity_threshold:
                    cluster.append(j)
                    assigned.add(j)

            clusters.append(cluster)

            # Assign cluster IDs
            for idx in cluster:
                items[idx]["cluster_id"] = len(clusters) - 1

        return clusters

    def _select_from_clusters(
        self,
        clusters: list[list[int]],
        items: list[dict[str, Any]],
        query: str,
        top_k: int,
        diversity_factor: float,
        config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Select diverse items from clusters balancing relevance and coverage.

        Strategy:
        - Sort clusters by their best relevance score
        - Round-robin select from clusters, picking best item from each
        - Balance between cluster coverage (diversity) and item relevance
        """
        query_terms = set(self._tokenize(query.lower()))

        # Calculate cluster scores (best item score in cluster)
        cluster_scores = []
        for cluster_id, cluster in enumerate(clusters):
            best_score = -1
            best_item_idx = -1

            for item_idx in cluster:
                item_data = items[item_idx]
                relevance = self._calculate_relevance(
                    query_terms,
                    item_data["content_terms"],
                    item_data["item"].get("score", 0.0),
                    config,
                )

                if relevance > best_score:
                    best_score = relevance
                    best_item_idx = item_idx

            cluster_scores.append(
                {
                    "cluster_id": cluster_id,
                    "best_score": best_score,
                    "best_item_idx": best_item_idx,
                    "size": len(cluster),
                    "items": cluster,
                }
            )

        # Sort clusters by best score (most relevant first)
        cluster_scores.sort(key=lambda x: x["best_score"], reverse=True)

        # Select items using round-robin from clusters
        selected = []
        cluster_pointers = {cs["cluster_id"]: 0 for cs in cluster_scores}

        # Calculate how many items to select from top clusters vs. all clusters
        # Higher diversity_factor = select from more clusters
        num_active_clusters = max(1, int(len(clusters) * (0.5 + 0.5 * diversity_factor)))

        round_idx = 0
        while len(selected) < top_k:
            # Determine which clusters to consider this round
            if round_idx == 0:
                # First round: pick best from each of top clusters
                active_clusters = cluster_scores[:num_active_clusters]
            else:
                # Subsequent rounds: continue round-robin
                active_clusters = [
                    cs for cs in cluster_scores if cluster_pointers[cs["cluster_id"]] < cs["size"]
                ]

            if not active_clusters:
                break

            for cluster_data in active_clusters:
                if len(selected) >= top_k:
                    break

                cluster_id = cluster_data["cluster_id"]
                pointer = cluster_pointers[cluster_id]

                if pointer >= cluster_data["size"]:
                    continue

                # Get next item from this cluster
                item_indices = cluster_data["items"]

                # Sort items in cluster by relevance
                cluster_items_sorted = sorted(
                    item_indices,
                    key=lambda idx: self._calculate_relevance(
                        query_terms,
                        items[idx]["content_terms"],
                        items[idx]["item"].get("score", 0.0),
                        config,
                    ),
                    reverse=True,
                )

                if pointer < len(cluster_items_sorted):
                    item_idx = cluster_items_sorted[pointer]
                    item_data = items[item_idx]

                    # Calculate score
                    relevance = self._calculate_relevance(
                        query_terms,
                        item_data["content_terms"],
                        item_data["item"].get("score", 0.0),
                        config,
                    )

                    selected.append({**item_data, "score": relevance})

                    cluster_pointers[cluster_id] += 1

            round_idx += 1

        return selected

    def _calculate_relevance(
        self,
        query_terms: set[str],
        content_terms: set[str],
        original_score: float,
        config: dict[str, Any],
    ) -> float:
        """Calculate relevance score."""
        if not query_terms or not content_terms:
            return 0.0

        # Calculate term overlap
        overlap = len(query_terms & content_terms)
        coverage = overlap / len(query_terms)

        # Use original score if configured
        use_original = config.get("use_original_score", True)
        if use_original and original_score > 0:
            return 0.5 * coverage + 0.5 * original_score
        return coverage

    def _calculate_similarity(self, terms1: set[str], terms2: set[str]) -> float:
        """Calculate Jaccard similarity between two term sets."""
        if not terms1 or not terms2:
            return 0.0

        intersection = len(terms1 & terms2)
        union = len(terms1 | terms2)

        return intersection / union if union > 0 else 0.0

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization by splitting on whitespace and punctuation."""
        text = re.sub(r"[^\w\s]", " ", text)
        return [token for token in text.split() if token]

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {
            "similarity_threshold": 0.3,  # Threshold for clustering
            "diversity_factor": 0.5,  # 0=max relevance, 1=max diversity
            "use_original_score": True,
        }

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "similarity_threshold" in config:
            if not (0 <= config["similarity_threshold"] <= 1):
                return False

        return not ("diversity_factor" in config and not 0 <= config["diversity_factor"] <= 1)

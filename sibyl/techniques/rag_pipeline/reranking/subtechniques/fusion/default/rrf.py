"""Reciprocal Rank Fusion (RRF) implementation.

RRF is a simple but effective method for combining multiple ranked lists.
It uses the formula: score(item) = sum(1 / (k + rank_i)) across all lists
where the item appears, with k being a constant (typically 60).
"""

from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.reranking.protocols import RankedItem, RerankingResult


class RRFFusion:
    """Reciprocal Rank Fusion implementation for combining multiple result lists."""

    def __init__(self) -> None:
        self._name = "rrf"
        self._description = "Reciprocal Rank Fusion for combining multiple ranked lists"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> RerankingResult:
        """Execute RRF fusion.

        Args:
            input_data: Dict with 'query', 'result_lists', 'top_k'
                - result_lists: List of result lists, each containing items with scores
            config: Merged configuration

        Returns:
            RerankingResult with fused items
        """
        query: str = input_data.get("query", "")
        result_lists: list[list[dict[str, Any]]] = input_data.get("result_lists", [])
        top_k: int = input_data.get("top_k", 10)

        # Get RRF parameter
        k = config.get("k", 60)

        if not result_lists:
            return RerankingResult(
                ranked_items=[],
                query=query,
                reranking_method="fusion:rrf",
                total_items=0,
                metadata={"error": "No result lists provided"},
            )

        # Calculate RRF scores for all items
        rrf_scores = defaultdict(float)
        item_data = {}  # Store item details by ID
        item_appearances = defaultdict(list)  # Track which lists each item appears in

        for list_idx, result_list in enumerate(result_lists):
            for rank, item in enumerate(result_list, start=1):
                item_id = item.get("id", "")

                if not item_id:
                    continue

                # RRF formula: 1 / (k + rank)
                rrf_score = 1.0 / (k + rank)
                rrf_scores[item_id] += rrf_score

                # Track appearances
                item_appearances[item_id].append(
                    {"list_idx": list_idx, "rank": rank, "score": item.get("score", 0.0)}
                )

                # Store item data (keep first occurrence)
                if item_id not in item_data:
                    item_data[item_id] = item

        # Sort items by RRF score descending
        sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # Create ranked items
        ranked_items = []
        for rank, (item_id, rrf_score) in enumerate(sorted_items[:top_k], start=1):
            item = item_data[item_id]
            appearances = item_appearances[item_id]

            # Calculate average original rank
            avg_original_rank = sum(app["rank"] for app in appearances) / len(appearances)

            ranked_items.append(
                RankedItem(
                    id=item_id,
                    content=item.get("content", ""),
                    score=float(rrf_score),
                    rank=rank,
                    original_rank=int(avg_original_rank),
                    metadata={
                        **item.get("metadata", {}),
                        "num_lists": len(appearances),
                        "list_appearances": [
                            {"list": app["list_idx"], "rank": app["rank"], "score": app["score"]}
                            for app in appearances
                        ],
                    },
                )
            )

        return RerankingResult(
            ranked_items=ranked_items,
            query=query,
            reranking_method="fusion:rrf",
            total_items=len(rrf_scores),
            metadata={
                "top_k": top_k,
                "k": k,
                "num_input_lists": len(result_lists),
                "unique_items": len(rrf_scores),
                "fused_items": len(ranked_items),
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {
            "k": 60,  # RRF constant (higher = less aggressive ranking)
        }

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return not ("k" in config and config["k"] < 0)

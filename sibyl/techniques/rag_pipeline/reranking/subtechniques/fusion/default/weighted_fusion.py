"""Weighted score fusion implementation.

This implementation combines multiple ranked lists by normalizing their
scores and applying configurable weights to each list before aggregating
the final scores.
"""

from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.reranking.protocols import RankedItem, RerankingResult


class WeightedFusion:
    """Weighted score fusion for combining multiple result lists."""

    def __init__(self) -> None:
        self._name = "weighted_fusion"
        self._description = "Weighted score fusion for combining multiple ranked lists"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> RerankingResult:
        """Execute weighted score fusion.

        Args:
            input_data: Dict with 'query', 'result_lists', 'top_k', 'weights' (optional)
                - result_lists: List of result lists, each containing items with scores
                - weights: Optional list of weights for each result list
            config: Merged configuration

        Returns:
            RerankingResult with fused items
        """
        query: str = input_data.get("query", "")
        result_lists: list[list[dict[str, Any]]] = input_data.get("result_lists", [])
        top_k: int = input_data.get("top_k", 10)

        # Get weights (from input or config)
        weights = input_data.get("weights", config.get("weights", []))

        if not result_lists:
            return RerankingResult(
                ranked_items=[],
                query=query,
                reranking_method="fusion:weighted_fusion",
                total_items=0,
                metadata={"error": "No result lists provided"},
            )

        # Set default equal weights if not provided
        if not weights or len(weights) != len(result_lists):
            weights = [1.0 / len(result_lists)] * len(result_lists)
        else:
            # Normalize weights to sum to 1.0
            total_weight = sum(weights)
            weights = [w / total_weight for w in weights]

        # Normalize scores within each list
        normalized_lists = []
        for result_list in result_lists:
            if not result_list:
                normalized_lists.append([])
                continue

            # Find min and max scores for normalization
            scores = [item.get("score", 0.0) for item in result_list]
            min_score = min(scores) if scores else 0.0
            max_score = max(scores) if scores else 1.0
            score_range = max_score - min_score if max_score > min_score else 1.0

            # Normalize scores to [0, 1]
            normalized_list = []
            for item in result_list:
                original_score = item.get("score", 0.0)
                normalized_score = (original_score - min_score) / score_range
                normalized_list.append(
                    {**item, "normalized_score": normalized_score, "original_score": original_score}
                )

            normalized_lists.append(normalized_list)

        # Calculate weighted scores for all items
        weighted_scores = defaultdict(float)
        item_data = {}  # Store item details by ID
        item_contributions = defaultdict(list)  # Track contributions from each list

        for list_idx, (normalized_list, weight) in enumerate(
            zip(normalized_lists, weights, strict=False)
        ):
            for rank, item in enumerate(normalized_list, start=1):
                item_id = item.get("id", "")

                if not item_id:
                    continue

                normalized_score = item.get("normalized_score", 0.0)
                weighted_contribution = weight * normalized_score

                weighted_scores[item_id] += weighted_contribution

                # Track contributions
                item_contributions[item_id].append(
                    {
                        "list_idx": list_idx,
                        "rank": rank,
                        "weight": weight,
                        "normalized_score": normalized_score,
                        "original_score": item.get("original_score", 0.0),
                        "contribution": weighted_contribution,
                    }
                )

                # Store item data (keep first occurrence)
                if item_id not in item_data:
                    item_data[item_id] = item

        # Sort items by weighted score descending
        sorted_items = sorted(weighted_scores.items(), key=lambda x: x[1], reverse=True)

        # Create ranked items
        ranked_items = []
        for rank, (item_id, weighted_score) in enumerate(sorted_items[:top_k], start=1):
            item = item_data[item_id]
            contributions = item_contributions[item_id]

            # Calculate average original rank
            avg_original_rank = sum(contrib["rank"] for contrib in contributions) / len(
                contributions
            )

            ranked_items.append(
                RankedItem(
                    id=item_id,
                    content=item.get("content", ""),
                    score=float(weighted_score),
                    rank=rank,
                    original_rank=int(avg_original_rank),
                    metadata={
                        **item.get("metadata", {}),
                        "num_lists": len(contributions),
                        "list_contributions": [
                            {
                                "list": contrib["list_idx"],
                                "rank": contrib["rank"],
                                "weight": contrib["weight"],
                                "normalized_score": contrib["normalized_score"],
                                "original_score": contrib["original_score"],
                                "contribution": contrib["contribution"],
                            }
                            for contrib in contributions
                        ],
                    },
                )
            )

        return RerankingResult(
            ranked_items=ranked_items,
            query=query,
            reranking_method="fusion:weighted_fusion",
            total_items=len(weighted_scores),
            metadata={
                "top_k": top_k,
                "weights": weights,
                "num_input_lists": len(result_lists),
                "unique_items": len(weighted_scores),
                "fused_items": len(ranked_items),
                "normalization": "min-max",
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {
            "weights": [],  # Empty means equal weights
            "normalization": "min-max",  # Score normalization method
        }

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "weights" in config:
            weights = config["weights"]
            if not isinstance(weights, list):
                return False
            if any(w < 0 for w in weights):
                return False

        if "normalization" in config:
            valid_methods = ["min-max", "z-score", "none"]
            if config["normalization"] not in valid_methods:
                return False

        return True

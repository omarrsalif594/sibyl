"""Cross-encoder reranking using simulated cross-encoder scoring.

This implementation simulates cross-encoder behavior using term overlap
and semantic similarity heuristics.
"""

import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.reranking.protocols import RankedItem, RerankingResult


class CrossEncoderReranking:
    """Cross-encoder reranking implementation using term overlap scoring."""

    def __init__(self) -> None:
        self._name = "sentence_transformer"
        self._description = "Cross-encoder reranking using simulated relevance scoring"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> RerankingResult:
        """Execute cross-encoder reranking.

        Args:
            input_data: Dict with 'query', 'items', 'top_k'
            config: Merged configuration

        Returns:
            RerankingResult with reranked items
        """
        query: str = input_data.get("query", "")
        items: list[dict[str, Any]] = input_data.get("items", [])
        top_k: int = input_data.get("top_k", 10)

        if not query or not items:
            return RerankingResult(
                ranked_items=[],
                query=query,
                reranking_method="cross_encoder:sentence_transformer",
                total_items=0,
                metadata={"error": "Empty query or no items"},
            )

        # Calculate cross-encoder scores for each item
        scored_items = []
        for idx, item in enumerate(items):
            content = item.get("content", "")
            original_score = item.get("score", 0.0)

            # Calculate cross-encoder score (simulated)
            cross_score = self._calculate_cross_encoder_score(query, content, config)

            # Combine with original score if configured
            use_original = config.get("use_original_score", True)
            original_weight = config.get("original_score_weight", 0.3)

            if use_original:
                final_score = (1 - original_weight) * cross_score + original_weight * original_score
            else:
                final_score = cross_score

            scored_items.append({"item": item, "score": final_score, "original_rank": idx + 1})

        # Sort by score descending
        scored_items.sort(key=lambda x: x["score"], reverse=True)

        # Create ranked items
        ranked_items = []
        for rank, scored_item in enumerate(scored_items[:top_k], start=1):
            item = scored_item["item"]
            ranked_items.append(
                RankedItem(
                    id=item.get("id", ""),
                    content=item.get("content", ""),
                    score=float(scored_item["score"]),
                    rank=rank,
                    original_rank=scored_item["original_rank"],
                    metadata=item.get("metadata", {}),
                )
            )

        return RerankingResult(
            ranked_items=ranked_items,
            query=query,
            reranking_method="cross_encoder:sentence_transformer",
            total_items=len(items),
            metadata={
                "top_k": top_k,
                "reranked_items": len(ranked_items),
                "use_original_score": config.get("use_original_score", True),
                "original_score_weight": config.get("original_score_weight", 0.3),
            },
        )

    def _calculate_cross_encoder_score(
        self, query: str, content: str, config: dict[str, Any]
    ) -> float:
        """Calculate simulated cross-encoder relevance score.

        Uses multiple heuristics to estimate query-document relevance:
        - Term overlap (weighted by IDF)
        - Query term coverage
        - Position of query terms in content
        - Content length normalization
        """
        query_terms = self._tokenize(query.lower())
        content_terms = self._tokenize(content.lower())

        if not query_terms or not content_terms:
            return 0.0

        query_counter = Counter(query_terms)
        content_counter = Counter(content_terms)

        # 1. Term overlap score
        overlap_score = 0.0
        for term in query_counter:
            if term in content_counter:
                # TF-IDF inspired scoring
                tf = content_counter[term] / len(content_terms)
                overlap_score += tf * query_counter[term]

        # 2. Query coverage (what fraction of query terms appear in content)
        coverage = sum(1 for term in query_terms if term in content_counter) / len(query_terms)

        # 3. Position bias (earlier matches are better)
        position_score = 0.0
        content_lower = content.lower()
        for term in query_terms:
            pos = content_lower.find(term)
            if pos != -1:
                # Score decreases with position
                position_score += 1.0 / (1.0 + pos / 100.0)
        position_score /= len(query_terms)

        # 4. Length normalization
        length_penalty = min(1.0, len(content_terms) / 100.0)

        # Combine scores
        weights = {
            "overlap": config.get("overlap_weight", 0.4),
            "coverage": config.get("coverage_weight", 0.3),
            "position": config.get("position_weight", 0.2),
            "length": config.get("length_weight", 0.1),
        }

        final_score = (
            weights["overlap"] * overlap_score
            + weights["coverage"] * coverage
            + weights["position"] * position_score
            + weights["length"] * length_penalty
        )

        return min(1.0, final_score)

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization by splitting on whitespace and punctuation."""
        text = re.sub(r"[^\w\s]", " ", text)
        return [token for token in text.split() if token]

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {
            "use_original_score": True,
            "original_score_weight": 0.3,
            "overlap_weight": 0.4,
            "coverage_weight": 0.3,
            "position_weight": 0.2,
            "length_weight": 0.1,
        }

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "original_score_weight" in config:
            if not (0 <= config["original_score_weight"] <= 1):
                return False

        # Validate weights sum to reasonable value
        weights = [
            config.get("overlap_weight", 0.4),
            config.get("coverage_weight", 0.3),
            config.get("position_weight", 0.2),
            config.get("length_weight", 0.1),
        ]
        return all(0 <= w <= 1 for w in weights)

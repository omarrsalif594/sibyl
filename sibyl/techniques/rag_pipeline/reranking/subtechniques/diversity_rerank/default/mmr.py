"""Maximal Marginal Relevance (MMR) reranking for diversity.

MMR selects items that balance relevance and diversity by iteratively
choosing items that are relevant to the query but different from
already selected items.
"""

import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.reranking.protocols import RankedItem, RerankingResult


class MMRReranking:
    """MMR-based diversity reranking implementation."""

    def __init__(self) -> None:
        self._name = "mmr"
        self._description = "Maximal Marginal Relevance diversity reranking"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> RerankingResult:
        """Execute MMR diversity reranking.

        Args:
            input_data: Dict with 'query', 'items', 'top_k', 'diversity_factor'
            config: Merged configuration

        Returns:
            RerankingResult with diverse reranked items
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
                reranking_method="diversity_rerank:mmr",
                total_items=0,
                metadata={"error": "Empty query or no items"},
            )

        # Calculate relevance scores for all items
        query_terms = set(self._tokenize(query.lower()))
        item_scores = []

        for idx, item in enumerate(items):
            content = item.get("content", "")
            original_score = item.get("score", 0.0)

            # Calculate query relevance
            relevance = self._calculate_relevance(query_terms, content)

            # Use original score if available, otherwise use calculated relevance
            use_original = config.get("use_original_score", True)
            final_relevance = original_score if use_original and original_score > 0 else relevance

            item_scores.append(
                {
                    "item": item,
                    "content_terms": set(self._tokenize(content.lower())),
                    "relevance": final_relevance,
                    "original_rank": idx + 1,
                    "selected": False,
                }
            )

        # MMR algorithm: iteratively select items balancing relevance and diversity
        selected_items = []
        lambda_param = diversity_factor  # Controls relevance vs diversity trade-off

        while len(selected_items) < min(top_k, len(item_scores)):
            best_score = -float("inf")
            best_idx = -1

            for idx, item_data in enumerate(item_scores):
                if item_data["selected"]:
                    continue

                # MMR score = λ * relevance - (1-λ) * max_similarity_to_selected
                relevance_score = item_data["relevance"]

                if not selected_items:
                    # First item: just pick most relevant
                    mmr_score = relevance_score
                else:
                    # Calculate max similarity to already selected items
                    max_similarity = max(
                        self._calculate_similarity(
                            item_data["content_terms"], selected["content_terms"]
                        )
                        for selected in selected_items
                    )

                    mmr_score = lambda_param * relevance_score - (1 - lambda_param) * max_similarity

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx >= 0:
                item_scores[best_idx]["selected"] = True
                item_scores[best_idx]["mmr_score"] = best_score
                selected_items.append(item_scores[best_idx])

        # Create ranked items
        ranked_items = []
        for rank, item_data in enumerate(selected_items, start=1):
            item = item_data["item"]
            ranked_items.append(
                RankedItem(
                    id=item.get("id", ""),
                    content=item.get("content", ""),
                    score=float(item_data["mmr_score"]),
                    rank=rank,
                    original_rank=item_data["original_rank"],
                    metadata={
                        **item.get("metadata", {}),
                        "original_score": item.get("score", 0.0),
                        "relevance": item_data["relevance"],
                    },
                )
            )

        return RerankingResult(
            ranked_items=ranked_items,
            query=query,
            reranking_method="diversity_rerank:mmr",
            total_items=len(items),
            metadata={
                "top_k": top_k,
                "diversity_factor": diversity_factor,
                "reranked_items": len(ranked_items),
            },
        )

    def _calculate_relevance(self, query_terms: set[str], content: str) -> float:
        """Calculate relevance score between query and content."""
        content_terms = Counter(self._tokenize(content.lower()))

        if not query_terms or not content_terms:
            return 0.0

        # Calculate term overlap and coverage
        overlap = sum(1 for term in query_terms if term in content_terms)
        coverage = overlap / len(query_terms) if query_terms else 0.0

        # Weight by term frequency
        weighted_overlap = sum(content_terms[term] for term in query_terms if term in content_terms)
        total_terms = sum(content_terms.values())
        tf_score = weighted_overlap / total_terms if total_terms > 0 else 0.0

        # Combine coverage and TF
        return 0.6 * coverage + 0.4 * tf_score

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
        return not ("diversity_factor" in config and not 0 <= config["diversity_factor"] <= 1)

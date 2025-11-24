"""BM25-based reranking implementation.

This implementation uses the BM25 algorithm to rescore and rerank items
based on their relevance to the query using probabilistic term weighting.
"""

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.reranking.protocols import RankedItem, RerankingResult


class BM25Reranking:
    """BM25-based reranking implementation."""

    def __init__(self) -> None:
        self._name = "bm25_scorer"
        self._description = "BM25 probabilistic reranking"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> RerankingResult:
        """Execute BM25 reranking.

        Args:
            input_data: Dict with 'query', 'items', 'top_k'
            config: Merged configuration

        Returns:
            RerankingResult with BM25 reranked items
        """
        query: str = input_data.get("query", "")
        items: list[dict[str, Any]] = input_data.get("items", [])
        top_k: int = input_data.get("top_k", 10)

        # Get BM25 parameters
        k1 = config.get("k1", 1.5)
        b = config.get("b", 0.75)
        min_score = config.get("min_score", 0.0)

        if not query or not items:
            return RerankingResult(
                ranked_items=[],
                query=query,
                reranking_method="bm25_rerank:bm25_scorer",
                total_items=0,
                metadata={"error": "Empty query or no items"},
            )

        # Tokenize query
        query_terms = self._tokenize(query.lower())

        # Calculate document stats
        doc_data = []
        total_length = 0

        for idx, item in enumerate(items):
            content = item.get("content", "").lower()
            doc_terms = self._tokenize(content)
            doc_length = len(doc_terms)
            total_length += doc_length

            doc_data.append(
                {"item": item, "terms": doc_terms, "length": doc_length, "original_rank": idx + 1}
            )

        avg_doc_length = total_length / len(doc_data) if doc_data else 1

        # Calculate IDF for query terms
        idf_scores = self._calculate_idf(query_terms, doc_data)

        # Score each document using BM25
        scored_items = []
        for doc in doc_data:
            term_freqs = Counter(doc["terms"])
            doc_len = doc["length"]

            # Calculate BM25 score
            score = 0.0
            for term in query_terms:
                if term in term_freqs:
                    tf = term_freqs[term]
                    idf = idf_scores.get(term, 0.0)

                    # BM25 formula
                    numerator = tf * (k1 + 1)
                    denominator = tf + k1 * (1 - b + b * (doc_len / avg_doc_length))
                    score += idf * (numerator / denominator)

            if score >= min_score:
                scored_items.append(
                    {"item": doc["item"], "score": score, "original_rank": doc["original_rank"]}
                )

        # Sort by BM25 score descending
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
                    metadata={**item.get("metadata", {}), "original_score": item.get("score", 0.0)},
                )
            )

        return RerankingResult(
            ranked_items=ranked_items,
            query=query,
            reranking_method="bm25_rerank:bm25_scorer",
            total_items=len(items),
            metadata={
                "top_k": top_k,
                "k1": k1,
                "b": b,
                "min_score": min_score,
                "avg_doc_length": avg_doc_length,
                "query_terms": len(query_terms),
                "reranked_items": len(ranked_items),
            },
        )

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization by splitting on whitespace and punctuation."""
        text = re.sub(r"[^\w\s]", " ", text)
        return [token for token in text.split() if token]

    def _calculate_idf(
        self, query_terms: list[str], doc_data: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Calculate IDF (Inverse Document Frequency) for query terms.

        Uses the BM25 IDF formula: log((N - df(t) + 0.5) / (df(t) + 0.5) + 1)
        where N is total documents and df(t) is document frequency of term t.
        """
        n = len(doc_data)
        idf_scores = {}

        for term in set(query_terms):
            # Count documents containing term
            doc_count = sum(1 for doc in doc_data if term in doc["terms"])

            # BM25 IDF formula
            if doc_count > 0:
                idf_scores[term] = math.log((n - doc_count + 0.5) / (doc_count + 0.5) + 1)
            else:
                idf_scores[term] = 0.0

        return idf_scores

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {
            "k1": 1.5,  # Term frequency saturation parameter
            "b": 0.75,  # Length normalization parameter
            "min_score": 0.0,
        }

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "k1" in config and config["k1"] < 0:
            return False
        if "b" in config and not (0 <= config["b"] <= 1):
            return False
        return not ("min_score" in config and config["min_score"] < 0)

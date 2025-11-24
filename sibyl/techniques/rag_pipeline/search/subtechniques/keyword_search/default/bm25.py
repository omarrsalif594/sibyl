"""BM25 keyword search implementation.

BM25 (Best Matching 25) is a probabilistic ranking function used
for keyword-based document retrieval.
"""

import math
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.search.protocols import SearchResponse, SearchResult


class BM25Search:
    """BM25 keyword search implementation."""

    def __init__(self) -> None:
        self._name = "bm25"
        self._description = "BM25 probabilistic keyword search"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> SearchResponse:
        """Execute BM25 keyword search.

        Args:
            input_data: Dict with 'query', 'top_k', 'documents'
            config: Merged configuration

        Returns:
            SearchResponse with results
        """
        query: str = input_data.get("query", "")
        top_k: int = input_data.get("top_k", 10)
        documents: list[dict[str, Any]] = input_data.get("documents", [])

        # Get BM25 parameters
        k1 = config.get("k1", 1.5)
        b = config.get("b", 0.75)
        min_score = config.get("min_score", 0.0)

        if not query or not documents:
            return SearchResponse(
                results=[],
                query=query,
                total_results=0,
                search_type="keyword_search:bm25",
                metadata={"error": "Empty query or no documents"},
            )

        # Tokenize query
        query_terms = self._tokenize(query.lower())

        # Calculate document stats
        doc_lengths = [len(self._tokenize(doc.get("content", "").lower())) for doc in documents]
        avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1

        # Calculate IDF for query terms
        idf_scores = self._calculate_idf(query_terms, documents)

        # Score each document
        results = []
        for doc, doc_len in zip(documents, doc_lengths, strict=False):
            content = doc.get("content", "").lower()
            doc_terms = self._tokenize(content)
            term_freqs = Counter(doc_terms)

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
                results.append(
                    SearchResult(
                        id=doc.get("id", ""),
                        content=doc.get("content", ""),
                        score=float(score),
                        metadata=doc.get("metadata", {}),
                    )
                )

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        # Take top_k
        top_results = results[:top_k]

        # Add ranks
        for i, result in enumerate(top_results):
            result.rank = i + 1

        return SearchResponse(
            results=top_results,
            query=query,
            total_results=len(results),
            search_type="keyword_search:bm25",
            metadata={
                "k1": k1,
                "b": b,
                "min_score": min_score,
                "avg_doc_length": avg_doc_length,
                "query_terms": len(query_terms),
            },
        )

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization by splitting on whitespace and punctuation."""
        import re  # can be moved to top

        # Remove punctuation and split
        text = re.sub(r"[^\w\s]", " ", text)
        return [token for token in text.split() if token]

    def _calculate_idf(self, query_terms: list[str], documents: list[dict]) -> dict[str, float]:
        """Calculate IDF (Inverse Document Frequency) for query terms."""
        n = len(documents)
        idf_scores = {}

        for term in set(query_terms):
            # Count documents containing term
            doc_count = sum(
                1 for doc in documents if term in self._tokenize(doc.get("content", "").lower())
            )

            # IDF formula: log((N - n(t) + 0.5) / (n(t) + 0.5))
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

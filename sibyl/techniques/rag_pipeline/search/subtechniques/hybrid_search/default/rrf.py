"""Reciprocal Rank Fusion (RRF) hybrid search implementation.

RRF combines results from multiple search strategies by summing their
reciprocal ranks, providing a simple yet effective rank aggregation method.
"""

from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.rag_pipeline.search.protocols import SearchResponse, SearchResult


class RRFHybridSearch:
    """Reciprocal Rank Fusion hybrid search implementation."""

    def __init__(self) -> None:
        self._name = "rrf"
        self._description = "Reciprocal Rank Fusion for combining search results"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> SearchResponse:
        """Execute RRF hybrid search.

        Args:
            input_data: Dict with 'query', 'top_k', 'vector_results', 'keyword_results'
            config: Merged configuration

        Returns:
            SearchResponse with fused results
        """
        query: str = input_data.get("query", "")
        top_k: int = input_data.get("top_k", 10)
        vector_results: list[SearchResult] = input_data.get("vector_results", [])
        keyword_results: list[SearchResult] = input_data.get("keyword_results", [])

        # Get RRF parameter
        k = config.get("k", 60)  # RRF constant

        if not vector_results and not keyword_results:
            return SearchResponse(
                results=[],
                query=query,
                total_results=0,
                search_type="hybrid_search:rrf",
                metadata={"error": "No input results provided"},
            )

        # Calculate RRF scores
        rrf_scores: dict[str, float] = {}
        result_map: dict[str, SearchResult] = {}

        # Process vector results
        for rank, result in enumerate(vector_results, start=1):
            doc_id = result.id
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))
            result_map[doc_id] = result

        # Process keyword results
        for rank, result in enumerate(keyword_results, start=1):
            doc_id = result.id
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))
            if doc_id not in result_map:
                result_map[doc_id] = result

        # Create fused results
        fused_results = []
        for doc_id, rrf_score in rrf_scores.items():
            result = result_map[doc_id]
            # Create new result with RRF score
            fused_results.append(
                SearchResult(
                    id=result.id,
                    content=result.content,
                    score=rrf_score,
                    metadata={
                        **result.metadata,
                        "original_vector_score": next(
                            (r.score for r in vector_results if r.id == doc_id), None
                        ),
                        "original_keyword_score": next(
                            (r.score for r in keyword_results if r.id == doc_id), None
                        ),
                    },
                )
            )

        # Sort by RRF score descending
        fused_results.sort(key=lambda x: x.score, reverse=True)

        # Take top_k
        top_results = fused_results[:top_k]

        # Add ranks
        for i, result in enumerate(top_results):
            result.rank = i + 1

        return SearchResponse(
            results=top_results,
            query=query,
            total_results=len(fused_results),
            search_type="hybrid_search:rrf",
            metadata={
                "rrf_k": k,
                "vector_results_count": len(vector_results),
                "keyword_results_count": len(keyword_results),
                "unique_docs": len(rrf_scores),
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {
            "k": 60,  # RRF constant (typical value)
        }

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return not ("k" in config and config["k"] < 0)

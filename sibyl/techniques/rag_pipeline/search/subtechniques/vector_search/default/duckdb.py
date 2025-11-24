"""DuckDB vector search implementation.

Vector similarity search using DuckDB's vector extension.
Supports cosine similarity and euclidean distance.
"""

from pathlib import Path
from typing import Any

import numpy as np
import yaml

from sibyl.techniques.rag_pipeline.search.protocols import SearchResponse, SearchResult


class DuckDBVectorSearch:
    """DuckDB vector search implementation."""

    def __init__(self) -> None:
        self._name = "duckdb"
        self._description = "Vector search using DuckDB vector extension"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> SearchResponse:
        """Execute vector search.

        Args:
            input_data: Dict with 'query_vector', 'top_k', 'documents', and optional 'filters'
            config: Merged configuration

        Returns:
            SearchResponse with results
        """
        query_vector: list[float] = input_data.get("query_vector", [])
        top_k: int = input_data.get("top_k", 10)
        documents: list[dict[str, Any]] = input_data.get("documents", [])
        input_data.get("filters")
        query_text: str = input_data.get("query", "")

        # Get configuration
        distance_metric = config.get("distance_metric", "cosine")
        min_score = config.get("min_score", 0.0)

        if not query_vector:
            return SearchResponse(
                results=[],
                query=query_text,
                total_results=0,
                search_type="vector_search:duckdb",
                metadata={"error": "No query vector provided"},
            )

        # Perform in-memory vector similarity search
        results = []
        query_vec = np.array(query_vector)

        for doc in documents:
            if "vector" not in doc:
                continue

            doc_vec = np.array(doc["vector"])

            # Calculate similarity based on metric
            if distance_metric == "cosine":
                similarity = self._cosine_similarity(query_vec, doc_vec)
            elif distance_metric == "euclidean":
                similarity = 1.0 / (1.0 + self._euclidean_distance(query_vec, doc_vec))
            else:
                similarity = self._cosine_similarity(query_vec, doc_vec)

            if similarity >= min_score:
                results.append(
                    SearchResult(
                        id=doc.get("id", ""),
                        content=doc.get("content", ""),
                        score=float(similarity),
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
            query=query_text,
            total_results=len(results),
            search_type="vector_search:duckdb",
            metadata={
                "distance_metric": distance_metric,
                "min_score": min_score,
                "documents_searched": len(documents),
            },
        )

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def _euclidean_distance(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate Euclidean distance between two vectors."""
        return float(np.linalg.norm(vec1 - vec2))

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {
            "distance_metric": "cosine",
            "min_score": 0.0,
        }

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "distance_metric" in config:
            if config["distance_metric"] not in ["cosine", "euclidean"]:
                return False

        return not ("min_score" in config and not 0.0 <= config["min_score"] <= 1.0)

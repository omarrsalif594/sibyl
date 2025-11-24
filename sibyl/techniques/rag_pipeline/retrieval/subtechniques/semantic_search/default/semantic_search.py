"""
Semantic Search Retrieval Subtechnique

This module provides semantic similarity-based retrieval.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class SemanticSearch:
    """
    Semantic search retrieval implementation.

    This subtechnique retrieves items based on semantic similarity
    to a query.
    """

    def __init__(self) -> None:
        """Initialize semantic search."""
        self._name = "semantic_search"
        self._description = "Semantic similarity-based retrieval"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        """Get subtechnique name."""
        return self._name

    @property
    def description(self) -> str:
        """Get subtechnique description."""
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Execute semantic search.

        EXPERIMENTAL: Not production ready. This implementation requires proper
        vector embeddings and similarity computation infrastructure.

        Args:
            input_data: Query and corpus (dict with 'query' and 'corpus' keys)
            config: Merged configuration

        Returns:
            List of search results with scores

        Raises:
            NotImplementedError: This feature is experimental
            ValueError: If input_data is invalid
        """
        # Validate input
        if not isinstance(input_data, dict):
            msg = "input_data must be a dictionary with 'query' and 'corpus'"
            raise TypeError(msg)

        query = input_data.get("query")
        corpus = input_data.get("corpus", [])
        query_embedding = input_data.get("query_embedding")
        corpus_embeddings = input_data.get("corpus_embeddings")

        if not query and query_embedding is None:
            msg = "Must provide either 'query' or 'query_embedding'"
            raise ValueError(msg)

        if not corpus and not corpus_embeddings:
            return []

        # Check if we have actual embeddings to work with
        if query_embedding is not None and corpus_embeddings is not None:
            # Get configuration
            top_k = config.get("top_k", 10)
            similarity_threshold = config.get("similarity_threshold", 0.3)
            similarity_metric = config.get("similarity_metric", "cosine")
            include_scores = config.get("include_scores", True)

            logger.debug(
                f"Semantic search: top_k={top_k}, threshold={similarity_threshold}, "
                f"metric={similarity_metric}"
            )

            # Compute real semantic similarity using provided embeddings
            results = self._compute_similarity(
                query_embedding,
                corpus_embeddings,
                corpus,
                top_k,
                similarity_threshold,
                similarity_metric,
                include_scores,
            )

            logger.info("Retrieved %s results", len(results))
            return results

        # If no embeddings provided, fail explicitly
        msg = (
            "Semantic search requires pre-computed embeddings. "
            "Please provide 'query_embedding' and 'corpus_embeddings' in input_data. "
            "This feature is experimental and not production ready without proper "
            "embedding infrastructure."
        )
        raise NotImplementedError(msg)

    def _compute_similarity(
        self,
        query_embedding: np.ndarray,
        corpus_embeddings: np.ndarray,
        corpus: list[Any],
        top_k: int,
        threshold: float,
        similarity_metric: str,
        include_scores: bool,
    ) -> list[dict[str, Any]]:
        """
        Compute semantic similarity using embeddings.

        Args:
            query_embedding: Query vector embedding
            corpus_embeddings: Corpus vector embeddings matrix
            corpus: List of items to search
            top_k: Number of results to return
            threshold: Similarity threshold
            similarity_metric: Metric to use (cosine, dot_product, euclidean)
            include_scores: Whether to include scores

        Returns:
            List of search results sorted by similarity
        """
        # Convert to numpy arrays if needed
        query_vec = np.asarray(query_embedding)
        corpus_vecs = np.asarray(corpus_embeddings)

        # Compute similarities based on metric
        if similarity_metric == "cosine":
            # Normalize vectors for cosine similarity
            query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
            corpus_norms = corpus_vecs / (
                np.linalg.norm(corpus_vecs, axis=1, keepdims=True) + 1e-10
            )
            similarities = np.dot(corpus_norms, query_norm)
        elif similarity_metric == "dot_product":
            similarities = np.dot(corpus_vecs, query_vec)
        elif similarity_metric == "euclidean":
            # For euclidean, smaller distance = higher similarity
            distances = np.linalg.norm(corpus_vecs - query_vec, axis=1)
            similarities = 1.0 / (1.0 + distances)
        else:
            msg = f"Unsupported similarity metric: {similarity_metric}"
            raise ValueError(msg)

        # Get top-k results above threshold
        # Sort by similarity (descending)
        sorted_indices = np.argsort(similarities)[::-1]

        results = []
        for rank, idx in enumerate(sorted_indices[:top_k]):
            score = float(similarities[idx])

            if score < threshold:
                break

            item = corpus[idx]

            # Extract content
            if isinstance(item, str):
                content = item
                metadata = {}
            elif isinstance(item, dict):
                content = item.get("content", str(item))
                metadata = {k: v for k, v in item.items() if k != "content"}
            else:
                content = str(item)
                metadata = {}

            result = {
                "content": content,
                "metadata": metadata,
                "rank": rank + 1,
            }

            if include_scores:
                result["score"] = score

            results.append(result)

        return results

    def get_config(self) -> dict[str, Any]:
        """
        Get default configuration for this subtechnique.

        Returns:
            Default configuration
        """
        import yaml

        if self._config_path.exists():
            with open(self._config_path) as f:
                config = yaml.safe_load(f)
                return config if config is not None else {}
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate top_k
        top_k = config.get("top_k")
        if top_k is not None and (not isinstance(top_k, int) or top_k <= 0):
            msg = f"top_k must be a positive integer, got {top_k}"
            raise ValueError(msg)

        # Validate similarity_threshold
        threshold = config.get("similarity_threshold")
        if threshold is not None and not 0 <= threshold <= 1:
            msg = f"similarity_threshold must be between 0 and 1, got {threshold}"
            raise ValueError(msg)

        # Validate similarity_metric
        metric = config.get("similarity_metric")
        if metric is not None:
            valid_metrics = ["cosine", "dot_product", "euclidean"]
            if metric not in valid_metrics:
                msg = f"similarity_metric must be one of {valid_metrics}, got {metric}"
                raise ValueError(msg)

        return True

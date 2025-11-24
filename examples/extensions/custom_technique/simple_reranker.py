"""
Simple custom reranking technique example.

This demonstrates how to create a custom technique that can be registered
and used in Sibyl workspaces. This reranker filters and sorts search results
by relevance score.
"""

from typing import Any

from sibyl.techniques.protocols import BaseSubtechnique, BaseTechnique


class ScoreBasedReranker(BaseSubtechnique):
    """
    Rerank search results by relevance score.

    This subtechnique filters results by minimum score threshold
    and sorts them in descending order by score.
    """

    @property
    def name(self) -> str:
        return "score_based"

    @property
    def description(self) -> str:
        return "Rerank search results using relevance scores"

    def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """
        Rerank search results.

        Args:
            input_data: List of search results, each with 'score' field
                       Example: [{"text": "...", "score": 0.85}, ...]
            config: Configuration dict with:
                   - min_score (float): Minimum score threshold (default: 0.7)
                   - max_results (int): Maximum results to return (default: 10)

        Returns:
            List of filtered and reranked results
        """
        results = input_data if isinstance(input_data, list) else []
        min_score = config.get("min_score", 0.7)
        max_results = config.get("max_results", 10)

        # Filter by minimum score
        filtered = [r for r in results if r.get("score", 0) >= min_score]

        # Sort by score descending
        reranked = sorted(filtered, key=lambda x: x.get("score", 0), reverse=True)

        # Limit results
        return reranked[:max_results]

    def get_config(self) -> dict[str, Any]:
        """Get default configuration"""
        return {"min_score": 0.7, "max_results": 10}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        min_score = config.get("min_score")
        if min_score is not None and not (0.0 <= min_score <= 1.0):
            msg = "min_score must be between 0.0 and 1.0"
            raise ValueError(msg)

        max_results = config.get("max_results")
        if max_results is not None and max_results < 1:
            msg = "max_results must be at least 1"
            raise ValueError(msg)

        return True


class DiversityReranker(BaseSubtechnique):
    """
    Rerank results to maximize diversity.

    This subtechnique ensures that top results are diverse by
    penalizing similar consecutive results.
    """

    @property
    def name(self) -> str:
        return "diversity"

    @property
    def description(self) -> str:
        return "Rerank to maximize diversity in results"

    def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """
        Rerank with diversity penalty.

        Args:
            input_data: List of search results with 'score' and 'text' fields
            config: Configuration dict with:
                   - diversity_weight (float): Weight for diversity penalty (default: 0.3)
                   - max_results (int): Maximum results to return (default: 10)

        Returns:
            List of reranked results with diversity
        """
        results = input_data if isinstance(input_data, list) else []
        diversity_weight = config.get("diversity_weight", 0.3)
        max_results = config.get("max_results", 10)

        if not results:
            return []

        # Start with highest scored result
        reranked = [max(results, key=lambda x: x.get("score", 0))]
        remaining = [r for r in results if r != reranked[0]]

        # Iteratively add most diverse result
        while remaining and len(reranked) < max_results:
            best_score = -1
            best_result = None

            for candidate in remaining:
                # Calculate diversity penalty based on similarity to already selected
                penalty = 0
                for selected in reranked:
                    # Simple similarity based on shared words
                    candidate_words = set(candidate.get("text", "").lower().split())
                    selected_words = set(selected.get("text", "").lower().split())
                    if candidate_words and selected_words:
                        overlap = len(candidate_words & selected_words)
                        similarity = overlap / max(len(candidate_words), len(selected_words))
                        penalty += similarity

                # Normalize penalty
                avg_penalty = penalty / len(reranked)

                # Calculate final score with diversity
                base_score = candidate.get("score", 0)
                final_score = base_score * (1 - diversity_weight * avg_penalty)

                if final_score > best_score:
                    best_score = final_score
                    best_result = candidate

            if best_result:
                reranked.append(best_result)
                remaining.remove(best_result)
            else:
                break

        return reranked

    def get_config(self) -> dict[str, Any]:
        """Get default configuration"""
        return {"diversity_weight": 0.3, "max_results": 10}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration"""
        diversity_weight = config.get("diversity_weight")
        if diversity_weight is not None and not (0.0 <= diversity_weight <= 1.0):
            msg = "diversity_weight must be between 0.0 and 1.0"
            raise ValueError(msg)

        max_results = config.get("max_results")
        if max_results is not None and max_results < 1:
            msg = "max_results must be at least 1"
            raise ValueError(msg)

        return True


class SimpleRerankingTechnique(BaseTechnique):
    """
    Simple reranking technique with multiple strategies.

    This technique provides two reranking strategies:
    - score_based: Filter and sort by score
    - diversity: Maximize diversity in top results

    Example usage:
        >>> from sibyl.techniques.registry import register_technique, get_technique
        >>> register_technique("simple_reranking",
        ...     "examples.extensions.custom_technique.simple_reranker.SimpleRerankingTechnique")
        >>> reranker = get_technique("simple_reranking")
        >>> results = [
        ...     {"text": "Python is great", "score": 0.9},
        ...     {"text": "Python is awesome", "score": 0.85},
        ...     {"text": "Java is verbose", "score": 0.6},
        ... ]
        >>> reranked = reranker.execute(results, "score_based", {"min_score": 0.8})
        >>> print(len(reranked))  # 2
    """

    def __init__(self) -> None:
        self._subtechniques = {
            "score_based": ScoreBasedReranker(),
            "diversity": DiversityReranker(),
        }

    @property
    def name(self) -> str:
        return "simple_reranking"

    @property
    def description(self) -> str:
        return "Simple reranking technique with score-based and diversity strategies"

    @property
    def subtechniques(self) -> dict[str, BaseSubtechnique]:
        return self._subtechniques

    def execute(
        self, input_data: Any, subtechnique: str, config: dict[str, Any], **kwargs: Any
    ) -> Any:
        """
        Execute reranking with specified subtechnique.

        Args:
            input_data: List of search results to rerank
            subtechnique: Name of subtechnique to use ("score_based" or "diversity")
            config: Configuration overrides
            **kwargs: Additional keyword arguments

        Returns:
            Reranked results

        Raises:
            ValueError: If subtechnique is unknown
        """
        if subtechnique not in self._subtechniques:
            msg = (
                f"Unknown subtechnique: '{subtechnique}'. "
                f"Available: {list(self._subtechniques.keys())}"
            )
            raise ValueError(msg)

        # Get subtechnique instance
        impl = self._subtechniques[subtechnique]

        # Merge default config with overrides
        merged_config = {**impl.get_config(), **config}

        # Validate configuration
        impl.validate_config(merged_config)

        # Execute
        return impl.execute(input_data, merged_config)

    def get_config(self) -> dict[str, Any]:
        """Get default configuration"""
        return {
            "default_subtechnique": "score_based",
            "min_score": 0.7,
            "max_results": 10,
        }

    def load_config(self, config_path: Any) -> dict[str, Any]:
        """Load configuration from file"""
        from pathlib import Path  # noqa: PLC0415 - plugin registration

        import yaml  # noqa: PLC0415 - plugin registration

        path = Path(config_path)
        if not path.exists():
            msg = f"Config file not found: {config_path}"
            raise FileNotFoundError(msg)

        with open(path) as f:
            return yaml.safe_load(f)

    def register_subtechnique(self, subtechnique: BaseSubtechnique) -> None:
        """Register a new subtechnique"""
        if subtechnique.name in self._subtechniques:
            msg = (
                f"Subtechnique '{subtechnique.name}' already registered. "
                "Use a different name or override the existing one."
            )
            raise ValueError(msg)
        self._subtechniques[subtechnique.name] = subtechnique

    def list_subtechniques(self) -> list[str]:
        """List all available subtechnique names"""
        return list(self._subtechniques.keys())


# Register the technique (can be done at import time or explicitly)
def register() -> None:
    """Register this technique with Sibyl"""
    from sibyl.techniques.registry import register_technique  # noqa: PLC0415 - plugin registration

    register_technique(
        "simple_reranking",
        "examples.extensions.custom_technique.simple_reranker.SimpleRerankingTechnique",
    )


# Auto-register on import (optional)
# Uncomment to auto-register:
# register()

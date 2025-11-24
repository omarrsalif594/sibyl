"""
Scoring Technique

Provides scoring algorithms for agents:
- Confidence calculation for plan quality
- Quality scoring for review results
- Relevance scoring for search results

Extracted from hardcoded logic in:
- agents/planner.py:263-266 (confidence calculation)
- agents/reviewer.py:193,199-203 (quality scoring)
- agents/search.py:249-252 (relevance scoring)
"""

from typing import Any

from sibyl.techniques.protocols import BaseTechnique, SubtechniqueResult


class ScoringTechnique(BaseTechnique):
    """Scoring algorithms for agents."""

    def execute(
        self, subtechnique: str, implementation: str, context: dict[str, Any], **kwargs
    ) -> SubtechniqueResult:
        """
        Execute a scoring subtechnique.

        Args:
            subtechnique: One of ['confidence_calculation', 'quality_scoring', 'relevance_scoring']
            implementation: Implementation name (e.g., 'weighted_sum', 'penalty_based', 'threshold_based')
            context: Input data for scoring algorithm
            **kwargs: Additional arguments

        Returns:
            SubtechniqueResult with score and metadata

        Examples:
            >>> # Calculate confidence for a plan
            >>> result = technique.execute(
            ...     'confidence_calculation',
            ...     'weighted_sum',
            ...     {'tools': ['tool1', 'tool2', 'tool3']}
            ... )
            >>> print(result.result['score'])  # 0.8

            >>> # Calculate quality score
            >>> result = technique.execute(
            ...     'quality_scoring',
            ...     'penalty_based',
            ...     {'failures': 2, 'issues': [{'severity': 'high'}, {'severity': 'medium'}]}
            ... )
            >>> print(result.result['score'])  # -55

            >>> # Calculate relevance score
            >>> result = technique.execute(
            ...     'relevance_scoring',
            ...     'threshold_based',
            ...     {'similarity': 0.85}
            ... )
            >>> print(result.result['score'])  # 0.8 (high relevance)
        """
        impl = self.get_subtechnique(subtechnique, implementation)
        return impl.execute(context, **kwargs)

    def calculate_confidence(
        self, tools: list[str], implementation: str | None = None, **kwargs
    ) -> float:
        """
        Convenience method to calculate confidence score.

        Args:
            tools: List of tools in the plan
            implementation: Optional implementation name (defaults to config default)
            **kwargs: Additional arguments

        Returns:
            Confidence score (0.0 to 1.0)
        """
        impl = implementation or self.config.get("default_implementation", "weighted_sum")
        result = self.execute("confidence_calculation", impl, {"tools": tools}, **kwargs)
        return result.result.get("score", 0.5)

    def calculate_quality(
        self,
        failures: int = 0,
        issues: list[dict[str, Any]] | None = None,
        implementation: str | None = None,
        **kwargs,
    ) -> float:
        """
        Convenience method to calculate quality score.

        Args:
            failures: Number of failures
            issues: List of issues with severity levels
            implementation: Optional implementation name
            **kwargs: Additional arguments

        Returns:
            Quality score (negative values indicate problems)
        """
        impl = implementation or "penalty_based"
        result = self.execute(
            "quality_scoring", impl, {"failures": failures, "issues": issues or []}, **kwargs
        )
        return result.result.get("score", 0.0)

    def calculate_relevance(
        self, similarity: float, implementation: str | None = None, **kwargs
    ) -> float:
        """
        Convenience method to calculate relevance score.

        Args:
            similarity: Similarity score (0.0 to 1.0)
            implementation: Optional implementation name
            **kwargs: Additional arguments

        Returns:
            Relevance score (0.0 to 1.0)
        """
        impl = implementation or "threshold_based"
        result = self.execute("relevance_scoring", impl, {"similarity": similarity}, **kwargs)
        return result.result.get("score", 0.5)

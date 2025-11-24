"""
Threshold-Based Relevance Scoring

Original logic from agents/search.py:249-252:
    if similarity >= 0.8: return 0.8
    elif similarity >= 0.5: return 0.5
    else: return 0.2

This calculates relevance score by categorizing similarity into discrete levels.
"""

from typing import Any

from sibyl.techniques.protocols import SubtechniqueImplementation, SubtechniqueResult


class ThresholdBasedRelevanceScoring(SubtechniqueImplementation):
    """Calculate relevance score using threshold-based approach."""

    def execute(self, context: dict[str, Any], **kwargs) -> SubtechniqueResult:
        """
        Calculate relevance score based on similarity threshold.

        Args:
            context: Must contain 'similarity' key with float value (0.0 to 1.0)
            **kwargs: Additional arguments (ignored)

        Returns:
            SubtechniqueResult with score and metadata

        Example:
            >>> impl = ThresholdBasedRelevanceScoring(config)
            >>> result = impl.execute({'similarity': 0.85})
            >>> result.result['score']  # 0.8 (high relevance)
            >>> result.result['category']  # 'high'
        """
        similarity = context.get("similarity", 0.0)

        # Get thresholds and scores from config
        high_threshold = self.config.get("high_threshold", 0.8)
        medium_threshold = self.config.get("medium_threshold", 0.5)
        high_score = self.config.get("high_score", 0.8)
        medium_score = self.config.get("medium_score", 0.5)
        low_score = self.config.get("low_score", 0.2)

        # Determine score based on thresholds
        if similarity >= high_threshold:
            score = high_score
            category = "high"
        elif similarity >= medium_threshold:
            score = medium_score
            category = "medium"
        else:
            score = low_score
            category = "low"

        return SubtechniqueResult(
            success=True,
            result={
                "score": score,
                "category": category,
                "similarity": similarity,
                "method": "threshold_based",
            },
            metadata={
                "thresholds": {"high": high_threshold, "medium": medium_threshold},
                "scores": {"high": high_score, "medium": medium_score, "low": low_score},
            },
        )

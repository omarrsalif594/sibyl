"""Quality scoring implementations.

This module provides implementations for calculating quality scores
based on failures and issues (e.g., from code review results).
"""

import logging
from typing import Any

from sibyl.techniques.infrastructure.scoring.protocols import (
    QualityInput,
    ScoringResult,
)

logger = logging.getLogger(__name__)


class PenaltyBasedScorer:
    """Calculate quality score using penalty-based approach.

    This implementation is based on the original logic from agents/reviewer.py:193,199-203:
    - Start at 0 (neutral quality)
    - Penalty per failure: -10
    - Penalty per issue: based on severity
      - high: -30
      - medium: -15
      - low: -5
    - Negative score indicates quality problems

    Examples:
        >>> scorer = PenaltyBasedScorer()
        >>> input_data = QualityInput(failures=1, issues=[{'severity': 'high'}])
        >>> result = scorer.score(input_data, {})
        >>> assert result.score == -40  # -10 (failure) + -30 (high severity)
    """

    @property
    def name(self) -> str:
        """Scorer name for identification."""
        return "penalty_based"

    def __init__(
        self,
        failure_penalty: float = -10.0,
        severity_penalties: dict[str, float] | None = None,
    ) -> None:
        """Initialize penalty-based scorer.

        Args:
            failure_penalty: Penalty per failure (default: -10)
            severity_penalties: Penalty per issue severity (default: high=-30, medium=-15, low=-5)
        """
        self.failure_penalty = failure_penalty
        self.severity_penalties = severity_penalties or {
            "high": -30.0,
            "medium": -15.0,
            "low": -5.0,
        }

        logger.debug(
            f"Initialized {self.name} scorer: "
            f"failure_penalty={failure_penalty}, "
            f"severity_penalties={self.severity_penalties}"
        )

    def score(self, input_data: QualityInput, context: dict[str, Any]) -> ScoringResult:
        """Calculate quality score using penalty-based approach.

        Args:
            input_data: Quality input data with failures and issues
            context: Scoring context (unused in this implementation)

        Returns:
            ScoringResult with quality score (negative indicates problems)

        Examples:
            >>> scorer = PenaltyBasedScorer()
            >>> input_data = QualityInput(failures=2, issues=[
            ...     {'severity': 'high'},
            ...     {'severity': 'medium'}
            ... ])
            >>> result = scorer.score(input_data, {})
            >>> assert result.score == -65  # -20 (failures) + -30 (high) + -15 (medium)
        """
        # Start at 0 (neutral quality)
        score = 0.0

        # Apply failure penalties
        failure_penalty_total = input_data.failures * self.failure_penalty
        score += failure_penalty_total

        # Apply issue severity penalties
        issue_penalties = {}
        for issue in input_data.issues:
            severity = issue.get("severity", "low")
            penalty = self.severity_penalties.get(severity, self.severity_penalties["low"])
            issue_penalties[severity] = issue_penalties.get(severity, 0.0) + penalty
            score += penalty

        # Calculate score breakdown
        breakdown = {
            "base_score": 0.0,
            "failure_penalty": failure_penalty_total,
            "issue_penalties": issue_penalties,
            "total_penalty": score,
        }

        logger.debug(
            f"Quality calculated: score={score:.2f}, "
            f"failures={input_data.failures}, issues={len(input_data.issues)}"
        )

        return ScoringResult(
            score=score,
            confidence=1.0,  # We're confident in our calculation
            metadata={
                "scorer": self.name,
                "num_failures": input_data.failures,
                "num_issues": len(input_data.issues),
                "issue_severities": [i.get("severity", "low") for i in input_data.issues],
            },
            breakdown=breakdown,
        )


def create_default_quality_scorer() -> PenaltyBasedScorer:
    """Factory function to create default quality scorer.

    Returns:
        Configured PenaltyBasedScorer instance
    """
    return PenaltyBasedScorer()

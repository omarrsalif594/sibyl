"""
Penalty-Based Quality Scoring

Original logic from agents/reviewer.py:193,199-203:
    score = -20 * num_failures
    for issue in issues:
        if issue.severity == 'critical': score -= 15
        elif issue.severity == 'high': score -= 10
        elif issue.severity == 'medium': score -= 5

This calculates quality score by applying penalties for failures and issues.
Negative scores indicate quality problems.
"""

from typing import Any

from sibyl.techniques.protocols import SubtechniqueImplementation, SubtechniqueResult


class PenaltyBasedQualityScoring(SubtechniqueImplementation):
    """Calculate quality score using penalty-based approach."""

    def execute(self, context: dict[str, Any], **kwargs) -> SubtechniqueResult:
        """
        Calculate quality score based on failures and issues.

        Args:
            context: Must contain:
                - 'failures': int, number of failures
                - 'issues': List[Dict], list of issues with 'severity' field
            **kwargs: Additional arguments (ignored)

        Returns:
            SubtechniqueResult with score and metadata

        Example:
            >>> impl = PenaltyBasedQualityScoring(config)
            >>> result = impl.execute({
            ...     'failures': 2,
            ...     'issues': [
            ...         {'severity': 'high'},
            ...         {'severity': 'medium'}
            ...     ]
            ... })
            >>> result.result['score']  # -55 (2*-20 + -10 + -5)
        """
        failures = context.get("failures", 0)
        issues = context.get("issues", [])

        # Get penalties from config
        failure_penalty = self.config.get("failure_penalty", -20)
        critical_penalty = self.config.get("critical_penalty", -15)
        high_penalty = self.config.get("high_penalty", -10)
        medium_penalty = self.config.get("medium_penalty", -5)
        low_penalty = self.config.get("low_penalty", 0)

        # Calculate score
        score = failure_penalty * failures

        # Track issue breakdown
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for issue in issues:
            severity = issue.get("severity", "low").lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            if severity == "critical":
                score += critical_penalty
            elif severity == "high":
                score += high_penalty
            elif severity == "medium":
                score += medium_penalty
            elif severity == "low":
                score += low_penalty

        return SubtechniqueResult(
            success=True,
            result={
                "score": score,
                "num_failures": failures,
                "num_issues": len(issues),
                "method": "penalty_based",
            },
            metadata={
                "severity_counts": severity_counts,
                "penalties": {
                    "failure": failure_penalty,
                    "critical": critical_penalty,
                    "high": high_penalty,
                    "medium": medium_penalty,
                    "low": low_penalty,
                },
            },
        )

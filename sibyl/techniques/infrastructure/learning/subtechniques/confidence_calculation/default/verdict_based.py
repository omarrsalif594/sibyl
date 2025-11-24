"""
Verdict-Based Confidence Calculation

Original logic from sibyl/core/learning/hook.py:265-283:
    confidence = verdict.metadata.get("classification_confidence", 0.0)
    if verdict.status == VerdictStatus.GREEN:
        confidence = max(confidence, 0.8)  # High confidence for success
    elif verdict.status == VerdictStatus.RED:
        confidence = min(confidence, 0.5)  # Lower confidence for failure

This calculates confidence based on validation verdict status,
adjusting confidence thresholds based on success/failure outcomes.
"""

from typing import Any

from sibyl.techniques.protocols import SubtechniqueImplementation, SubtechniqueResult


class VerdictBasedConfidenceCalculation(SubtechniqueImplementation):
    """Calculate confidence based on validation verdict status."""

    def execute(self, context: dict[str, Any], **kwargs) -> SubtechniqueResult:
        """
        Calculate confidence score based on verdict status.

        Args:
            context: Must contain:
                - 'verdict_status': Status (GREEN, YELLOW, RED)
                - 'base_confidence': Base confidence from classification (0.0-1.0)
            **kwargs: Additional arguments (ignored)

        Returns:
            SubtechniqueResult with confidence score and metadata

        Example:
            >>> impl = VerdictBasedConfidenceCalculation(config)
            >>> result = impl.execute({
            ...     'verdict_status': 'GREEN',
            ...     'base_confidence': 0.7
            ... })
            >>> result.result['confidence']  # 0.8 (adjusted minimum for GREEN)
        """
        verdict_status = context.get("verdict_status", "UNKNOWN")
        base_confidence = context.get("base_confidence", 0.0)

        # Get thresholds from config
        green_min_confidence = self.config.get("green_min_confidence", 0.8)
        red_max_confidence = self.config.get("red_max_confidence", 0.5)
        yellow_confidence = self.config.get("yellow_confidence", base_confidence)

        # Apply status-based adjustments
        if verdict_status == "GREEN":
            confidence = max(base_confidence, green_min_confidence)
            adjustment = "increased to minimum for success"
        elif verdict_status == "RED":
            confidence = min(base_confidence, red_max_confidence)
            adjustment = "decreased to maximum for failure"
        elif verdict_status == "YELLOW":
            confidence = (
                yellow_confidence if yellow_confidence != base_confidence else base_confidence
            )
            adjustment = "kept at base for partial success"
        else:
            confidence = base_confidence
            adjustment = "no adjustment for unknown status"

        return SubtechniqueResult(
            success=True,
            result={
                "confidence": confidence,
                "verdict_status": verdict_status,
                "base_confidence": base_confidence,
                "adjustment": adjustment,
            },
            metadata={
                "green_min_confidence": green_min_confidence,
                "red_max_confidence": red_max_confidence,
                "yellow_confidence": yellow_confidence,
                "adjusted": confidence != base_confidence,
            },
        )

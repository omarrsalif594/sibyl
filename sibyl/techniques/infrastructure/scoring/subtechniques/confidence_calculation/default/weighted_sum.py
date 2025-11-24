"""
Weighted Sum Confidence Calculation

Original logic from agents/planner.py:263-266:
    confidence = min(0.5 + (0.1 * len(tools)), 0.9)

This calculates confidence based on the number of tools in a plan,
with more tools generally indicating higher confidence (up to a maximum).
"""

from typing import Any

from sibyl.techniques.protocols import SubtechniqueImplementation, SubtechniqueResult


class WeightedSumConfidenceCalculation(SubtechniqueImplementation):
    """Calculate confidence using weighted sum of factors."""

    def execute(self, context: dict[str, Any], **kwargs) -> SubtechniqueResult:
        """
        Calculate confidence score based on number of tools.

        Args:
            context: Must contain 'tools' key with list of tools
            **kwargs: Additional arguments (ignored)

        Returns:
            SubtechniqueResult with score and metadata

        Example:
            >>> impl = WeightedSumConfidenceCalculation(config)
            >>> result = impl.execute({'tools': ['tool1', 'tool2', 'tool3']})
            >>> result.result['score']  # 0.8
        """
        tools = context.get("tools", [])
        num_tools = len(tools) if tools else 0

        # Get parameters from config
        base_confidence = self.config.get("base_confidence", 0.5)
        tool_weight = self.config.get("tool_weight", 0.1)
        max_confidence = self.config.get("max_confidence", 0.9)

        # Calculate: base + (weight * num_tools), capped at max
        confidence = min(base_confidence + (tool_weight * num_tools), max_confidence)

        return SubtechniqueResult(
            success=True,
            result={"score": confidence, "num_tools": num_tools, "method": "weighted_sum"},
            metadata={
                "base_confidence": base_confidence,
                "tool_weight": tool_weight,
                "max_confidence": max_confidence,
                "capped": confidence >= max_confidence,
            },
        )

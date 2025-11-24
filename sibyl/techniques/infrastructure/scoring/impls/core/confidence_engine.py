"""Confidence calculation implementations.

This module provides implementations for calculating confidence scores
based on plan characteristics (e.g., number of tools, complexity).
"""

import logging
from typing import Any

from sibyl.techniques.infrastructure.scoring.protocols import (
    ConfidenceInput,
    ScoringResult,
)

logger = logging.getLogger(__name__)


class WeightedSumCalculator:
    """Calculate confidence score using weighted sum of plan characteristics.

    This implementation is based on the original logic from agents/planner.py:263-266:
    - Base confidence: 0.5
    - Tools bonus: +0.05 per tool (capped at 3 tools = +0.15)
    - Max confidence: 0.8

    Examples:
        >>> calculator = WeightedSumCalculator()
        >>> input_data = ConfidenceInput(tools=['tool1', 'tool2'])
        >>> result = calculator.calculate(input_data, {})
        >>> assert result.score == 0.6  # 0.5 + 2*0.05
        >>> assert 0.0 <= result.score <= 1.0
    """

    @property
    def name(self) -> str:
        """Calculator name for identification."""
        return "weighted_sum"

    def __init__(
        self,
        base_confidence: float = 0.5,
        tool_bonus: float = 0.05,
        max_tools_bonus: int = 3,
        max_confidence: float = 0.8,
    ) -> None:
        """Initialize weighted sum calculator.

        Args:
            base_confidence: Base confidence score (default: 0.5)
            tool_bonus: Bonus per tool (default: 0.05)
            max_tools_bonus: Maximum tools to count for bonus (default: 3)
            max_confidence: Maximum confidence score (default: 0.8)
        """
        self.base_confidence = base_confidence
        self.tool_bonus = tool_bonus
        self.max_tools_bonus = max_tools_bonus
        self.max_confidence = max_confidence

        logger.debug(
            f"Initialized {self.name} calculator: "
            f"base={base_confidence}, tool_bonus={tool_bonus}, "
            f"max_tools={max_tools_bonus}, max={max_confidence}"
        )

    def calculate(self, input_data: ConfidenceInput, context: dict[str, Any]) -> ScoringResult:
        """Calculate confidence score using weighted sum.

        Args:
            input_data: Confidence input data with tools list
            context: Calculation context (unused in this implementation)

        Returns:
            ScoringResult with confidence score (0.0 to 1.0)

        Examples:
            >>> calculator = WeightedSumCalculator()
            >>> input_data = ConfidenceInput(tools=['a', 'b', 'c'])
            >>> result = calculator.calculate(input_data, {})
            >>> assert result.score == 0.65  # 0.5 + 3*0.05
        """
        num_tools = len(input_data.tools)

        # Calculate tools bonus (capped at max_tools_bonus)
        tools_counted = min(num_tools, self.max_tools_bonus)
        bonus = tools_counted * self.tool_bonus

        # Calculate final score (capped at max_confidence)
        score = min(self.base_confidence + bonus, self.max_confidence)

        # Calculate score breakdown
        breakdown = {
            "base_confidence": self.base_confidence,
            "tools_bonus": bonus,
            "num_tools": num_tools,
            "tools_counted": tools_counted,
        }

        logger.debug(
            f"Confidence calculated: score={score:.2f}, tools={num_tools}, bonus={bonus:.2f}"
        )

        return ScoringResult(
            score=score,
            confidence=1.0,  # We're confident in our calculation
            metadata={
                "calculator": self.name,
                "num_tools": num_tools,
                "tools_counted": tools_counted,
            },
            breakdown=breakdown,
        )


def create_default_confidence_calculator() -> WeightedSumCalculator:
    """Factory function to create default confidence calculator.

    Returns:
        Configured WeightedSumCalculator instance
    """
    return WeightedSumCalculator()

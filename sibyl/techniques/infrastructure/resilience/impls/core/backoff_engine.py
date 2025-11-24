"""Backoff strategy implementations."""

import logging
import random
from typing import Any

from sibyl.techniques.infrastructure.resilience.protocols import (
    BackoffInput,
    BackoffResult,
)

logger = logging.getLogger(__name__)


class ExponentialJitterBackoff:
    """Exponential backoff with jitter.

    Based on infrastructure/router.py:270,280 logic:
    - Exponential: delay = base_delay * (2 ** attempt)
    - Jitter: random factor to prevent thundering herd
    """

    @property
    def name(self) -> str:
        return "exponential_jitter"

    def __init__(
        self,
        max_delay: float = 60.0,
        jitter_factor: float = 0.1,
    ) -> None:
        """Initialize exponential jitter backoff.

        Args:
            max_delay: Maximum delay in seconds (default: 60)
            jitter_factor: Jitter factor (0.0 to 1.0, default: 0.1)
        """
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor

    def calculate_delay(self, input_data: BackoffInput, context: dict[str, Any]) -> BackoffResult:
        """Calculate exponential backoff with jitter.

        Args:
            input_data: Backoff input
            context: Context

        Returns:
            Backoff result with delay
        """
        # Calculate exponential delay
        exp_delay = input_data.base_delay * (2**input_data.attempt)

        # Apply jitter
        # S311: Using random for backoff jitter (not security-sensitive)
        jitter = random.uniform(-self.jitter_factor * exp_delay, self.jitter_factor * exp_delay)
        delay = exp_delay + jitter

        # Cap at max_delay
        max_delay = input_data.max_delay or self.max_delay
        delay = min(delay, max_delay)
        delay = max(delay, 0.0)  # Ensure non-negative

        logger.debug("Calculated backoff: attempt=%s, delay=%ss", input_data.attempt, delay)
        return BackoffResult(
            delay=delay,
            attempt=input_data.attempt,
            metadata={
                "strategy": self.name,
                "base_delay": input_data.base_delay,
                "exponential_delay": exp_delay,
                "jitter": jitter,
                "max_delay": max_delay,
            },
        )

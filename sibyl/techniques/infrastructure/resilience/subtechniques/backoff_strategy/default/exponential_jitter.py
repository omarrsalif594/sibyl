"""
Exponential Backoff with Jitter

Original logic from infrastructure/router.py:270,280:
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = delay * (jitter_percent / 100) * random.random()
    actual_delay = delay + jitter

Implements exponential backoff with random jitter to prevent thundering herd.
"""

import random
from typing import Any

from sibyl.techniques.protocols import SubtechniqueImplementation, SubtechniqueResult


class ExponentialJitterBackoff(SubtechniqueImplementation):
    """Calculate retry delay using exponential backoff with jitter."""

    def execute(self, context: dict[str, Any], **kwargs) -> SubtechniqueResult:
        """
        Calculate backoff delay with exponential growth and jitter.

        Args:
            context: Must contain:
                - 'attempt': int, retry attempt number (0-indexed)
                - 'base_delay': float, base delay in seconds (optional)
            **kwargs: Additional arguments (ignored)

        Returns:
            SubtechniqueResult with calculated delay

        Example:
            >>> impl = ExponentialJitterBackoff(config)
            >>> result = impl.execute({'attempt': 2, 'base_delay': 1.0})
            >>> result.result['delay']  # ~4.0-4.8 seconds (4 * 2^2 + jitter)
        """
        attempt = context.get("attempt", 0)
        base_delay = context.get("base_delay", self.config.get("base_delay", 1.0))

        # Get parameters from config
        max_delay = self.config.get("max_delay", 60.0)
        jitter_percent = self.config.get("jitter_percent", 20)
        exponential_base = self.config.get("exponential_base", 2)

        # Calculate exponential delay
        exponential_delay = base_delay * (exponential_base**attempt)

        # Cap at max_delay
        capped_delay = min(exponential_delay, max_delay)

        # Add random jitter
        # S311: Using random for backoff jitter (not security-sensitive)
        jitter_range = capped_delay * (jitter_percent / 100.0)
        jitter = jitter_range * random.random()
        final_delay = capped_delay + jitter

        return SubtechniqueResult(
            success=True,
            result={
                "delay": final_delay,
                "base_delay": capped_delay,
                "jitter": jitter,
                "attempt": attempt,
                "method": "exponential_jitter",
            },
            metadata={
                "exponential_delay": exponential_delay,
                "capped": exponential_delay > max_delay,
                "max_delay": max_delay,
                "jitter_percent": jitter_percent,
            },
        )

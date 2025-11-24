"""Exponential backoff retry strategy implementation.

Implements exponential backoff with configurable base delay and multiplier.
Delay increases exponentially: base_delay * (multiplier ^ attempt).
"""

from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.ai_generation.validation.subtechniques.qc_verdict.default.quality_control import (
    ValidationVerdict,
    VerdictStatus,
)


class ExponentialBackoffRetry:
    """Exponential backoff retry strategy implementation."""

    def __init__(self) -> None:
        self._name = "exponential_backoff"
        self._description = "Retry with exponentially increasing delays"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> dict[str, Any]:
        """Calculate retry decision and backoff delay.

        Args:
            input_data: Dict with 'verdict', 'attempt', and 'max_attempts' keys
            config: Merged configuration with 'base_delay' and 'multiplier'

        Returns:
            Dict with 'should_retry' (bool) and 'backoff_delay' (float)
        """
        verdict: ValidationVerdict = input_data.get("verdict")
        attempt: int = input_data.get("attempt", 1)
        max_attempts: int = input_data.get("max_attempts", 3)

        # Extract configuration
        base_delay = config.get("base_delay", 1.0)
        multiplier = config.get("multiplier", 2.0)
        max_delay = config.get("max_delay", 60.0)

        # Determine if should retry
        should_retry = (
            verdict is not None and verdict.status == VerdictStatus.RED and attempt < max_attempts
        )

        # Calculate exponential backoff delay
        delay = min(base_delay * multiplier ** (attempt - 1), max_delay) if should_retry else 0.0

        return {
            "should_retry": should_retry,
            "backoff_delay": delay,
            "attempt": attempt,
            "max_attempts": max_attempts,
        }

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {
            "base_delay": 1.0,
            "multiplier": 2.0,
            "max_delay": 60.0,
        }

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "base_delay" in config and config["base_delay"] <= 0:
            return False
        if "multiplier" in config and config["multiplier"] <= 1:
            return False
        return not ("max_delay" in config and config["max_delay"] <= 0)

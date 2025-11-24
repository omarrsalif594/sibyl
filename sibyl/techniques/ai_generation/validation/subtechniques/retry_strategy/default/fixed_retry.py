"""Fixed delay retry strategy implementation.

Implements retry with fixed delay between attempts.
Simple and predictable retry pattern.
"""

from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.ai_generation.validation.subtechniques.qc_verdict.default.quality_control import (
    ValidationVerdict,
    VerdictStatus,
)


class FixedRetry:
    """Fixed delay retry strategy implementation."""

    def __init__(self) -> None:
        self._name = "fixed_retry"
        self._description = "Retry with fixed delay between attempts"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> dict[str, Any]:
        """Calculate retry decision and fixed delay.

        Args:
            input_data: Dict with 'verdict', 'attempt', and 'max_attempts' keys
            config: Merged configuration with 'retry_delay'

        Returns:
            Dict with 'should_retry' (bool) and 'backoff_delay' (float)
        """
        verdict: ValidationVerdict = input_data.get("verdict")
        attempt: int = input_data.get("attempt", 1)
        max_attempts: int = input_data.get("max_attempts", 3)

        # Extract configuration
        retry_delay = config.get("retry_delay", 2.0)

        # Determine if should retry
        should_retry = (
            verdict is not None and verdict.status == VerdictStatus.RED and attempt < max_attempts
        )

        return {
            "should_retry": should_retry,
            "backoff_delay": retry_delay if should_retry else 0.0,
            "attempt": attempt,
            "max_attempts": max_attempts,
        }

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {
            "retry_delay": 2.0,
        }

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return not ("retry_delay" in config and config["retry_delay"] < 0)

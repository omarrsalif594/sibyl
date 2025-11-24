"""No retry strategy implementation.

Never retries - returns failure immediately on RED verdict.
Useful for fast-fail scenarios or when retries are not desired.
"""

from pathlib import Path
from typing import Any

import yaml


class NoRetry:
    """No retry strategy implementation."""

    def __init__(self) -> None:
        self._name = "no_retry"
        self._description = "Never retry - fail immediately"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> dict[str, Any]:
        """Never retry.

        Args:
            input_data: Dict with 'verdict', 'attempt', and 'max_attempts' keys
            config: Merged configuration (not used for no_retry)

        Returns:
            Dict with 'should_retry' (False) and 'backoff_delay' (0.0)
        """
        attempt: int = input_data.get("attempt", 1)
        max_attempts: int = input_data.get("max_attempts", 1)

        return {
            "should_retry": False,
            "backoff_delay": 0.0,
            "attempt": attempt,
            "max_attempts": max_attempts,
        }

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True

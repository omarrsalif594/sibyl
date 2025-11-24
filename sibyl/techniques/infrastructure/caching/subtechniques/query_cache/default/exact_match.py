"""
Exact Match implementation for query_cache.
"""

from pathlib import Path
from typing import Any

import yaml


def _extract(input_data: Any) -> tuple[str, Any]:
    if isinstance(input_data, dict):
        return str(input_data.get("query", "")), input_data.get("value")
    return str(input_data or ""), None


class ExactMatchImplementation:
    """Exact Match implementation."""

    def __init__(self) -> None:
        self._name = "exact_match"
        self._description = "Exact Match implementation"
        self._config_path = Path(__file__).parent.parent / "config.yaml"
        self._cache: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> Any:
        """Execute the implementation.

        Args:
            input_data: Input data to process
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            Implementation-specific output
        """
        query, value = _extract(input_data)

        if not query:
            msg = "Query must be provided for caching"
            raise ValueError(msg)

        if query in self._cache:
            return {"hit": True, "value": self._cache[query]}

        if value is not None:
            self._cache[query] = value

        return {"hit": False, "value": value}

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return isinstance(config, dict)

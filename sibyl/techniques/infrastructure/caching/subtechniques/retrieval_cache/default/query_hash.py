"""
Query Hash implementation for retrieval_cache.
"""

import hashlib
from pathlib import Path
from typing import Any

import yaml


def _extract(input_data: Any) -> tuple[str, Any]:
    if isinstance(input_data, dict):
        return str(input_data.get("query", "")), input_data.get("value")
    return str(input_data or ""), None


class QueryHashImplementation:
    """Query Hash implementation."""

    def __init__(self) -> None:
        self._name = "query_hash"
        self._description = "Query Hash implementation"
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
            msg = "query is required"
            raise ValueError(msg)

        hashed = hashlib.sha1(query.encode("utf-8")).hexdigest()

        if hashed in self._cache:
            return {"hit": True, "value": self._cache[hashed], "key": hashed}

        if value is not None:
            self._cache[hashed] = value

        return {"hit": False, "value": value, "key": hashed}

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return isinstance(config, dict)

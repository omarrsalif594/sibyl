"""
Ttl implementation for embedding_cache.
"""

import time
from pathlib import Path
from typing import Any

import yaml


def _extract(input_data: Any) -> tuple[Any, Any]:
    if isinstance(input_data, dict):
        return input_data.get("key"), input_data.get("value")
    return input_data, None


class TtlImplementation:
    """Ttl implementation."""

    def __init__(self) -> None:
        self._name = "ttl"
        self._description = "Ttl implementation"
        self._config_path = Path(__file__).parent.parent / "config.yaml"
        self._cache: dict[Any, tuple[Any, float]] = {}

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
        key, value = _extract(input_data)
        if key is None:
            msg = "Caching requires a key"
            raise ValueError(msg)

        ttl_seconds = float(config.get("ttl_seconds", 3600))
        now = time.time()

        # Evict expired
        if key in self._cache:
            cached_value, expires_at = self._cache[key]
            if expires_at > now:
                return {"hit": True, "value": cached_value, "expires_at": expires_at}
            self._cache.pop(key, None)

        if value is not None:
            self._cache[key] = (value, now + ttl_seconds)
            return {"hit": False, "value": value, "expires_at": now + ttl_seconds}

        return {"hit": False, "value": None}

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if not isinstance(config.get("ttl_seconds", 0), (int, float)):
            msg = "ttl_seconds must be numeric"
            raise TypeError(msg)
        return True

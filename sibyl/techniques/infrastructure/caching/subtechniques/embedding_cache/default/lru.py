"""
Lru implementation for embedding_cache.
"""

from collections import OrderedDict
from pathlib import Path
from typing import Any

import yaml


def _extract(input_data: Any) -> tuple[Any, Any]:
    if isinstance(input_data, dict):
        return input_data.get("key"), input_data.get("value")
    return input_data, None


class LruImplementation:
    """Lru implementation."""

    def __init__(self) -> None:
        self._name = "lru"
        self._description = "Lru implementation"
        self._config_path = Path(__file__).parent.parent / "config.yaml"
        self._cache: OrderedDict[Any, Any] = OrderedDict()

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

        max_size = int(config.get("max_size", 128))

        if key in self._cache:
            cached = self._cache.pop(key)
            self._cache[key] = cached
            return {"hit": True, "value": cached, "size": len(self._cache)}

        if value is not None:
            self._cache[key] = value
            if len(self._cache) > max_size:
                self._cache.popitem(last=False)

        return {"hit": False, "value": value, "size": len(self._cache)}

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if not isinstance(config.get("max_size", 0), (int, float)):
            msg = "max_size must be numeric"
            raise TypeError(msg)
        return True

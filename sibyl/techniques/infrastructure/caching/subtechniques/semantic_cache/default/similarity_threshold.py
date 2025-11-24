"""
Similarity Threshold implementation for semantic_cache.
"""

from pathlib import Path
from typing import Any

import yaml


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in text.split() if t.strip()]


def _similarity(a: str, b: str) -> float:
    a_tokens = set(_tokenize(a))
    b_tokens = set(_tokenize(b))
    if not a_tokens or not b_tokens:
        return 0.0
    overlap = len(a_tokens.intersection(b_tokens))
    return overlap / len(a_tokens.union(b_tokens))


class SimilarityThresholdImplementation:
    """Similarity Threshold implementation."""

    def __init__(self) -> None:
        self._name = "similarity_threshold"
        self._description = "Similarity Threshold implementation"
        self._config_path = Path(__file__).parent.parent / "config.yaml"
        self._cache: list[tuple[str, Any]] = []

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
        if not isinstance(input_data, dict):
            msg = "Input must be dict with 'key' and optional 'value'"
            raise TypeError(msg)

        key = str(input_data.get("key", ""))
        value = input_data.get("value")
        threshold = float(config.get("similarity_threshold", 0.65))

        best_score = 0.0
        best_value = None
        for cached_key, cached_value in self._cache:
            score = _similarity(key, cached_key)
            if score > best_score:
                best_score = score
                best_value = cached_value

        if best_score >= threshold and best_value is not None:
            return {"hit": True, "value": best_value, "score": best_score}

        if value is not None:
            self._cache.append((key, value))

        return {"hit": False, "value": value, "score": best_score}

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if not isinstance(config.get("similarity_threshold", 0.0), (int, float)):
            msg = "similarity_threshold must be numeric"
            raise TypeError(msg)
        return True

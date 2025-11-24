"""
Semantic implementation for retrieval_cache.
"""

from pathlib import Path
from typing import Any

import yaml


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in text.split() if t.strip()]


def _similarity(query: str, candidate: str) -> float:
    q_tokens = set(_tokenize(query))
    c_tokens = set(_tokenize(candidate))
    if not q_tokens or not c_tokens:
        return 0.0
    intersection = len(q_tokens.intersection(c_tokens))
    return intersection / float(len(q_tokens.union(c_tokens)))


class SemanticImplementation:
    """Semantic implementation."""

    def __init__(self) -> None:
        self._name = "semantic"
        self._description = "Semantic implementation"
        self._config_path = Path(__file__).parent.parent / "config.yaml"
        self._entries: list[tuple[str, Any]] = []

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
            msg = "Input must be a dict with 'query'/'value'"
            raise TypeError(msg)

        query = input_data.get("query", "")
        value = input_data.get("value")
        threshold = float(config.get("similarity_threshold", 0.7))

        best_match = None
        best_score = 0.0
        for stored_query, stored_value in self._entries:
            score = _similarity(query, stored_query)
            if score > best_score:
                best_score = score
                best_match = stored_value

        if best_score >= threshold and best_match is not None:
            return {"hit": True, "value": best_match, "score": best_score}

        if value is not None:
            self._entries.append((query, value))

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

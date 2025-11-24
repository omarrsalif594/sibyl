"""
Keyword Match implementation for relevance.
"""

from pathlib import Path
from typing import Any

import yaml


def _normalize_input(input_data: Any) -> tuple[str, str, dict[str, Any]]:
    if isinstance(input_data, dict):
        query = input_data.get("query") or ""
        response = input_data.get("response") or input_data.get("content") or ""
        metadata = {
            k: v for k, v in input_data.items() if k not in {"query", "response", "content"}
        }
    else:
        query = ""
        response = "" if input_data is None else str(input_data)
        metadata = {}
    return query, response, metadata


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in text.split() if t.strip()]


class KeywordMatchImplementation:
    """Keyword Match implementation."""

    def __init__(self) -> None:
        self._name = "keyword_match"
        self._description = "Keyword Match implementation"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

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
        query, response, metadata = _normalize_input(input_data)
        keywords = config.get("keywords") or _tokenize(query)

        if not keywords:
            return {"score": 0.0, "matched_keywords": []}

        matched = [kw for kw in keywords if kw in response.lower()]
        score = len(matched) / len(keywords)

        metadata["relevance"] = {"matched": matched, "total_keywords": len(keywords)}
        return {"score": round(score, 2), "matched_keywords": matched, "metadata": metadata}

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f)
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        # TODO: Add validation logic
        return True

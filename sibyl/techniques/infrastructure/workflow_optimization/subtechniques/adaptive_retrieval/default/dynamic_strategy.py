"""
Dynamic Strategy implementation for adaptive_retrieval.
"""

from pathlib import Path
from typing import Any

import yaml


def _normalize_input(input_data: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(input_data, dict):
        query = input_data.get("query") or ""
        metadata = {k: v for k, v in input_data.items() if k != "query"}
    else:
        query = "" if input_data is None else str(input_data)
        metadata = {}
    return query, metadata


class DynamicStrategyImplementation:
    """Dynamic Strategy implementation."""

    def __init__(self) -> None:
        self._name = "dynamic_strategy"
        self._description = "Dynamic Strategy implementation"
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
        query, metadata = _normalize_input(input_data)
        length_threshold = int(config.get("length_threshold", 120))
        has_code = "`" in query or "def " in query

        if has_code:
            strategy = "code_retrieval"
        elif len(query) > length_threshold:
            strategy = "hybrid"
        else:
            strategy = "keyword"

        metadata["strategy"] = strategy
        return {"strategy": strategy, "metadata": metadata}

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

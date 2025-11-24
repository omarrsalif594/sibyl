"""
Ml Routing implementation for query_routing.
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


class MlRoutingImplementation:
    """Ml Routing implementation."""

    def __init__(self) -> None:
        self._name = "ml_routing"
        self._description = "Ml Routing implementation"
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
        score = len(query)
        route = "search" if "?" in query else "generation"
        if score > config.get("analysis_threshold", 200):
            route = "analysis"

        metadata["routing"] = {"route": route, "score": score}
        return {"route": route, "metadata": metadata}

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

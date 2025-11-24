"""
Routing Rules implementation for query_routing.
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


class RoutingRulesImplementation:
    """Routing Rules implementation."""

    def __init__(self) -> None:
        self._name = "routing_rules"
        self._description = "Routing Rules implementation"
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
        rules: dict[str, str] = config.get("rules") or {
            "code": "code_path",
            "error": "support_path",
        }
        chosen = config.get("default_route", "general")

        for keyword, route in rules.items():
            if keyword.lower() in query.lower():
                chosen = route
                break

        metadata["routing"] = {"route": chosen}
        return {"route": chosen, "metadata": metadata}

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

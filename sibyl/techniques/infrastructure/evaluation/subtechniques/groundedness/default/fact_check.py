"""
Fact Check implementation for groundedness.
"""

from pathlib import Path
from typing import Any

import yaml


def _normalize_input(input_data: Any) -> tuple[str, list[str], dict[str, Any]]:
    if isinstance(input_data, dict):
        response = input_data.get("response") or input_data.get("content") or ""
        facts = input_data.get("facts") or input_data.get("context") or []
        if isinstance(facts, str):
            facts = [facts]
        metadata = {
            k: v
            for k, v in input_data.items()
            if k not in {"response", "content", "facts", "context"}
        }
    else:
        response = "" if input_data is None else str(input_data)
        facts = []
        metadata = {}
    return response, facts, metadata


class FactCheckImplementation:
    """Fact Check implementation."""

    def __init__(self) -> None:
        self._name = "fact_check"
        self._description = "Fact Check implementation"
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
        response, facts, metadata = _normalize_input(input_data)
        checked = 0

        for fact in facts:
            if fact and str(fact).lower() in response.lower():
                checked += 1

        grounded = checked == len(facts) if facts else True
        score = 1.0 if grounded else checked / max(len(facts), 1)

        metadata["fact_check"] = {"verified": checked, "total": len(facts)}
        return {"score": round(score, 2), "grounded": grounded, "metadata": metadata}

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

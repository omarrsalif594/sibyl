"""
Source Attribution implementation for faithfulness.
"""

from pathlib import Path
from typing import Any

import yaml


def _normalize_input(input_data: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(input_data, dict):
        response = input_data.get("response") or input_data.get("content") or ""
        metadata = {k: v for k, v in input_data.items() if k not in {"response", "content"}}
    else:
        response = "" if input_data is None else str(input_data)
        metadata = {}
    return response, metadata


class SourceAttributionImplementation:
    """Source Attribution implementation."""

    def __init__(self) -> None:
        self._name = "source_attribution"
        self._description = "Source Attribution implementation"
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
        response, metadata = _normalize_input(input_data)
        sources: list[str] = metadata.get("sources") or config.get("sources") or []

        if not sources:
            return {"score": 0.5, "missing_sources": True, "response": response}

        coverage = 0
        for source in sources:
            if str(source) in response:
                coverage += 1

        score = coverage / len(sources)
        return {
            "score": round(score, 2),
            "missing_sources": coverage < len(sources),
            "attributed_sources": coverage,
            "total_sources": len(sources),
        }

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

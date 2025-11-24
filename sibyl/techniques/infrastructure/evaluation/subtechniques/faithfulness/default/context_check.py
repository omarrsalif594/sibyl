"""
Context Check implementation for faithfulness.
"""

from pathlib import Path
from typing import Any

import yaml


def _normalize_input(input_data: Any) -> tuple[str, list[str], dict[str, Any]]:
    if isinstance(input_data, dict):
        response = input_data.get("response") or input_data.get("content") or ""
        context = input_data.get("context") or []
        if isinstance(context, str):
            context = [context]
        metadata = {
            k: v for k, v in input_data.items() if k not in {"response", "content", "context"}
        }
    else:
        response = "" if input_data is None else str(input_data)
        context = []
        metadata = {}
    return response, context, metadata


class ContextCheckImplementation:
    """Context Check implementation."""

    def __init__(self) -> None:
        self._name = "context_check"
        self._description = "Context Check implementation"
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
        response, context, metadata = _normalize_input(input_data)
        if not context:
            return {"score": 0.5, "context_used": 0, "context_count": 0}

        hits = 0
        for snippet in context:
            if snippet and str(snippet).lower() in response.lower():
                hits += 1

        score = hits / len(context)
        metadata["context_check"] = {"matches": hits, "total": len(context)}
        return {"score": round(score, 2), "metadata": metadata}

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

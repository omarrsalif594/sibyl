"""
Token Budget implementation for cost_optimization.
"""

from pathlib import Path
from typing import Any

import yaml


def _normalize_input(input_data: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(input_data, dict):
        content = input_data.get("content") or input_data.get("prompt") or ""
        metadata = {k: v for k, v in input_data.items() if k not in {"content", "prompt"}}
    else:
        content = "" if input_data is None else str(input_data)
        metadata = {}
    return content, metadata


class TokenBudgetImplementation:
    """Token Budget implementation."""

    def __init__(self) -> None:
        self._name = "token_budget"
        self._description = "Token Budget implementation"
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
        prompt, metadata = _normalize_input(input_data)
        max_tokens = int(config.get("max_tokens", 200))
        tokens: list[str] = prompt.split()

        trimmed = len(tokens) > max_tokens
        if trimmed:
            tokens = tokens[:max_tokens]
        content = " ".join(tokens)

        metadata["token_budget"] = {"trimmed": trimmed, "max_tokens": max_tokens}
        return {"content": content, "metadata": metadata}

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

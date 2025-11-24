"""
Pattern Based implementation for prompt_injection_detection.
"""

import re
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


class PatternBasedImplementation:
    """Pattern Based implementation."""

    def __init__(self) -> None:
        self._name = "pattern_based"
        self._description = "Pattern Based implementation"
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
        patterns: list[str] = config.get("injection_patterns") or [
            r"ignore previous",
            r"override instructions",
            r"disregard earlier",
            r"system prompt",
        ]

        detected = [pat for pat in patterns if re.search(pat, prompt, re.IGNORECASE)]
        score = min(1.0, len(detected) / max(len(patterns), 1))

        metadata["prompt_injection"] = {"matches": detected, "score": score}
        return {"is_injection": bool(detected), "score": round(score, 2), "metadata": metadata}

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

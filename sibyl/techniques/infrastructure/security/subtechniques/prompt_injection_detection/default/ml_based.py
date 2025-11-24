"""
Ml Based implementation for prompt_injection_detection.
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


class MlBasedImplementation:
    """Ml Based implementation."""

    def __init__(self) -> None:
        self._name = "ml_based"
        self._description = "Ml Based implementation"
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
        pattern_hits = len(re.findall(r"(ignore|override|reset)", prompt, re.IGNORECASE))
        max_len = int(config.get("max_prompt_length", 4000))
        length_penalty = 0.1 if len(prompt) > max_len else 0.0

        score = min(1.0, pattern_hits * 0.25 + length_penalty)
        threshold = float(config.get("suspicion_threshold", 0.4))

        metadata["prompt_injection"] = {
            "pattern_hits": pattern_hits,
            "length_penalty": length_penalty,
            "threshold": threshold,
        }
        return {"is_injection": score >= threshold, "score": round(score, 2), "metadata": metadata}

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

"""
Hallucination Detect implementation for groundedness.
"""

import re
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


class HallucinationDetectImplementation:
    """Hallucination Detect implementation."""

    def __init__(self) -> None:
        self._name = "hallucination_detect"
        self._description = "Hallucination Detect implementation"
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
        patterns = [
            r"as an ai",
            r"cannot access",
            r"imaginary",
            r"not actually",
            r"guess",
        ]
        flags = sum(bool(re.search(pat, response, re.IGNORECASE)) for pat in patterns)
        risk = min(1.0, flags * 0.25)

        metadata["hallucination"] = {"flags": flags, "patterns_checked": len(patterns)}
        return {"score": round(1 - risk, 2), "risk": round(risk, 2), "metadata": metadata}

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

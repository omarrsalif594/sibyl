"""
Presidio implementation for pii_redaction.
"""

import re
from pathlib import Path
from typing import Any

import yaml

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.IGNORECASE)
PHONE = re.compile(r"\b\d{3}[-.\s]?\d{2,3}[-.\s]?\d{4}\b")


def _normalize_input(input_data: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(input_data, dict):
        content = input_data.get("content") or input_data.get("text") or ""
        metadata = {k: v for k, v in input_data.items() if k not in {"content", "text"}}
    else:
        content = "" if input_data is None else str(input_data)
        metadata = {}
    return content, metadata


class PresidioImplementation:
    """Presidio implementation."""

    def __init__(self) -> None:
        self._name = "presidio"
        self._description = "Presidio implementation"
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
        content, metadata = _normalize_input(input_data)
        matches = []

        for pattern in (EMAIL, PHONE):
            matches.extend(pattern.findall(content))
            content = pattern.sub("[REDACTED]", content)

        metadata["pii_redaction"] = {"matches": matches, "method": "presidio-lite"}
        return {"content": content, "metadata": metadata, "redacted": bool(matches)}

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

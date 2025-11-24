"""
Spacy implementation for pii_redaction.
"""

import re
from pathlib import Path
from typing import Any

import yaml


def _normalize_input(input_data: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(input_data, dict):
        content = input_data.get("content") or input_data.get("text") or ""
        metadata = {k: v for k, v in input_data.items() if k not in {"content", "text"}}
    else:
        content = "" if input_data is None else str(input_data)
        metadata = {}
    return content, metadata


class SpacyImplementation:
    """Spacy implementation."""

    def __init__(self) -> None:
        self._name = "spacy"
        self._description = "Spacy implementation"
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
        # Simple name detection: capitalized words longer than 2 characters
        names = re.findall(r"\b[A-Z][a-z]{2,}\b", content)
        redacted = content
        for name in names:
            redacted = re.sub(rf"\b{name}\b", "[NAME]", redacted)

        metadata["pii_redaction"] = {"names_redacted": len(names), "method": "pattern"}
        return {"content": redacted, "metadata": metadata, "redacted": bool(names)}

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

"""
Spacy implementation for entity_linking.
"""

import re
from pathlib import Path
from typing import Any

import yaml


def _normalize(input_data: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(input_data, dict):
        content = input_data.get("content", "")
        metadata = {k: v for k, v in input_data.items() if k != "content"}
    else:
        content = "" if input_data is None else str(input_data)
        metadata = {}
    return content, metadata


def _detect_entities(text: str) -> list[str]:
    pattern = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")
    return list(dict.fromkeys(pattern.findall(text)))


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
        content, metadata = _normalize(input_data)
        entities = _detect_entities(content)
        metadata["entities"] = [{"value": entity, "method": "rule_based"} for entity in entities]
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

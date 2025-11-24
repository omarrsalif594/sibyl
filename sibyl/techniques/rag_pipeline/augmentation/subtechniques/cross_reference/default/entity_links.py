"""
Entity Links implementation for cross_reference.
"""

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml


def _normalize(input_data: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(input_data, dict):
        content = input_data.get("content", "")
        metadata = {k: v for k, v in input_data.items() if k != "content"}
    else:
        content = "" if input_data is None else str(input_data)
        metadata = {}
    return content, metadata


def _extract_entities(text: str) -> list[str]:
    pattern = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")
    return list(dict.fromkeys(pattern.findall(text)))


class EntityLinksImplementation:
    """Entity Links implementation."""

    def __init__(self) -> None:
        self._name = "entity_links"
        self._description = "Entity Links implementation"
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
        base_url = config.get("entity_base_url", "entity://")
        entities = metadata.get("entities") or _extract_entities(content)

        metadata["entity_links"] = [
            {"entity": entity, "link": f"{base_url}{quote(entity)}"} for entity in entities
        ]

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

"""
Template implementation for basic_generation.
"""

from pathlib import Path
from typing import Any

import yaml


def _normalize_input(input_data: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if isinstance(input_data, dict):
        content = input_data
        metadata = {}
    else:
        content = {"content": "" if input_data is None else str(input_data)}
        metadata = {}
    return content, metadata


class TemplateImplementation:
    """Template implementation."""

    def __init__(self) -> None:
        self._name = "template"
        self._description = "Template implementation"
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
        payload, metadata = _normalize_input(input_data)
        template = config.get("template", "{content}")
        try:
            rendered = template.format(**payload)
        except Exception:
            # Fall back to simple str replacement
            rendered = template.replace("{content}", str(payload.get("content", "")))

        metadata["generation"] = {"strategy": "template", "template_used": template}
        return {"content": rendered, "metadata": metadata}

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

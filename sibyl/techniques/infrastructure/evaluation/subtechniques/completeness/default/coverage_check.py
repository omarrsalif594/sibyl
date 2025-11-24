"""
Coverage Check implementation for completeness.
"""

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


class CoverageCheckImplementation:
    """Coverage Check implementation."""

    def __init__(self) -> None:
        self._name = "coverage_check"
        self._description = "Coverage Check implementation"
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
        required: list[str] = (
            config.get("required_sections") or metadata.get("required_sections") or []
        )

        if not required:
            return {"score": 1.0, "covered": [], "metadata": metadata}

        covered = [section for section in required if section.lower() in response.lower()]
        score = len(covered) / len(required)

        metadata["completeness"] = {"covered": covered, "required": required}
        return {"score": round(score, 2), "covered": covered, "metadata": metadata}

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

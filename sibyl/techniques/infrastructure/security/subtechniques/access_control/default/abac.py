"""
Abac implementation for access_control.
"""

from pathlib import Path
from typing import Any

import yaml


class AbacImplementation:
    """Abac implementation."""

    def __init__(self) -> None:
        self._name = "abac"
        self._description = "Abac implementation"
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
        attributes = input_data if isinstance(input_data, dict) else {}
        rules = config.get("rules") or {}

        missing = {}
        for key, expected in rules.items():
            if attributes.get(key) != expected:
                missing[key] = {"expected": expected, "actual": attributes.get(key)}

        allowed = len(missing) == 0
        return {"allowed": allowed, "missing_attributes": missing, "attributes": attributes}

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

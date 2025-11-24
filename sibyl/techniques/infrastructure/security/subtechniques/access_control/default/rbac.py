"""
Rbac implementation for access_control.
"""

from pathlib import Path
from typing import Any

import yaml


class RbacImplementation:
    """Rbac implementation."""

    def __init__(self) -> None:
        self._name = "rbac"
        self._description = "Rbac implementation"
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
        user_roles: set[str] = set()
        if isinstance(input_data, dict):
            roles = input_data.get("roles") or input_data.get("user_roles") or []
            user_roles = {str(r) for r in roles}

        required: list[str] = config.get("required_roles") or ["reader"]
        missing = [role for role in required if role not in user_roles]
        allowed = len(missing) == 0

        return {"allowed": allowed, "missing_roles": missing, "granted_roles": list(user_roles)}

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

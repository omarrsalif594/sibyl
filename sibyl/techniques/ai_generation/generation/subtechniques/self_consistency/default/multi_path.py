"""
Multi Path implementation for self_consistency.
"""

from pathlib import Path
from typing import Any

import yaml


def _normalize_paths(input_data: Any) -> tuple[list[str], dict[str, Any]]:
    metadata: dict[str, Any] = {}
    if isinstance(input_data, dict):
        paths = input_data.get("paths") or input_data.get("candidates") or []
        metadata = {k: v for k, v in input_data.items() if k not in {"paths", "candidates"}}
    elif isinstance(input_data, list):
        paths = [str(item) for item in input_data]
    else:
        paths = [str(input_data)] if input_data is not None else []
    return paths, metadata


class MultiPathImplementation:
    """Multi Path implementation."""

    def __init__(self) -> None:
        self._name = "multi_path"
        self._description = "Multi Path implementation"
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
        paths, metadata = _normalize_paths(input_data)
        max_paths = config.get("max_paths", 3)
        selected = paths[:max_paths]

        merged = " | ".join(selected)
        metadata["multi_path"] = {"selected": len(selected), "total": len(paths)}

        return {"content": merged, "metadata": metadata}

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

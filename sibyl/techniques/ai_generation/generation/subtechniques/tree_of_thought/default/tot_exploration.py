"""Tot Exploration implementation for tree_of_thought."""

from pathlib import Path
from typing import Any

import yaml


def _normalize_input(input_data: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(input_data, dict):
        content = input_data.get("content", "")
        metadata = {k: v for k, v in input_data.items() if k != "content"}
    else:
        content = "" if input_data is None else str(input_data)
        metadata = {}
    return content, metadata


class TotExplorationImplementation:
    """Tot Exploration implementation."""

    def __init__(self) -> None:
        self._name = "tot_exploration"
        self._description = "Tot Exploration implementation"
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
        prompt, metadata = _normalize_input(input_data)
        max_depth = int(config.get("max_depth", 2))

        branches: list[str] = []
        for depth in range(1, max_depth + 1):
            branches.append(f"Depth {depth}: explore variation of '{prompt}' (path {depth})")

        metadata["tree_of_thought"] = {"depth": max_depth, "branches": len(branches)}
        return {"content": "\n".join(branches), "metadata": metadata}

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

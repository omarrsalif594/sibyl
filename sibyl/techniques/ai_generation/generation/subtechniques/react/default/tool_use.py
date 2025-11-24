"""
Tool Use implementation for react.
"""

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


class ToolUseImplementation:
    """Tool Use implementation."""

    def __init__(self) -> None:
        self._name = "tool_use"
        self._description = "Tool Use implementation"
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
        tools: list[dict[str, Any]] = metadata.get("tools") or config.get("tools") or []

        chosen_tool = None
        if tools:
            # Pick the first available tool or one matching preferred capability
            preferred = config.get("preferred_capability")
            for tool in tools:
                if not preferred or preferred in tool.get("capabilities", []):
                    chosen_tool = tool
                    break
            chosen_tool = chosen_tool or tools[0]

        action = chosen_tool["name"] if chosen_tool else "no_tool"
        content = f"Tool decision: {action} for prompt '{prompt}'."

        metadata["react"] = {"tool_selected": action, "tool_count": len(tools)}
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

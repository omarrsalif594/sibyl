"""
Step By Step implementation for chain_of_thought.
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


class StepByStepImplementation:
    """Step By Step implementation."""

    def __init__(self) -> None:
        self._name = "step_by_step"
        self._description = "Step By Step implementation"
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
        segments = [seg.strip() for seg in prompt.replace("\n", " ").split(".") if seg.strip()]
        if not segments and prompt:
            segments = [prompt]

        steps: list[str] = [f"Step {idx + 1}: {seg}" for idx, seg in enumerate(segments)]
        explanation = "\n".join(steps) if steps else "No steps derived from prompt."

        metadata["reasoning"] = {"steps": steps, "derived_from": "prompt"}
        return {"content": explanation, "metadata": metadata}

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

"""
Confidence Threshold implementation for early_stopping.
"""

from pathlib import Path
from typing import Any

import yaml


class ConfidenceThresholdImplementation:
    """Confidence Threshold implementation."""

    def __init__(self) -> None:
        self._name = "confidence_threshold"
        self._description = "Confidence Threshold implementation"
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
        threshold = float(config.get("min_confidence", 0.75))
        scores: list[float] = []

        if isinstance(input_data, dict):
            scores = [float(s) for s in input_data.get("scores", [])]
            if "confidence" in input_data:
                scores.append(float(input_data["confidence"]))
        elif isinstance(input_data, (list, tuple)):
            scores = [float(s) for s in input_data]

        best = max(scores) if scores else 0.0
        stop = best >= threshold

        return {"stop": stop, "best_confidence": best, "threshold": threshold}

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

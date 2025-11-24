"""Rule-based quality scoring implementation.

Calculates quality score based on validation verdict status:
- GREEN: High score (configurable)
- YELLOW: Medium score (configurable)
- RED: Low score (0.0)
"""

from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.ai_generation.validation.subtechniques.qc_verdict.default.quality_control import (
    ValidationVerdict,
    VerdictStatus,
)


class RuleBasedScoring:
    """Rule-based quality scoring implementation."""

    def __init__(self) -> None:
        self._name = "rule_based"
        self._description = "Score based on verdict status using fixed rules"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> dict[str, Any]:
        """Calculate quality score based on verdict.

        Args:
            input_data: Dict with 'output', 'context', and optionally 'verdict'
            config: Merged configuration with score mappings

        Returns:
            Dict with 'quality_score' (float 0.0-1.0) and 'score_metadata'
        """
        input_data.get("output")
        input_data.get("context", {})
        verdict: ValidationVerdict | None = input_data.get("verdict")

        # Extract configuration
        green_score = config.get("green_score", 1.0)
        yellow_score = config.get("yellow_score", 0.7)
        red_score = config.get("red_score", 0.0)

        # Calculate score based on verdict status
        if verdict is None:
            # No verdict - return neutral score
            score = 0.5
            status = "no_verdict"
        elif verdict.status == VerdictStatus.GREEN:
            score = green_score
            status = "green"
        elif verdict.status == VerdictStatus.YELLOW:
            score = yellow_score
            status = "yellow"
        else:  # RED
            score = red_score
            status = "red"

        return {
            "quality_score": score,
            "score_metadata": {
                "verdict_status": status,
                "scorer": self._name,
                "verdict_id": verdict.validation_id if verdict else None,
            },
        }

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {
            "green_score": 1.0,
            "yellow_score": 0.7,
            "red_score": 0.0,
        }

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        for key in ["green_score", "yellow_score", "red_score"]:
            if key in config:
                val = config[key]
                if not (0.0 <= val <= 1.0):
                    return False
        return True

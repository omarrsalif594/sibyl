"""Threshold-based quality scoring implementation.

Calculates quality score based on multiple metrics and thresholds:
- Verdict status (primary factor)
- Number of warnings/issues (secondary factor)
- Custom metric thresholds
"""

from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.ai_generation.validation.subtechniques.qc_verdict.default.quality_control import (
    ValidationVerdict,
    VerdictStatus,
)


class ThresholdBasedScoring:
    """Threshold-based quality scoring implementation."""

    def __init__(self) -> None:
        self._name = "threshold_based"
        self._description = "Score based on multiple thresholds and metrics"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> dict[str, Any]:
        """Calculate quality score based on thresholds.

        Args:
            input_data: Dict with 'output', 'context', and optionally 'verdict'
            config: Merged configuration with threshold settings

        Returns:
            Dict with 'quality_score' (float 0.0-1.0) and 'score_metadata'
        """
        input_data.get("output")
        input_data.get("context", {})
        verdict: ValidationVerdict | None = input_data.get("verdict")

        # Extract configuration
        base_scores = config.get(
            "base_scores",
            {
                "green": 1.0,
                "yellow": 0.7,
                "red": 0.0,
            },
        )
        penalty_per_issue = config.get("penalty_per_issue", 0.05)
        max_penalty = config.get("max_penalty", 0.3)

        # Start with base score from verdict
        if verdict is None:
            base_score = 0.5
            status = "no_verdict"
            issues = []
        elif verdict.status == VerdictStatus.GREEN:
            base_score = base_scores.get("green", 1.0)
            status = "green"
            issues = []
        elif verdict.status == VerdictStatus.YELLOW:
            base_score = base_scores.get("yellow", 0.7)
            status = "yellow"
            # Extract issues from verdict metadata
            issues = verdict.metadata.get("issues", [verdict.feedback])
        else:  # RED
            base_score = base_scores.get("red", 0.0)
            status = "red"
            issues = verdict.metadata.get("issues", [verdict.feedback])

        # Apply penalties for issues
        num_issues = len(issues)
        total_penalty = min(num_issues * penalty_per_issue, max_penalty)
        final_score = max(0.0, base_score - total_penalty)

        return {
            "quality_score": final_score,
            "score_metadata": {
                "verdict_status": status,
                "base_score": base_score,
                "num_issues": num_issues,
                "penalty_applied": total_penalty,
                "scorer": self._name,
                "verdict_id": verdict.validation_id if verdict else None,
            },
        }

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        defaults = {
            "base_scores": {
                "green": 1.0,
                "yellow": 0.7,
                "red": 0.0,
            },
            "penalty_per_issue": 0.05,
            "max_penalty": 0.3,
        }

        if self._config_path.exists():
            with open(self._config_path) as f:
                loaded = yaml.safe_load(f) or {}
                # Deep merge for base_scores
                if "base_scores" in loaded:
                    defaults["base_scores"].update(loaded["base_scores"])
                    del loaded["base_scores"]
                defaults.update(loaded)

        return defaults

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "base_scores" in config:
            for val in config["base_scores"].values():
                if not (0.0 <= val <= 1.0):
                    return False

        if "penalty_per_issue" in config and config["penalty_per_issue"] < 0:
            return False

        return not ("max_penalty" in config and not 0.0 <= config["max_penalty"] <= 1.0)

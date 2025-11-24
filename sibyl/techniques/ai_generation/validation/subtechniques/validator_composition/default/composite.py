"""Composite validator composition implementation.

Runs multiple validators and aggregates their verdicts using standard rules:
- If any validator returns RED, overall verdict is RED
- If any validator returns YELLOW (and none RED), overall verdict is YELLOW
- If all validators return GREEN, overall verdict is GREEN
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.ai_generation.validation.subtechniques.qc_verdict.default.quality_control import (
    ValidationVerdict,
    Validator,
    VerdictStatus,
)

logger = logging.getLogger(__name__)


class CompositeValidation:
    """Composite validator composition implementation."""

    def __init__(self) -> None:
        self._name = "composite"
        self._description = "Compose multiple validators with RED > YELLOW > GREEN precedence"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ValidationVerdict:
        """Execute composite validation.

        Args:
            input_data: Dict with 'validators', 'output', and 'context' keys
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            Aggregated validation verdict
        """
        # Extract parameters
        validators: list[Validator] = input_data.get("validators", [])
        output: Any = input_data.get("output")
        context: dict[str, Any] = input_data.get("context", {})

        if not validators:
            return ValidationVerdict(
                status=VerdictStatus.GREEN,
                feedback="No validators provided",
                validator_name="composite_validator",
            )

        verdicts = []

        # Run all validators
        for validator in validators:
            try:
                verdict = await validator.validate(output, context)
                verdicts.append(verdict)
            except Exception as e:
                logger.exception("Validator %s failed: %s", validator.name, e)
                # Create RED verdict for validator failure
                verdicts.append(
                    ValidationVerdict(
                        status=VerdictStatus.RED,
                        feedback=f"Validator {validator.name} failed: {e!s}",
                        error_category="validator_error",
                        validator_name=validator.name,
                    )
                )

        # Aggregate verdicts
        has_red = any(v.status == VerdictStatus.RED for v in verdicts)
        has_yellow = any(v.status == VerdictStatus.YELLOW for v in verdicts)

        if has_red:
            status = VerdictStatus.RED
            red_verdicts = [v for v in verdicts if v.status == VerdictStatus.RED]
            feedback = f"Validation failed: {len(red_verdicts)} RED verdict(s)"
            error_category = red_verdicts[0].error_category if red_verdicts else "validation_failed"
            suggested_fixes = []
            for v in red_verdicts:
                suggested_fixes.extend(v.suggested_fixes)
        elif has_yellow:
            status = VerdictStatus.YELLOW
            yellow_verdicts = [v for v in verdicts if v.status == VerdictStatus.YELLOW]
            feedback = f"Validation passed with warnings: {len(yellow_verdicts)} YELLOW verdict(s)"
            error_category = None
            suggested_fixes = []
            for v in yellow_verdicts:
                suggested_fixes.extend(v.suggested_fixes)
        else:
            status = VerdictStatus.GREEN
            feedback = f"All {len(verdicts)} validations passed"
            error_category = None
            suggested_fixes = []

        return ValidationVerdict(
            status=status,
            feedback=feedback,
            error_category=error_category,
            suggested_fixes=suggested_fixes,
            validator_name="composite_validator",
            metadata={
                "validator_count": len(verdicts),
                "verdicts": [v.to_dict() for v in verdicts],
            },
        )

    def get_config(self) -> dict[str, Any]:
        """Load default configuration."""
        if self._config_path.exists():
            with open(self._config_path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True

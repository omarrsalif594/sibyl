"""First-pass validator composition implementation.

Runs validators in sequence and stops at first RED verdict.
Returns immediately on first failure for fast-fail behavior.
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


class FirstPassValidation:
    """First-pass validator composition implementation."""

    def __init__(self) -> None:
        self._name = "first_pass"
        self._description = "Run validators until first RED verdict (fast-fail)"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ValidationVerdict:
        """Execute first-pass validation.

        Args:
            input_data: Dict with 'validators', 'output', and 'context' keys
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            First RED verdict, or aggregated GREEN/YELLOW verdict if no failures
        """
        # Extract parameters
        validators: list[Validator] = input_data.get("validators", [])
        output: Any = input_data.get("output")
        context: dict[str, Any] = input_data.get("context", {})

        if not validators:
            return ValidationVerdict(
                status=VerdictStatus.GREEN,
                feedback="No validators provided",
                validator_name="first_pass_validator",
            )

        verdicts = []
        has_yellow = False

        # Run validators until first RED
        for validator in validators:
            try:
                verdict = await validator.validate(output, context)

                # Immediately return on first RED verdict
                if verdict.status == VerdictStatus.RED:
                    logger.info("First-pass validator %s returned RED, stopping", validator.name)
                    return verdict

                # Track YELLOW verdicts
                if verdict.status == VerdictStatus.YELLOW:
                    has_yellow = True

                verdicts.append(verdict)

            except Exception as e:
                logger.exception("Validator %s failed: %s", validator.name, e)
                # Return RED verdict immediately on validator failure
                return ValidationVerdict(
                    status=VerdictStatus.RED,
                    feedback=f"Validator {validator.name} failed: {e!s}",
                    error_category="validator_error",
                    validator_name=validator.name,
                )

        # All validators passed (no RED verdicts)
        if has_yellow:
            yellow_verdicts = [v for v in verdicts if v.status == VerdictStatus.YELLOW]
            suggested_fixes = []
            for v in yellow_verdicts:
                suggested_fixes.extend(v.suggested_fixes)

            return ValidationVerdict(
                status=VerdictStatus.YELLOW,
                feedback=f"Validation passed with {len(yellow_verdicts)} warning(s)",
                suggested_fixes=suggested_fixes,
                validator_name="first_pass_validator",
                metadata={
                    "validator_count": len(verdicts),
                    "yellow_count": len(yellow_verdicts),
                },
            )
        return ValidationVerdict(
            status=VerdictStatus.GREEN,
            feedback=f"All {len(verdicts)} validations passed",
            validator_name="first_pass_validator",
            metadata={"validator_count": len(verdicts)},
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

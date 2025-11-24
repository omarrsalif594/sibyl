"""Single validator composition implementation.

Runs a single validator and returns its verdict directly.
Useful for simple validation scenarios or testing.
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


class SingleValidation:
    """Single validator composition implementation."""

    def __init__(self) -> None:
        self._name = "single"
        self._description = "Run a single validator and return its verdict"
        self._config_path = Path(__file__).parent.parent / "config.yaml"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, input_data: Any, config: dict[str, Any]) -> ValidationVerdict:
        """Execute single validator validation.

        Args:
            input_data: Dict with 'validator' (or 'validators' list), 'output', and 'context' keys
            config: Merged configuration (global + technique + subtechnique)

        Returns:
            Validation verdict from the single validator
        """
        # Extract parameters
        validator: Validator = input_data.get("validator")
        validators: list = input_data.get("validators", [])
        output: Any = input_data.get("output")
        context: dict[str, Any] = input_data.get("context", {})

        # Use first validator from list if no explicit validator provided
        if not validator and validators:
            validator = validators[0]

        if not validator:
            return ValidationVerdict(
                status=VerdictStatus.GREEN,
                feedback="No validator provided",
                validator_name="single_validator",
            )

        try:
            return await validator.validate(output, context)
        except Exception as e:
            logger.exception("Validator %s failed: %s", validator.name, e)
            return ValidationVerdict(
                status=VerdictStatus.RED,
                feedback=f"Validator {validator.name} failed: {e!s}",
                error_category="validator_error",
                validator_name=validator.name,
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

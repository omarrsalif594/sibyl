"""Base Validator abstraction for Sibyl templates.

This module provides the foundation for template-specific validators.
Templates extend SibylValidator to create domain-specific validation logic.

Example:
    ```python
    from sibyl.core.contracts.validator_base import SibylValidator, ValidationResult, VerdictStatus

    class PythonSyntaxValidator(SibylValidator):
        name = "syntax_check"
        description = "Validate Python syntax"

        async def validate(self, resource: dict) -> ValidationResult:
            code = resource.get("content", "")

            try:
                compile(code, "<string>", "exec")
                return ValidationResult(
                    status=VerdictStatus.GREEN,
                    feedback="Syntax is valid",
                    validator_name=self.name
                )
            except SyntaxError as e:
                return ValidationResult(
                    status=VerdictStatus.RED,
                    feedback=f"Syntax error: {e}",
                    error_category="syntax_error",
                    suggested_fixes=[f"Fix syntax at line {e.lineno}"],
                    validator_name=self.name
                )
    ```
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class VerdictStatus(str, Enum):
    """Verdict status for validation.

    GREEN: Validation passed, output is safe to use
    YELLOW: Validation passed with warnings, output may have non-critical issues
    RED: Validation failed, output should not be used
    """

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


@dataclass(frozen=True)
class ValidationResult:
    """Result of validator execution.

    Attributes:
        status: Verdict status (GREEN/YELLOW/RED)
        feedback: Human-readable feedback message
        error_category: Optional error category
        suggested_fixes: List of suggested fixes
        validator_name: Name of the validator
        validation_id: Unique identifier
        timestamp: When validation was performed
        metadata: Additional context
    """

    status: VerdictStatus
    feedback: str
    error_category: str | None = None
    suggested_fixes: list[str] = field(default_factory=list)
    validator_name: str = ""
    validation_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class SibylValidator(ABC):
    """Base class for all Sibyl validators.

    Templates inherit from this class to create domain-specific validators.
    Validators are used by the Quality Control framework to validate resources.

    Attributes:
        name: Unique validator identifier
        description: Human-readable description
        enabled: Whether validator is active
        severity: Importance level ("critical", "warning", "info")
        order: Execution order (lower runs first)
    """

    # Validator metadata (subclasses must set these)
    name: str = ""
    description: str = ""
    enabled: bool = True
    severity: str = "warning"  # critical, warning, info
    order: int = 100  # Execution order

    @abstractmethod
    async def validate(self, resource: dict[str, Any]) -> ValidationResult:
        """Validate a resource.

        Args:
            resource: Resource to validate (structure varies by template)

        Returns:
            ValidationResult with status and feedback
        """
        ...

    async def can_validate(self, resource: dict[str, Any]) -> bool:
        """Check if this validator can validate the resource.

        Allows validators to skip resources they don't handle.

        Args:
            resource: Resource to check

        Returns:
            True if validator can handle this resource
        """
        return True

    def is_critical(self) -> bool:
        """Check if this is a critical validator.

        Critical validators produce RED verdicts that block execution.

        Returns:
            True if severity is "critical"
        """
        return self.severity == "critical"


class ValidatorRegistry:
    """Registry for managing validators.

    Templates register their validators here.
    """

    def __init__(self) -> None:
        self._validators: dict[str, SibylValidator] = {}

    def register(self, validator: SibylValidator) -> None:
        """Register a validator.

        Args:
            validator: Validator instance to register
        """
        self._validators[validator.name] = validator

    def get(self, name: str) -> SibylValidator | None:
        """Get validator by name.

        Args:
            name: Validator name

        Returns:
            Validator instance or None
        """
        return self._validators.get(name)

    def get_all(self, enabled_only: bool = True) -> list[SibylValidator]:
        """Get all validators.

        Args:
            enabled_only: If True, return only enabled validators

        Returns:
            List of validators sorted by order
        """
        validators = self._validators.values()

        if enabled_only:
            validators = [v for v in validators if v.enabled]

        return sorted(validators, key=lambda v: v.order)

    def clear(self) -> None:
        """Clear all registered validators."""
        self._validators.clear()

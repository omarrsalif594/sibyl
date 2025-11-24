"""
Validation protocol interfaces.

This module contains the protocol abstractions for the validation system.
These are the interfaces that both framework and techniques depend on.

Layering:
    core/protocols/validation.py (this file) - Protocol definitions
    ├─> framework/validation/* - Validation framework
    └─> techniques/*/validation/* - Domain-specific validators

Key types:
- VerdictStatus: Validation verdict enum (GREEN/YELLOW/RED)
- IValidator: Base validator interface
"""

from enum import Enum
from typing import Any, Protocol, runtime_checkable


class VerdictStatus(str, Enum):
    """Verdict status for validation.

    This is the canonical definition of verdict status used throughout Sibyl.

    GREEN: Validation passed, output is safe to use
    YELLOW: Validation passed with warnings, output may have non-critical issues
    RED: Validation failed, output should not be used
    """

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


@runtime_checkable
class IValidator(Protocol):
    """Protocol for validator interface.

    Validators inspect outputs and return verdicts about their quality.
    """

    @property
    def name(self) -> str:
        """Validator name for identification."""
        ...

    async def validate(self, output: Any, context: dict[str, Any]) -> Any:
        """Validate output and return a verdict.

        Args:
            output: The output to validate
            context: Additional context for validation

        Returns:
            Validation verdict
        """
        ...


__all__ = [
    "IValidator",
    "VerdictStatus",
]

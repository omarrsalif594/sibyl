"""Concrete validator implementations.

This module provides validator implementations for quality control:
- SyntaxValidator: Validates syntax correctness
- AntiPatternValidator: Checks for code anti-patterns and quality issues
- TypeCheckValidator: Validates type consistency and usage
"""

import logging
import re
from typing import Any

from sibyl.techniques.ai_generation.validation.subtechniques.qc_verdict.default.quality_control import (
    ValidationVerdict,
    VerdictStatus,
)

logger = logging.getLogger(__name__)


class SyntaxValidator:
    """Validates syntax using basic checks.

    This validator performs basic syntax validation using built-in checks.
    """

    def __init__(self) -> None:
        """Initialize syntax validator."""
        self._name = "syntax_validator"

    @property
    def name(self) -> str:
        return self._name

    async def validate(self, output: Any, context: dict[str, Any]) -> ValidationVerdict:
        """Validate syntax.

        Args:
            output: Output to validate (string content)
            context: Context with tool_name, model_name, etc.

        Returns:
            ValidationVerdict with syntax validation result
        """
        if not isinstance(output, str):
            return ValidationVerdict(
                status=VerdictStatus.RED,
                feedback=f"Expected string output, got {type(output).__name__}",
                error_category="invalid_output_type",
                validator_name=self.name,
            )

        content = output.strip()

        # Basic syntax checks
        basic_checks = self._basic_syntax_checks(content)
        if basic_checks:
            return basic_checks

        # All basic checks passed
        return ValidationVerdict(
            status=VerdictStatus.GREEN,
            feedback="Syntax validation passed",
            validator_name=self.name,
            metadata={"content_length": len(content)},
        )

    def _basic_syntax_checks(self, content: str) -> ValidationVerdict | None:
        """Perform basic syntax checks.

        Args:
            content: Content to check

        Returns:
            ValidationVerdict if error found, None if all checks pass
        """
        # Check for empty content
        if not content:
            return ValidationVerdict(
                status=VerdictStatus.RED,
                feedback="Empty output",
                error_category="syntax_error",
                suggested_fixes=["Check for template rendering errors"],
                validator_name=self.name,
            )

        # Check for unclosed Jinja templates
        if re.search(r"\{\{(?![^}]*\}\})", content) or re.search(r"\{%(?![^}]*%\})", content):
            return ValidationVerdict(
                status=VerdictStatus.RED,
                feedback="Unclosed Jinja template found",
                error_category="compilation_error",
                suggested_fixes=[
                    "Check for missing closing braces in Jinja templates",
                    "Ensure compilation completed successfully",
                ],
                validator_name=self.name,
            )

        # Check for unbalanced parentheses
        if content.count("(") != content.count(")"):
            return ValidationVerdict(
                status=VerdictStatus.RED,
                feedback=f"Unbalanced parentheses: {content.count('(')} opening, {content.count(')')} closing",
                error_category="syntax_error",
                suggested_fixes=["Check for missing or extra parentheses"],
                validator_name=self.name,
            )

        return None


class AntiPatternValidator:
    """Validates for anti-patterns and code quality issues.

    Checks for:
    - Overly complex nested structures
    - Wildcard usage in production code (e.g., SELECT *, import *)
    - Potentially dangerous operations without safeguards
    """

    def __init__(self, strict_mode: bool = False) -> None:
        """Initialize anti-pattern validator.

        Args:
            strict_mode: If True, return RED for anti-patterns; if False, return YELLOW
        """
        self.strict_mode = strict_mode
        self._name = "anti_pattern_validator"

    @property
    def name(self) -> str:
        return self._name

    async def validate(self, output: Any, context: dict[str, Any]) -> ValidationVerdict:
        """Validate for anti-patterns.

        Args:
            output: Output to validate
            context: Context with tool_name, model_name, etc.

        Returns:
            ValidationVerdict with anti-pattern check result
        """
        if not isinstance(output, str):
            return ValidationVerdict(
                status=VerdictStatus.GREEN,
                feedback="Skipping anti-pattern check (non-string output)",
                validator_name=self.name,
            )

        content = output.strip()
        content_upper = content.upper()
        issues = []
        fixes = []

        # Check for wildcard patterns in query languages (SQL, etc.)
        if re.search(r"\bSELECT\s+\*\s+FROM\b", content_upper):
            issues.append("Wildcard selector found (SELECT *) - discouraged in production")
            fixes.append("Explicitly list fields/columns instead of using wildcards")

        # Check for potentially dangerous operations without conditions (SQL, etc.)
        if re.search(r"\bDELETE\s+FROM\s+\w+(?!\s+WHERE)\b", content_upper):
            issues.append("Bulk delete operation without condition clause (dangerous)")
            fixes.append("Add condition clause to delete operation")

        if re.search(r"\bUPDATE\s+\w+\s+SET\s+(?![^;]*WHERE)\b", content_upper):
            issues.append("Bulk update operation without condition clause (dangerous)")
            fixes.append("Add condition clause to update operation")

        # Check for excessive nesting depth (generalized for any nested structures)
        nesting_depth = self._count_nesting_depth(content)
        if nesting_depth > 3:
            issues.append(f"Deep nesting detected (depth={nesting_depth})")
            fixes.append("Consider refactoring to reduce complexity and improve readability")

        if issues:
            status = VerdictStatus.RED if self.strict_mode else VerdictStatus.YELLOW
            feedback = f"Anti-patterns found: {', '.join(issues)}"
            return ValidationVerdict(
                status=status,
                feedback=feedback,
                error_category="anti_pattern",
                suggested_fixes=fixes,
                validator_name=self.name,
                metadata={"issues": issues, "strict_mode": self.strict_mode},
            )

        return ValidationVerdict(
            status=VerdictStatus.GREEN,
            feedback="No anti-patterns detected",
            validator_name=self.name,
        )

    def _count_nesting_depth(self, content: str) -> int:
        """Count maximum nesting depth of any nested structures.

        Analyzes parentheses, brackets, and braces to detect deep nesting
        in any type of code (SQL, Python, JavaScript, etc.).

        Args:
            content: Content to analyze

        Returns:
            Maximum depth of nested structures
        """
        max_depth = 0
        current_depth = 0
        opening_chars = {"(", "[", "{"}
        closing_chars = {")", "]", "}"}

        for char in content:
            if char in opening_chars:
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char in closing_chars:
                current_depth = max(0, current_depth - 1)

        return max_depth


class TypeCheckValidator:
    """Validates type consistency and usage patterns.

    Checks for:
    - Mixed usage of similar type functions (indicates potential type mismatches)
    - Inconsistent type handling patterns
    """

    def __init__(self) -> None:
        """Initialize type check validator."""
        self._name = "type_check_validator"

    @property
    def name(self) -> str:
        return self._name

    async def validate(self, output: Any, context: dict[str, Any]) -> ValidationVerdict:
        """Validate type function usage.

        Args:
            output: Output to validate
            context: Context with tool_name, model_name, etc.

        Returns:
            ValidationVerdict with type check result
        """
        if not isinstance(output, str):
            return ValidationVerdict(
                status=VerdictStatus.GREEN,
                feedback="Skipping type check (non-string output)",
                validator_name=self.name,
            )

        content = output.strip()
        issues = []
        fixes = []

        # Check for mixed temporal function types (generic pattern)
        # This checks for inconsistent usage of similar function families
        temporal_patterns = [
            (r"\bDATETIME_\w+\s*\(", "datetime"),
            (r"\bTIMESTAMP_\w+\s*\(", "timestamp"),
            (r"\bDATE_\w+\s*\(", "date"),
        ]

        found_types = []
        for pattern, type_name in temporal_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                found_types.append(type_name)

        if len(found_types) > 1:
            issues.append(f"Mixed temporal function types detected: {', '.join(found_types)}")
            fixes.append(
                "Use consistent type handling throughout - verify data types and use appropriate functions"
            )

        # Check for type conversion with mismatched operations
        if re.search(
            r'\b(TIMESTAMP|DATETIME)_\w+\s*\(\s*(DATE|DATETIME|TIMESTAMP)\s*\([\'"]?\d{4}-\d{2}-\d{2}[\'"]?\)',
            content,
            re.IGNORECASE,
        ):
            issues.append(
                "Type conversion followed by type-specific operation - potential mismatch"
            )
            fixes.append("Ensure operation type matches the actual data type after conversion")

        if issues:
            return ValidationVerdict(
                status=VerdictStatus.YELLOW,
                feedback=f"Type usage warnings: {', '.join(issues)}",
                error_category="type_warning",
                suggested_fixes=fixes,
                validator_name=self.name,
                metadata={"issues": issues},
            )

        return ValidationVerdict(
            status=VerdictStatus.GREEN,
            feedback="No type mismatch issues detected",
            validator_name=self.name,
        )

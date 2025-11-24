"""Quality control specific errors."""

from typing import Any


class QualityControlError(Exception):
    """Base exception for quality control errors."""


class ValidationError(QualityControlError):
    """Raised when validation fails and cannot be retried."""


class ValidationTimeoutError(QualityControlError):
    """Raised when validation times out."""


class ValidatorNotFoundError(QualityControlError):
    """Raised when a requested validator is not found."""


class RetriesExhaustedError(QualityControlError):
    """Raised when all retry attempts are exhausted with RED verdicts."""

    def __init__(self, message: str, verdicts: list, retry_metadata: dict) -> None:
        super().__init__(message)
        self.verdicts = verdicts
        self.retry_metadata = retry_metadata


class StructuredCompilationError(QualityControlError):
    """Structured compilation error with classification and suggested fixes.

    This error type includes automatic error classification and context-specific
    suggested fixes. It's designed to provide rich, actionable information to users.

    Attributes:
        message: Human-readable error message
        category: Error category (e.g., "syntax_error", "macro_missing", "type_mismatch")
        suggested_fixes: List of suggested fixes for this error
        error_code: Optional error code (e.g., warehouse/compiler error code)
        model_name: Optional model name where error occurred
        line_number: Optional line number in SQL
        column_number: Optional column number in SQL
        matched_keywords: Keywords that matched during classification
        confidence: Classification confidence (0.0-1.0)
        context: Additional context dictionary
    """

    def __init__(
        self,
        message: str,
        category: str,
        suggested_fixes: list[str] | None = None,
        error_code: str | None = None,
        model_name: str | None = None,
        line_number: int | None = None,
        column_number: int | None = None,
        matched_keywords: list[str] | None = None,
        confidence: float = 0.0,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize structured compilation error.

        Args:
            message: Error message
            category: Error category
            suggested_fixes: List of suggested fixes
            error_code: Optional error code
            model_name: Optional model name
            line_number: Optional line number
            column_number: Optional column number
            matched_keywords: Keywords that matched during classification
            confidence: Classification confidence (0.0-1.0)
            context: Additional context
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.suggested_fixes = suggested_fixes or []
        self.error_code = error_code
        self.model_name = model_name
        self.line_number = line_number
        self.column_number = column_number
        self.matched_keywords = matched_keywords or []
        self.confidence = confidence
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for serialization.

        Returns:
            Dictionary representation of error
        """
        return {
            "message": self.message,
            "category": self.category,
            "suggested_fixes": self.suggested_fixes,
            "error_code": self.error_code,
            "model_name": self.model_name,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "matched_keywords": self.matched_keywords,
            "confidence": self.confidence,
            "context": self.context,
        }

    def format_for_user(self) -> str:
        """Format error for user display.

        Returns:
            Human-readable formatted error message
        """
        lines = []

        # Header
        lines.append(f"❌ {self.category.replace('_', ' ').title()}")
        lines.append("")

        # Model context
        if self.model_name:
            lines.append(f"Model: {self.model_name}")

        # Location
        if self.line_number:
            location = f"Line {self.line_number}"
            if self.column_number:
                location += f", Column {self.column_number}"
            lines.append(f"Location: {location}")

        if self.model_name or self.line_number:
            lines.append("")

        # Error message
        lines.append("Error:")
        lines.append(f"  {self.message}")
        lines.append("")

        # Suggested fixes
        if self.suggested_fixes:
            lines.append("Suggested Fixes:")
            for i, fix in enumerate(self.suggested_fixes, 1):
                lines.append(f"  {i}. {fix}")
            lines.append("")

        # Classification confidence (if low)
        if self.confidence < 0.5:
            lines.append(
                f"Note: Classification confidence is low ({self.confidence:.0%}). "
                "This error may belong to a different category."
            )

        return "\n".join(lines)

    def __str__(self) -> str:
        """String representation of error."""
        return self.format_for_user()


def create_structured_error_from_classification(
    classification: Any,  # ErrorClassification type
    model_name: str | None = None,
    error_code: str | None = None,
) -> StructuredCompilationError:
    """Create StructuredCompilationError from ErrorClassification.

    Args:
        classification: ErrorClassification result
        model_name: Optional model name
        error_code: Optional error code

    Returns:
        StructuredCompilationError instance
    """
    return StructuredCompilationError(
        message=classification.error_message,
        category=classification.category,
        suggested_fixes=classification.suggested_fixes,
        error_code=error_code,
        model_name=model_name,
        matched_keywords=classification.matched_keywords,
        confidence=classification.confidence,
    )

"""
Input Validation Implementation

Provides input sanitization and validation to prevent injection attacks.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Patterns for validation (from security/validators/input.py)
MODEL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
SQL_KEYWORDS_PATTERN = re.compile(
    r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|EXEC|EXECUTE|SCRIPT|UNION|SELECT)\b",
    re.IGNORECASE,
)
PATH_TRAVERSAL_PATTERN = re.compile(r"\.\.|/\.\.|\\\.\.|\.\./|\.\.\\")


def execute_input_validation(text: str, max_length: int, **kwargs) -> dict[str, Any]:
    """
    Execute input validation and sanitization.

    Args:
        text: Input text to validate
        max_length: Maximum allowed length in characters
        **kwargs: Additional parameters

    Returns:
        Result dictionary with validation status
    """
    validation_type = kwargs.get("validation_type", "general")
    allow_newlines = kwargs.get("allow_newlines", True)
    strip = kwargs.get("strip", True)

    # Track validation issues
    issues = []

    # Check length
    if len(text) > max_length:
        issues.append(
            {
                "type": "length_exceeded",
                "message": f"Input too long: {len(text)} chars (max: {max_length})",
                "severity": "error",
            }
        )
        return {"valid": False, "issues": issues, "sanitized": None}

    # Check for path traversal
    if PATH_TRAVERSAL_PATTERN.search(text):
        issues.append(
            {
                "type": "path_traversal",
                "message": "Path traversal pattern detected",
                "severity": "error",
            }
        )
        logger.warning("Path traversal attempt detected in input: %s", text[:100])

    # Check for SQL keywords (potential injection)
    if SQL_KEYWORDS_PATTERN.search(text):
        issues.append(
            {"type": "sql_keyword", "message": "SQL keyword detected", "severity": "warning"}
        )
        logger.warning("SQL keyword detected in input: %s", text[:100])

    # Sanitize the input
    if allow_newlines:
        # Keep \n, \r, \t
        sanitized = "".join(
            char for char in text if char.isprintable() or char in ("\n", "\r", "\t")
        )
    else:
        # Remove all control characters including newlines
        sanitized = "".join(char for char in text if char.isprintable())

    # Strip whitespace if requested
    if strip:
        sanitized = sanitized.strip()

    # Validate specific types
    if validation_type == "model_name" and not MODEL_NAME_PATTERN.match(text):
        issues.append(
            {
                "type": "invalid_model_name",
                "message": "Invalid model name: only alphanumeric, underscore, and dash allowed",
                "severity": "error",
            }
        )

    # Determine if valid (no error-level issues)
    valid = not any(issue["severity"] == "error" for issue in issues)

    return {
        "valid": valid,
        "sanitized": sanitized if valid else None,
        "issues": issues,
        "original_length": len(text),
        "sanitized_length": len(sanitized) if valid else 0,
    }


def validate_model_name(name: str, max_length: int = 200) -> dict[str, Any]:
    """
    Validate model name specifically.

    Args:
        name: Model name to validate
        max_length: Maximum allowed length

    Returns:
        Validation result
    """
    return execute_input_validation(
        text=name,
        max_length=max_length,
        validation_type="model_name",
        allow_newlines=False,
        strip=True,
    )

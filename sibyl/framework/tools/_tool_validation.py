"""
Internal module for tool input validation and schema handling.

This module is not part of the public API - do not import directly.
Use sibyl.framework.tools.tool_base instead.
"""

from typing import Any


async def validate_input_schema(
    schema: dict[str, Any], kwargs: dict[str, Any]
) -> tuple[bool, str | None]:
    """
    Validate inputs against a JSON schema.

    Args:
        schema: JSON Schema definition for validation
        kwargs: Input parameters to validate

    Returns:
        (is_valid, error_message) - error_message is None if valid
    """
    # Check required fields
    required = schema.get("required", [])
    provided = set(kwargs.keys())
    missing = set(required) - provided

    if missing:
        # Use "field" for single missing item, "fields" for multiple
        field_word = "field" if len(missing) == 1 else "fields"
        missing_str = next(iter(missing)) if len(missing) == 1 else str(missing)
        return False, f"Missing required {field_word}: {missing_str}"

    # Check types (basic validation)
    properties = schema.get("properties", {})
    for field, value in kwargs.items():
        if field not in properties:
            # Allow extra fields unless additionalProperties is false
            if not schema.get("additionalProperties", True):
                return False, f"Unknown field: {field}"
            continue

        # Type checking (simplified)
        expected_type = properties[field].get("type")
        if expected_type:
            actual_type = type(value).__name__
            # Map Python types to JSON schema types
            type_mapping = {
                "str": "string",
                "int": "integer",
                "float": "number",
                "bool": "boolean",
                "list": "array",
                "dict": "object",
                "NoneType": "null",
            }
            json_type = type_mapping.get(actual_type)
            if expected_type not in (json_type, "number"):
                # Allow int for number type
                if not (expected_type == "number" and actual_type == "int"):
                    return (
                        False,
                        f"Field '{field}' has wrong type: expected {expected_type}, got {actual_type}",
                    )

    return True, None


def get_default_metadata_from_class(tool_instance: Any, timeout: int = 120) -> dict[str, Any]:
    """
    Build default tool metadata from class attributes (domain style).

    Args:
        tool_instance: Tool instance with name/description/input_schema attributes
        timeout: Default timeout in seconds

    Returns:
        Dictionary with metadata fields
    """
    name = getattr(tool_instance, "name", "")
    if not name:
        name = tool_instance.__class__.__name__.replace("Tool", "").lower()

    description = getattr(tool_instance, "description", "")
    if not description:
        description = f"{tool_instance.__class__.__name__} tool"

    input_schema = getattr(tool_instance, "input_schema", {})
    if not input_schema:
        input_schema = {"type": "object"}

    return {
        "name": name,
        "description": description,
        "input_schema": input_schema,
        "version": "1.0.0",
        "category": "general",
        "max_execution_time_ms": timeout * 1000,
    }

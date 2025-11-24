"""Error taxonomy for Sibyl pipelines (C2.1).

This module defines a comprehensive error taxonomy with stable error codes,
human-readable messages, and actionable hints for developers.

This module contains only the abstract taxonomy and error types. For runtime
exception mapping, use sibyl.runtime.pipeline.error_mapping.

Example:
    from sibyl.core.pipeline.error_taxonomy import create_error

    # Create a validation error
    error = create_error(
        "SIBYL_PIPELINE_VALIDATION_ERROR",
        "Missing required field 'steps'",
        context={"pipeline": "my_pipeline", "field": "steps"}
    )

    # Access error properties
    print(error.code)  # SIBYL_PIPELINE_VALIDATION_ERROR
    print(error.message)  # Missing required field 'steps'
    print(error.hint)  # Add a 'steps:' list to your pipeline configuration

    # For mapping runtime exceptions, use:
    from sibyl.runtime.pipeline.error_mapping import map_exception_to_error
"""

from dataclasses import dataclass
from typing import Any


# Error code definitions (C2.1)
class ErrorCode:
    """Stable error codes for Sibyl pipeline errors."""

    # Configuration errors - issues with workspace/pipeline configuration
    SIBYL_CONFIG_ERROR = "SIBYL_CONFIG_ERROR"

    # Pipeline validation errors - invalid pipeline structure
    SIBYL_PIPELINE_VALIDATION_ERROR = "SIBYL_PIPELINE_VALIDATION_ERROR"

    # Runtime errors - unhandled exceptions during execution
    SIBYL_RUNTIME_ERROR = "SIBYL_RUNTIME_ERROR"

    # MCP errors - MCP provider/tool failures
    SIBYL_MCP_ERROR = "SIBYL_MCP_ERROR"

    # Control flow errors - misconfigured control flow (loops, parallel, try/catch)
    SIBYL_CONTROL_FLOW_ERROR = "SIBYL_CONTROL_FLOW_ERROR"

    # Budget errors - budget limit exceeded
    SIBYL_BUDGET_ERROR = "SIBYL_BUDGET_ERROR"

    # Timeout errors - operation timed out
    SIBYL_TIMEOUT_ERROR = "SIBYL_TIMEOUT_ERROR"

    # Condition evaluation errors - failed to evaluate condition
    SIBYL_CONDITION_ERROR = "SIBYL_CONDITION_ERROR"

    # Technique errors - technique loading/execution failures
    SIBYL_TECHNIQUE_ERROR = "SIBYL_TECHNIQUE_ERROR"


# Error hints mapping (C2.2)
ERROR_HINTS = {
    ErrorCode.SIBYL_CONFIG_ERROR: (
        "Check your workspace configuration file. Ensure all required fields are present and valid."
    ),
    ErrorCode.SIBYL_PIPELINE_VALIDATION_ERROR: (
        "Review your pipeline configuration. Ensure steps are properly defined with valid syntax."
    ),
    ErrorCode.SIBYL_RUNTIME_ERROR: (
        "An unexpected error occurred during pipeline execution. Check the error details for more information."
    ),
    ErrorCode.SIBYL_MCP_ERROR: (
        "MCP provider call failed. Verify the provider is running and accessible, and check authentication."
    ),
    ErrorCode.SIBYL_CONTROL_FLOW_ERROR: (
        "Control flow configuration is invalid. Review loop/parallel/try-catch syntax in your pipeline."
    ),
    ErrorCode.SIBYL_BUDGET_ERROR: (
        "Budget limit exceeded. Consider increasing limits or optimizing pipeline steps."
    ),
    ErrorCode.SIBYL_TIMEOUT_ERROR: (
        "Operation timed out. Increase timeout_s or optimize the pipeline step."
    ),
    ErrorCode.SIBYL_CONDITION_ERROR: (
        "Failed to evaluate condition. Check template syntax and available context variables."
    ),
    ErrorCode.SIBYL_TECHNIQUE_ERROR: (
        "Technique not found or execution failed. Verify technique name and shop configuration."
    ),
}


@dataclass
class SibylError:
    """Structured error with code, message, hint, and context (C2.1, C2.2).

    Attributes:
        code: Stable error code (SIBYL_*)
        message: Human-readable error message
        hint: Actionable hint for resolving the error
        context: Additional error context (pipeline name, step name, etc.)
        details: Detailed error information
    """

    code: str
    message: str
    hint: str
    context: dict[str, Any]
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for API responses.

        Returns:
            Dictionary with error information
        """
        result = {
            "error_code": self.code,
            "message": self.message,
            "hint": self.hint,
            "context": self.context,
        }

        if self.details:
            result["details"] = self.details

        return result

    def __str__(self) -> str:
        """Format error as human-readable string.

        Returns:
            Formatted error message
        """
        parts = [
            f"[{self.code}] {self.message}",
            f"Hint: {self.hint}",
        ]

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")

        return "\n".join(parts)


def create_error(
    code: str,
    message: str,
    context: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
    hint: str | None = None,
) -> SibylError:
    """Create a structured error with appropriate hint.

    Args:
        code: Error code (use ErrorCode constants)
        message: Error message
        context: Error context (pipeline name, step name, etc.)
        details: Additional error details
        hint: Optional custom hint (overrides default)

    Returns:
        Structured SibylError

    Example:
        error = create_error(
            ErrorCode.SIBYL_MCP_ERROR,
            "Failed to connect to MCP provider 'my_provider'",
            context={"provider": "my_provider", "transport": "http"},
            details={"url": "http://localhost:8000", "error": "Connection refused"}
        )
    """
    # Use provided hint or lookup default
    error_hint = hint or ERROR_HINTS.get(
        code, "Check the error message and context for more information."
    )

    return SibylError(
        code=code,
        message=message,
        hint=error_hint,
        context=context or {},
        details=details,
    )


def create_config_error(message: str, context: dict[str, Any] | None = None) -> SibylError:
    """Create a configuration error.

    Args:
        message: Error message
        context: Error context

    Returns:
        SibylError with SIBYL_CONFIG_ERROR code
    """
    return create_error(ErrorCode.SIBYL_CONFIG_ERROR, message, context)


def create_validation_error(message: str, context: dict[str, Any] | None = None) -> SibylError:
    """Create a pipeline validation error.

    Args:
        message: Error message
        context: Error context

    Returns:
        SibylError with SIBYL_PIPELINE_VALIDATION_ERROR code
    """
    return create_error(ErrorCode.SIBYL_PIPELINE_VALIDATION_ERROR, message, context)


def create_runtime_error(message: str, context: dict[str, Any] | None = None) -> SibylError:
    """Create a runtime error.

    Args:
        message: Error message
        context: Error context

    Returns:
        SibylError with SIBYL_RUNTIME_ERROR code
    """
    return create_error(ErrorCode.SIBYL_RUNTIME_ERROR, message, context)


def create_mcp_error(message: str, context: dict[str, Any] | None = None) -> SibylError:
    """Create an MCP error.

    Args:
        message: Error message
        context: Error context

    Returns:
        SibylError with SIBYL_MCP_ERROR code
    """
    return create_error(ErrorCode.SIBYL_MCP_ERROR, message, context)


def create_control_flow_error(message: str, context: dict[str, Any] | None = None) -> SibylError:
    """Create a control flow error.

    Args:
        message: Error message
        context: Error context

    Returns:
        SibylError with SIBYL_CONTROL_FLOW_ERROR code
    """
    return create_error(ErrorCode.SIBYL_CONTROL_FLOW_ERROR, message, context)


def create_budget_error(message: str, context: dict[str, Any] | None = None) -> SibylError:
    """Create a budget error.

    Args:
        message: Error message
        context: Error context

    Returns:
        SibylError with SIBYL_BUDGET_ERROR code
    """
    return create_error(ErrorCode.SIBYL_BUDGET_ERROR, message, context)


def create_timeout_error(message: str, context: dict[str, Any] | None = None) -> SibylError:
    """Create a timeout error.

    Args:
        message: Error message
        context: Error context

    Returns:
        SibylError with SIBYL_TIMEOUT_ERROR code
    """
    return create_error(ErrorCode.SIBYL_TIMEOUT_ERROR, message, context)


def create_condition_error(message: str, context: dict[str, Any] | None = None) -> SibylError:
    """Create a condition evaluation error.

    Args:
        message: Error message
        context: Error context

    Returns:
        SibylError with SIBYL_CONDITION_ERROR code
    """
    return create_error(ErrorCode.SIBYL_CONDITION_ERROR, message, context)


def create_technique_error(message: str, context: dict[str, Any] | None = None) -> SibylError:
    """Create a technique error.

    Args:
        message: Error message
        context: Error context

    Returns:
        SibylError with SIBYL_TECHNIQUE_ERROR code
    """
    return create_error(ErrorCode.SIBYL_TECHNIQUE_ERROR, message, context)

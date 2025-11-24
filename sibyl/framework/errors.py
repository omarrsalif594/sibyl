"""
Error taxonomy for standardized error handling across MCP server.

All tools and services should raise these typed exceptions, which are then
mapped to protocol-level errors by transport layers.

Key features:
- Error code enums (avoid typos)
- Severity levels (fatal, transient, user_error)
- Pydantic models for structured error details
- Boundary translation functions
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Error Codes and Severity
# ============================================================================


class ErrorCode(str, Enum):
    """Enumeration of all error codes in the system."""

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TOOL_INPUT_ERROR = "TOOL_INPUT_ERROR"
    TOOL_OUTPUT_ERROR = "TOOL_OUTPUT_ERROR"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"

    # Execution errors
    EXECUTION_ERROR = "EXECUTION_ERROR"
    TIMEOUT = "TIMEOUT"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"

    # Rate limiting
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"

    # Internal errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    PROVIDER_ERROR = "PROVIDER_ERROR"


class ErrorSeverity(str, Enum):
    """Error severity for automatic retry and alerting."""

    FATAL = "fatal"  # Unrecoverable, requires intervention
    TRANSIENT = "transient"  # Temporary, retryable
    USER_ERROR = "user_error"  # User mistake, not retryable


# ============================================================================
# Pydantic Error Models
# ============================================================================


class ErrorDetails(BaseModel):
    """Structured error details for serialization."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: ErrorCode = Field(..., description="Error code enum")
    message: str = Field(..., description="Human-readable error message")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    retry_after: int | None = Field(
        default=None, description="Retry after N seconds (for rate limits)"
    )
    severity: ErrorSeverity = Field(default=ErrorSeverity.FATAL, description="Error severity")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()


# ============================================================================
# Base Exception Class
# ============================================================================


class MCPError(Exception):
    """Base class for all MCP server errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode,
        details: dict[str, Any] | None = None,
        severity: ErrorSeverity = ErrorSeverity.FATAL,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.severity = severity

    def to_details(self) -> ErrorDetails:
        """Convert to structured ErrorDetails."""
        return ErrorDetails(
            code=self.code, message=self.message, context=self.details, severity=self.severity
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "error": self.code.value,
            "message": self.message,
            "details": self.details,
            "severity": self.severity.value,
        }


# ============================================================================
# Validation Errors
# ============================================================================


class ValidationError(MCPError):
    """Input validation failed."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        expected: str | None = None,
        received: Any | None = None,
    ) -> None:
        details = {}
        if field:
            details["field"] = field
        if expected:
            details["expected"] = expected
        if received is not None:
            details["received"] = str(received)
        super().__init__(
            message, ErrorCode.VALIDATION_ERROR, details, severity=ErrorSeverity.USER_ERROR
        )


class ToolInputError(ValidationError):
    """Tool input schema validation failed."""

    def __init__(self, message: str, tool_name: str, path: list[str] | None = None) -> None:
        super().__init__(message, field=".".join(path) if path else None)
        self.code = ErrorCode.TOOL_INPUT_ERROR
        self.details["tool"] = tool_name
        if path:
            self.details["path"] = path


class ToolOutputError(ValidationError):
    """Tool output schema validation failed."""

    def __init__(self, message: str, tool_name: str, path: list[str] | None = None) -> None:
        super().__init__(message, field=".".join(path) if path else None)
        self.code = ErrorCode.TOOL_OUTPUT_ERROR
        self.details["tool"] = tool_name
        if path:
            self.details["path"] = path


# ============================================================================
# Resource Errors
# ============================================================================


class NotFoundError(MCPError):
    """Resource not found."""

    def __init__(
        self, message: str, resource_type: str | None = None, resource_id: str | None = None
    ) -> None:
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, ErrorCode.NOT_FOUND, details, severity=ErrorSeverity.USER_ERROR)


class ConflictError(MCPError):
    """Resource conflict (e.g., duplicate key, version mismatch)."""

    def __init__(self, message: str, conflict_type: str | None = None) -> None:
        details = {}
        if conflict_type:
            details["conflict_type"] = conflict_type
        super().__init__(message, ErrorCode.CONFLICT, details, severity=ErrorSeverity.USER_ERROR)


# ============================================================================
# Execution Errors
# ============================================================================


class ExecutionError(MCPError):
    """Tool or operation execution failed."""

    def __init__(self, tool_name: str, cause: Exception) -> None:
        super().__init__(
            f"Tool '{tool_name}' failed: {cause}",
            ErrorCode.EXECUTION_ERROR,
            {"tool_name": tool_name, "cause_type": type(cause).__name__, "cause": str(cause)},
            severity=ErrorSeverity.TRANSIENT,  # May be retryable
        )


class TimeoutError(MCPError):
    """Operation timed out."""

    def __init__(
        self, message: str, operation: str | None = None, timeout_ms: int | None = None
    ) -> None:
        details = {}
        if operation:
            details["operation"] = operation
        if timeout_ms:
            details["timeout_ms"] = timeout_ms
        super().__init__(
            message,
            ErrorCode.TIMEOUT,
            details,
            severity=ErrorSeverity.TRANSIENT,  # Retryable
        )


class ToolTimeoutError(TimeoutError):
    """Tool execution exceeded max_execution_time_ms."""

    def __init__(self, tool_name: str, timeout_ms: int) -> None:
        super().__init__(
            f"Tool '{tool_name}' timed out after {timeout_ms}ms",
            operation=tool_name,
            timeout_ms=timeout_ms,
        )
        self.code = ErrorCode.TOOL_TIMEOUT


# ============================================================================
# Rate Limiting
# ============================================================================


class RateLimitError(MCPError):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: int) -> None:
        super().__init__(
            message,
            ErrorCode.RATE_LIMIT_ERROR,
            {"retry_after": retry_after},
            severity=ErrorSeverity.TRANSIENT,
        )
        self.retry_after = retry_after

    def to_details(self) -> ErrorDetails:
        """Include retry_after in ErrorDetails."""
        details = super().to_details()
        return ErrorDetails(
            code=details.code,
            message=details.message,
            context=details.context,
            retry_after=self.retry_after,
            severity=details.severity,
        )


# ============================================================================
# Internal Errors
# ============================================================================


class InternalError(MCPError):
    """Internal server error (unexpected condition)."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        details = {}
        if cause:
            details["cause"] = str(cause)
            details["cause_type"] = type(cause).__name__
        super().__init__(message, ErrorCode.INTERNAL_ERROR, details, severity=ErrorSeverity.FATAL)


class ProviderError(MCPError):
    """External provider/service error."""

    def __init__(self, message: str, provider: str, cause: Exception | None = None) -> None:
        details = {"provider": provider}
        if cause:
            details["cause"] = str(cause)
            details["cause_type"] = type(cause).__name__
        super().__init__(
            message,
            ErrorCode.PROVIDER_ERROR,
            details,
            severity=ErrorSeverity.TRANSIENT,  # Provider may recover
        )


# ============================================================================
# Boundary Translation Functions
# ============================================================================


def to_mcp_error(exc: Exception) -> MCPError:
    """
    Translate arbitrary exceptions to MCPError at boundaries.

    Args:
        exc: Any exception

    Returns:
        MCPError instance

    Example:
        try:
            some_provider_call()
        except ProviderTimeout as e:
            raise to_mcp_error(e)
    """
    # Already an MCPError, return as-is
    if isinstance(exc, MCPError):
        return exc

    # Known exception types -> specific MCPError
    if isinstance(exc, ValueError):
        return ValidationError(message=str(exc), expected="valid value", received=None)
    if isinstance(exc, KeyError):
        return NotFoundError(
            message=f"Key not found: {exc}", resource_type="key", resource_id=str(exc)
        )
    if isinstance(exc, TimeoutError):
        return TimeoutError(message=str(exc), operation="unknown")
    # Unknown exception -> InternalError
    return InternalError(message=f"Unexpected error: {exc}", cause=exc)


def from_mcp_error(error: MCPError) -> dict[str, Any]:
    """
    Convert MCPError to wire format for transport layers.

    Args:
        error: MCPError instance

    Returns:
        Dictionary representation for JSON serialization
    """
    return error.to_dict()

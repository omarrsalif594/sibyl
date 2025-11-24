"""Error types for pipeline execution.

This module defines the error hierarchy for runtime pipeline execution,
providing specific error types for different failure scenarios.

Example:
    # Validation error
    raise ValidationError("Invalid pipeline configuration", details={"field": "steps"})

    # Provider error
    raise ProviderError("LLM provider failed", details={"provider": "openai"})

    # Timeout error
    raise TimeoutError("Pipeline exceeded time limit", details={"timeout_s": 30})
"""

from typing import Any


class PipelineErrorBase(Exception):
    """Base class for all pipeline runtime errors.

    All pipeline errors include:
    - A human-readable message
    - Optional details dict for additional context
    - An error_type string for categorization

    Attributes:
        message: Error message
        details: Additional error context
        error_type: Error type string (defaults to class name)
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        error_type: str | None = None,
    ) -> None:
        """Initialize pipeline error.

        Args:
            message: Error message
            details: Optional additional context
            error_type: Optional error type override
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.error_type = error_type or self.__class__.__name__


class ValidationError(PipelineErrorBase):
    """Error raised when pipeline configuration or inputs are invalid.

    Examples:
        - Invalid pipeline name
        - Missing required input parameters
        - Invalid step configuration
        - Schema validation failures
    """


class ProviderError(PipelineErrorBase):
    """Error raised when a provider call fails.

    This wraps errors from external providers (LLM, embeddings, MCP, etc.)
    and includes provider-specific context.

    Examples:
        - LLM API call failed
        - Embedding generation failed
        - MCP provider timeout
        - Authentication errors
    """


class TimeoutError(PipelineErrorBase):
    """Error raised when pipeline execution exceeds time limit.

    Examples:
        - Pipeline timeout
        - Step timeout
        - Provider call timeout
    """


class StepError(PipelineErrorBase):
    """Error raised when a pipeline step fails to execute.

    This wraps errors that occur during step execution, including:
    - Technique resolution failures
    - Technique execution errors
    - Shop runtime errors

    Examples:
        - Technique not found in shop
        - Technique execution failed
        - Invalid step configuration
    """


class TechniqueError(PipelineErrorBase):
    """Error raised when technique loading or execution fails.

    Examples:
        - Technique not found in registry
        - Technique initialization failed
        - Technique execution error
    """


class RuntimeError(PipelineErrorBase):
    """Error raised for general runtime failures.

    This is used for errors that don't fit into other categories,
    such as:
    - Workspace configuration errors
    - Shop initialization failures
    - Internal runtime errors
    """


class BudgetExceededError(PipelineErrorBase):
    """Error raised when budget limits are exceeded.

    This error is raised when a pipeline, step, or workspace exceeds
    its configured budget limits for cost, tokens, or request count.

    Attributes:
        budget_type: Type of budget exceeded (e.g., "cost", "tokens", "requests")
        limit: The budget limit that was exceeded
        actual: The actual value that exceeded the limit
        scope: Budget scope (e.g., "step", "pipeline", "global")
    """

    def __init__(
        self,
        budget_type: str,
        limit: float,
        actual: float,
        scope: str = "unknown",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize budget exceeded error.

        Args:
            budget_type: Type of budget (cost, tokens, requests)
            limit: Budget limit
            actual: Actual value
            scope: Budget scope (step, pipeline, global)
            details: Additional context
        """
        message = (
            f"{scope.capitalize()} {budget_type} budget exceeded: limit={limit}, actual={actual}"
        )
        error_details = details or {}
        error_details.update(
            {
                "budget_type": budget_type,
                "limit": limit,
                "actual": actual,
                "scope": scope,
            }
        )
        super().__init__(message, details=error_details)
        self.budget_type = budget_type
        self.limit = limit
        self.actual = actual
        self.scope = scope


class StepTimeoutError(TimeoutError):
    """Error raised when a pipeline step exceeds its timeout.

    This error is raised when a step takes longer than its configured
    timeout_s value. It extends TimeoutError with step-specific context.

    Attributes:
        step_name: Name of the step that timed out
        timeout_s: Configured timeout in seconds
    """

    def __init__(
        self,
        step_name: str,
        timeout_s: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize step timeout error.

        Args:
            step_name: Name of the timed-out step
            timeout_s: Timeout limit in seconds
            details: Additional context
        """
        message = f"Step '{step_name}' timed out after {timeout_s}s"
        error_details = details or {}
        error_details.update(
            {
                "step_name": step_name,
                "timeout_s": timeout_s,
            }
        )
        super().__init__(message, details=error_details)
        self.step_name = step_name
        self.timeout_s = timeout_s

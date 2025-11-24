"""Runtime error to taxonomy mapping adapter.

This module provides the runtime-specific mapping from concrete runtime
exceptions to the abstract error taxonomy defined in sibyl.core.pipeline.error_taxonomy.

This keeps the core error taxonomy layer clean and focused on abstract error
codes and types, while the runtime layer handles the concrete mapping logic.
"""

from typing import Any

from sibyl.core.pipeline.error_taxonomy import (
    SibylError,
    create_budget_error,
    create_condition_error,
    create_mcp_error,
    create_runtime_error,
    create_technique_error,
    create_timeout_error,
    create_validation_error,
)


def map_exception_to_error(
    exception: Exception, context: dict[str, Any] | None = None
) -> SibylError:
    """Map a runtime exception to a structured SibylError.

    This function provides runtime-specific mapping logic that bridges
    concrete runtime exceptions to the abstract error taxonomy.

    Args:
        exception: Python exception from runtime execution
        context: Additional context

    Returns:
        Structured SibylError

    Example:
        from sibyl.runtime.pipeline.error_mapping import map_exception_to_error
        from sibyl.runtime.pipeline.errors import BudgetExceededError

        try:
            # ... some operation
        except BudgetExceededError as e:
            error = map_exception_to_error(e, {"pipeline": "my_pipeline"})
            print(error.to_dict())
    """
    # Import runtime-specific errors here to avoid circular dependencies
    from sibyl.core.pipeline.condition_evaluator import ConditionEvaluationError
    from sibyl.runtime.pipeline.errors import (
        BudgetExceededError,
        ProviderError,
        StepTimeoutError,
        TechniqueError,
        ValidationError,
    )

    error_context = context or {}
    error_message = str(exception)

    # Map specific exception types to error codes
    if isinstance(exception, BudgetExceededError):
        error_context.update(
            {
                "budget_type": exception.budget_type,
                "limit": exception.limit,
                "actual": exception.actual,
                "scope": exception.scope,
            }
        )
        return create_budget_error(error_message, error_context)

    if isinstance(exception, StepTimeoutError):
        error_context.update(
            {
                "step_name": exception.step_name,
                "timeout_s": exception.timeout_s,
            }
        )
        return create_timeout_error(error_message, error_context)

    if isinstance(exception, ValidationError):
        return create_validation_error(error_message, error_context)

    if isinstance(exception, ProviderError):
        return create_mcp_error(error_message, error_context)

    if isinstance(exception, TechniqueError):
        return create_technique_error(error_message, error_context)

    if isinstance(exception, ConditionEvaluationError):
        error_context.update(
            {
                "condition": exception.condition,
                "available_keys": exception.context_keys,
            }
        )
        return create_condition_error(error_message, error_context)

    # Default to runtime error for unknown exceptions
    return create_runtime_error(f"{type(exception).__name__}: {error_message}", error_context)


__all__ = ["map_exception_to_error"]

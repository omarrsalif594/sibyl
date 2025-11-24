"""Condition evaluator for control flow.

This module provides condition evaluation for loops, conditionals, and error matching
in pipeline control flow. It uses Jinja2 templates to evaluate boolean expressions.

Example:
    evaluator = ConditionEvaluator()
    context = {"counter": 5, "max": 10}

    result = evaluator.evaluate("{{ counter < max }}", context)
    # Returns: True
"""

import logging
from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError

logger = logging.getLogger(__name__)


class ConditionEvaluationError(Exception):
    """Raised when condition evaluation fails.

    Attributes:
        condition: The condition that failed to evaluate
        original_error: The underlying exception
        context_keys: Available keys in the context
    """

    def __init__(
        self,
        condition: str,
        error: Exception,
        context_keys: list[str],
    ) -> None:
        """Initialize condition evaluation error.

        Args:
            condition: Condition that failed
            error: Original exception
            context_keys: Available context keys
        """
        self.condition = condition
        self.original_error = error
        self.context_keys = context_keys

        message = (
            f"Failed to evaluate condition: {error}\n"
            f"Condition: {condition}\n"
            f"Available context keys: {', '.join(context_keys)}"
        )
        super().__init__(message)


class ConditionEvaluator:
    """Evaluates boolean conditions for control flow.

    Uses Jinja2 templates to evaluate conditions with access to:
    - input: Pipeline input parameters
    - context: Step results and loop variables
    - env: Environment variables
    - error: Error information (in catch blocks)

    Example:
        evaluator = ConditionEvaluator()

        # Loop while condition
        context = {"counter": 5}
        result = evaluator.evaluate("{{ counter < 10 }}", context)

        # Error matching
        error_info = {"type": "TimeoutError", "message": "Connection timeout"}
        result = evaluator.evaluate("{{ error.type == 'TimeoutError' }}",
                                   {"error": error_info})
    """

    def __init__(self) -> None:
        """Initialize condition evaluator with Jinja2 environment."""
        self.env = Environment(
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        logger.debug("ConditionEvaluator initialized")

    def evaluate(
        self,
        condition: str,
        context: dict[str, Any],
    ) -> bool:
        """Evaluate a condition to a boolean result.

        Args:
            condition: Condition template (e.g., "{{ counter < 10 }}")
            context: Context dictionary with variables

        Returns:
            Boolean evaluation result

        Raises:
            ConditionEvaluationError: If condition evaluation fails
        """
        try:
            # Render the condition template
            template = self.env.from_string(condition)
            result = template.render(**context)

            # Convert to boolean
            # Handle common string representations
            if isinstance(result, str):
                result = result.strip()
                if result.lower() in ("true", "1", "yes"):
                    return True
                if result.lower() in ("false", "0", "no", ""):
                    return False
                # Try to interpret as truthy/falsy
                return bool(result)

            # For non-strings, use Python truthiness
            return bool(result)

        except (TemplateSyntaxError, UndefinedError) as e:
            raise ConditionEvaluationError(
                condition=condition,
                error=e,
                context_keys=list(context.keys()),
            ) from e
        except Exception as e:
            raise ConditionEvaluationError(
                condition=condition,
                error=e,
                context_keys=list(context.keys()),
            ) from e

    def is_truthy(self, value: Any) -> bool:
        """Check if a value is truthy (for non-template conditions).

        Args:
            value: Value to check

        Returns:
            True if value is truthy
        """
        return bool(value)

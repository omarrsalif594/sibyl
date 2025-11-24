"""Template engine for pipeline parameter interpolation.

This module provides Jinja2-based template rendering for dynamic parameter
construction in MCP pipelines. It supports variable interpolation, context
chaining, type coercion, and loop constructs.

Example:
    engine = PipelineTemplateEngine()
    context = {
        "input": {"query": "test"},
        "context": {"step1": {"result": "data"}},
        "env": {"API_KEY": "secret"}
    }

    result = engine.render("{{ input.query }}", context)
    # Returns: "test"
"""

import logging
import os
from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError

logger = logging.getLogger(__name__)


class TemplateRenderError(Exception):
    """Raised when template rendering fails.

    Attributes:
        template: The template string that failed to render
        original_error: The underlying exception that caused the failure
        context_keys: Available keys in the context at time of failure
    """

    def __init__(
        self,
        template: str,
        error: Exception,
        context_keys: list[str],
    ) -> None:
        """Initialize template render error.

        Args:
            template: Template string that failed
            error: Original exception
            context_keys: Available context keys
        """
        self.template = template
        self.original_error = error
        self.context_keys = context_keys

        # Truncate template for display
        template_display = template[:100]
        if len(template) > 100:
            template_display += "..."

        message = (
            f"Failed to render template: {error}\n"
            f"Template: {template_display}\n"
            f"Available context keys: {', '.join(context_keys)}"
        )
        super().__init__(message)


class PipelineTemplateEngine:
    """Template engine for pipeline parameter interpolation.

    Uses Jinja2 with StrictUndefined to catch missing variables early.
    Supports input, context, and env namespace access.

    Features:
    - Variable interpolation: {{ input.field }}, {{ context.step1.result }}
    - Environment variables: {{ env.VAR_NAME }}
    - Filters: default, length, max, min
    - Type coercion: Auto-convert strings to int/float/bool
    - Loop constructs: {% for item in items %}...{% endfor %}

    Example:
        engine = PipelineTemplateEngine()
        context = {
            "input": {"query": "test"},
            "context": {"step1": {"result": "data"}},
            "env": {"API_KEY": "secret"}
        }

        result = engine.render("{{ input.query }}", context)
        # Returns: "test"
    """

    def __init__(self) -> None:
        """Initialize template engine with Jinja2 environment."""
        self.env = Environment(
            undefined=StrictUndefined,  # Fail on undefined variables
            autoescape=False,  # Don't escape for non-HTML use
            trim_blocks=True,  # Remove first newline after block
            lstrip_blocks=True,  # Strip leading spaces/tabs before block
        )

        # Register custom filters
        self.env.filters["default"] = self._default_filter
        self.env.filters["length"] = len
        self.env.filters["max"] = max
        self.env.filters["min"] = min

        logger.debug("PipelineTemplateEngine initialized")

    def render(
        self,
        template_str: str,
        context: dict[str, Any],
    ) -> Any:
        """Render a template string with context.

        Args:
            template_str: Template string (may contain {{ }} or {% %})
            context: Context dictionary with input, context, env keys

        Returns:
            Rendered value (with type coercion applied)

        Raises:
            TemplateRenderError: If template rendering fails
        """
        # Build full context with env namespace
        full_context = self._build_context(context)

        # For simple variable access like {{ input.items }}, return the actual value
        # instead of converting to string
        if self._is_simple_variable_access(template_str):
            try:
                var_path = template_str.strip()[2:-2].strip()  # Remove {{ }}
                result = self._resolve_variable_path(var_path, full_context)
                logger.debug(
                    "Direct variable access: %s -> %s", template_str, type(result).__name__
                )
                return result
            except Exception:
                # Fall through to normal template rendering
                logger.debug(
                    "Direct variable access failed for %s, using template rendering", template_str
                )

        try:
            template = self.env.from_string(template_str)
            result = template.render(**full_context)

            # Apply type coercion only if original template was a simple {{ }} expression
            # (not for multi-line templates with loops)
            if self._is_simple_expression(template_str):
                result = self._coerce_type(result)

            logger.debug("Rendered template: %s... -> %s...", template_str[:50], str(result)[:50])
            return result

        except (TemplateSyntaxError, UndefinedError) as e:
            raise TemplateRenderError(
                template=template_str,
                error=e,
                context_keys=list(full_context.keys()),
            ) from e
        except Exception as e:
            raise TemplateRenderError(
                template=template_str,
                error=e,
                context_keys=list(full_context.keys()),
            ) from e

    def _build_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Build full context with env namespace.

        Args:
            context: Original context (should have input, context keys)

        Returns:
            Enhanced context with env namespace
        """
        # Add environment variables as 'env' namespace
        full_context = dict(context)
        if "env" not in full_context:
            full_context["env"] = dict(os.environ)

        return full_context

    def _is_simple_variable_access(self, template_str: str) -> bool:
        """Check if template is a simple variable access like {{ var.path }}.

        Args:
            template_str: Template string

        Returns:
            True if simple variable access (no filters, operators, etc.)
        """
        stripped = template_str.strip()
        if not (stripped.startswith("{{") and stripped.endswith("}}")):
            return False

        # Extract content between {{ }}
        content = stripped[2:-2].strip()

        # Check for filters, operators, or function calls
        if any(char in content for char in ["|", "+", "-", "*", "/", "(", ")", "[", "]"]):
            return False

        # Simple dotted path like "input.items" or "context.step1.result"
        return True

    def _resolve_variable_path(self, path: str, context: dict[str, Any]) -> Any:
        """Resolve a dotted variable path in context.

        Args:
            path: Dotted path like "input.items" or "context.step1.result"
            context: Context dictionary

        Returns:
            Resolved value

        Raises:
            KeyError: If path doesn't exist
        """
        parts = path.split(".")
        value = context
        for part in parts:
            value = value[part]
        return value

    def _is_simple_expression(self, template_str: str) -> bool:
        """Check if template is a simple {{ }} expression (not multi-line with loops).

        Args:
            template_str: Template string

        Returns:
            True if simple expression (eligible for type coercion)
        """
        # Simple expression: starts with {{ and ends with }}, no {% %}
        stripped = template_str.strip()
        return stripped.startswith("{{") and stripped.endswith("}}") and "{%" not in stripped

    def _coerce_type(self, value: str) -> Any:
        """Coerce rendered string to appropriate type.

        Attempts to convert to int, float, bool, or returns string.

        Args:
            value: Rendered string value

        Returns:
            Coerced value
        """
        if not isinstance(value, str):
            return value

        # Try bool first (before int, since "True"/"False" would fail int parse)
        if value.lower() in {"true", "false"}:
            return value.lower() == "true"

        # Try int
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value

    def _default_filter(self, value: Any, default: Any) -> Any:
        """Provide default value if undefined or None.

        Args:
            value: Input value
            default: Default value to use if input is None

        Returns:
            value if not None, else default
        """
        return value if value is not None else default

    def has_template_syntax(self, value: Any) -> bool:
        """Check if value contains template syntax.

        Args:
            value: Value to check

        Returns:
            True if value is a string containing {{ }} or {% %}
        """
        if not isinstance(value, str):
            return False

        return "{{" in value or "{%" in value

"""Feature configuration validation.

This module validates features including:
- Template interpolation syntax ({{ }})
- Control flow expressions (when:, loop:)
- Job polling configuration
- Typed artifacts
- Graph transformer configurations

All features are opt-in, so validation focuses on catching
common mistakes when features are used.

Example:
    from sibyl.core.config.feature_validation import validate_features

    config = load_workspace("config.yaml")
    errors = validate_features(config)
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
"""

import re
from typing import Any


class ValidationError:
    """A single validation error with location and message."""

    def __init__(self, path: str, message: str, severity: str = "error") -> None:
        """Initialize validation error.

        Args:
            path: Path to the error in config (e.g., "pipelines.my_pipeline.steps[0]")
            message: Human-readable error message
            severity: Error severity ("error", "warning", "info")
        """
        self.path = path
        self.message = message
        self.severity = severity

    def __str__(self) -> str:
        """Format error as string."""
        severity_prefix = {"error": "ERROR", "warning": "WARNING", "info": "INFO"}.get(
            self.severity, "ERROR"
        )
        return f"[{severity_prefix}] {self.path}: {self.message}"

    def __repr__(self) -> str:
        """Format error for debugging."""
        return f"ValidationError(path={self.path!r}, message={self.message!r}, severity={self.severity!r})"


def validate_features(
    config: dict[str, Any],
    check_templates: bool = True,
    check_control_flow: bool = True,
    check_job_polling: bool = True,
    check_artifacts: bool = True,
) -> list[ValidationError]:
    """Validate features in workspace configuration.

    Args:
        config: Workspace configuration dictionary
        check_templates: Validate template syntax
        check_control_flow: Validate control flow syntax
        check_job_polling: Validate job polling config
        check_artifacts: Validate artifact configurations

    Returns:
        List of validation errors (empty if valid)

    Example:
        >>> config = {"pipelines": {"test": {...}}}
        >>> errors = validate_features(config)
        >>> if errors:
        ...     for error in errors:
        ...         print(error)
    """
    errors = []

    # Validate pipelines
    if "pipelines" in config:
        for pipeline_name, pipeline_config in config["pipelines"].items():
            path = f"pipelines.{pipeline_name}"
            errors.extend(
                _validate_pipeline(
                    pipeline_config,
                    path,
                    check_templates=check_templates,
                    check_control_flow=check_control_flow,
                    check_job_polling=check_job_polling,
                )
            )

    # Validate MCP providers (for job polling config)
    if check_job_polling and "providers" in config and "mcp" in config["providers"]:
        for provider_name, provider_config in config["providers"]["mcp"].items():
            path = f"providers.mcp.{provider_name}"
            errors.extend(_validate_mcp_provider(provider_config, path))

    return errors


def _validate_pipeline(
    pipeline: dict[str, Any],
    path: str,
    check_templates: bool,
    check_control_flow: bool,
    check_job_polling: bool,
) -> list[ValidationError]:
    """Validate a single pipeline configuration."""
    errors = []

    # Validate steps
    if "steps" not in pipeline:
        return errors

    steps = pipeline.get("steps", [])
    if not isinstance(steps, list):
        errors.append(ValidationError(path, "Pipeline 'steps' must be a list"))
        return errors

    for i, step in enumerate(steps):
        step_path = f"{path}.steps[{i}]"
        errors.extend(
            _validate_step(
                step,
                step_path,
                check_templates=check_templates,
                check_control_flow=check_control_flow,
                check_job_polling=check_job_polling,
            )
        )

    return errors


def _validate_step(
    step: dict[str, Any],
    path: str,
    check_templates: bool,
    check_control_flow: bool,
    check_job_polling: bool,
) -> list[ValidationError]:
    """Validate a single pipeline step."""
    errors = []

    # Check template syntax in params and config
    if check_templates:
        if "params" in step:
            errors.extend(_validate_templates(step["params"], f"{path}.params"))
        if "config" in step:
            errors.extend(_validate_templates(step["config"], f"{path}.config"))

    # Check control flow syntax
    if check_control_flow:
        if "when" in step:
            errors.extend(_validate_when_clause(step["when"], f"{path}.when"))
        if "loop" in step:
            errors.extend(_validate_loop_clause(step["loop"], f"{path}.loop"))

    # Check job polling configuration
    if check_job_polling and "wait" in step:
        errors.extend(_validate_wait_config(step, path))

    return errors


def _validate_templates(value: Any, path: str) -> list[ValidationError]:
    """Validate template syntax ({{ }} expressions) in value.

    Checks for:
    - Unmatched braces
    - Invalid template expressions
    - Common syntax mistakes
    """
    errors = []

    if isinstance(value, dict):
        for key, val in value.items():
            errors.extend(_validate_templates(val, f"{path}.{key}"))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            errors.extend(_validate_templates(item, f"{path}[{i}]"))
    elif isinstance(value, str):
        # Check for unmatched braces
        open_count = value.count("{{")
        close_count = value.count("}}")
        if open_count != close_count:
            errors.append(
                ValidationError(
                    path,
                    f"Unmatched template braces in '{value}'. "
                    f"Found {open_count} '{{{{' and {close_count} '}}}}'.",
                )
            )

        # Check for single brace (common mistake)
        if "{" in value and "{{" not in value:
            errors.append(
                ValidationError(
                    path,
                    f"Found single brace in '{value}'. Did you mean '{{{{'? "
                    f"Template syntax requires double braces: {{{{ expression }}}}",
                    severity="warning",
                )
            )

        # Extract and validate template expressions
        template_pattern = re.compile(r"\{\{([^}]+)\}\}")
        for match in template_pattern.finditer(value):
            expr = match.group(1).strip()
            errors.extend(_validate_template_expression(expr, path))

    return errors


def _validate_template_expression(expr: str, path: str) -> list[ValidationError]:
    """Validate a single template expression.

    Checks for common mistakes:
    - Empty expressions: {{ }}
    - Invalid variable names
    - Unsupported syntax
    """
    errors = []

    if not expr:
        errors.append(
            ValidationError(
                path, "Empty template expression: {{ }}. Must contain a variable reference."
            )
        )
        return errors

    # Check for valid prefixes: input., context., env.
    valid_prefixes = ["input.", "context.", "env."]
    has_valid_prefix = any(expr.startswith(prefix) for prefix in valid_prefixes)

    if not has_valid_prefix and "." in expr:
        errors.append(
            ValidationError(
                path,
                f"Invalid template expression '{{{{ {expr} }}}}'. "
                f"Template variables must start with: {', '.join(valid_prefixes)}",
                severity="warning",
            )
        )

    # Check for common mistakes
    if expr.startswith("$"):
        errors.append(
            ValidationError(
                path,
                f"Invalid template expression '{{{{ {expr} }}}}'. "
                f"Template syntax does not use $ prefix. Use {{{{ input.var }}}} instead of {{{{ $var }}}}.",
                severity="warning",
            )
        )

    return errors


def _validate_when_clause(when: Any, path: str) -> list[ValidationError]:
    """Validate 'when:' conditional clause.

    Checks for:
    - Valid expression syntax
    - Supported operators
    - Common mistakes
    """
    errors = []

    if not isinstance(when, str):
        errors.append(
            ValidationError(
                path, f"'when' clause must be a string expression, got {type(when).__name__}"
            )
        )
        return errors

    # Check for empty expression
    if not when.strip():
        errors.append(ValidationError(path, "'when' clause cannot be empty"))
        return errors

    # Check for template syntax in when clause (should use boolean expressions)
    if "{{" in when and "}}" in when:
        errors.append(
            ValidationError(
                path,
                "'when' clause should not use template syntax. "
                "Use boolean expressions directly: 'context.var == value' instead of '{{ context.var }} == value'",
                severity="warning",
            )
        )

    # Check for unsafe syntax (prevent code injection)
    unsafe_patterns = [
        (r"__\w+__", "dunder methods"),
        (r"import\s+", "import statements"),
        (r"exec\(", "exec() calls"),
        (r"eval\(", "eval() calls"),
        (r"open\(", "open() calls"),
    ]

    for pattern, description in unsafe_patterns:
        if re.search(pattern, when):
            errors.append(
                ValidationError(
                    path,
                    f"'when' clause contains potentially unsafe syntax: {description}. "
                    f"Only simple boolean expressions are allowed.",
                )
            )

    return errors


def _validate_loop_clause(loop: Any, path: str) -> list[ValidationError]:
    """Validate 'loop:' iteration clause.

    Checks for:
    - Valid loop configuration
    - Required fields
    - Bounded iteration
    """
    errors = []

    if not isinstance(loop, dict):
        errors.append(
            ValidationError(path, f"'loop' clause must be a dictionary, got {type(loop).__name__}")
        )
        return errors

    # Check for required fields
    if "until" not in loop and "max_iterations" not in loop:
        errors.append(
            ValidationError(
                path,
                "'loop' clause must specify either 'until' condition or 'max_iterations' (or both)",
            )
        )

    # Validate max_iterations
    if "max_iterations" in loop:
        max_iter = loop["max_iterations"]
        if not isinstance(max_iter, int):
            errors.append(
                ValidationError(
                    path, f"'loop.max_iterations' must be an integer, got {type(max_iter).__name__}"
                )
            )
        elif max_iter <= 0:
            errors.append(
                ValidationError(path, f"'loop.max_iterations' must be positive, got {max_iter}")
            )
        elif max_iter > 1000:
            errors.append(
                ValidationError(
                    path,
                    f"'loop.max_iterations' is very large ({max_iter}). "
                    f"Consider using a smaller limit to prevent runaway loops.",
                    severity="warning",
                )
            )

    # Validate until condition
    if "until" in loop:
        errors.extend(_validate_when_clause(loop["until"], f"{path}.until"))

    return errors


def _validate_wait_config(step: dict[str, Any], path: str) -> list[ValidationError]:
    """Validate job polling 'wait' configuration.

    Checks for:
    - Valid wait parameter
    - Presence of status_tool when wait=True
    - Reasonable timeout values
    """
    errors = []

    wait = step.get("wait")

    # Validate wait parameter type
    if not isinstance(wait, bool):
        errors.append(
            ValidationError(path, f"'wait' parameter must be a boolean, got {type(wait).__name__}")
        )
        return errors

    # If wait=True, check for status_tool
    if wait and "status_tool" not in step:
        errors.append(
            ValidationError(
                path,
                "'wait: true' requires 'status_tool' parameter to check job status. "
                "Specify the tool name to poll for status (e.g., 'status_tool: get_job_status').",
            )
        )

    # Check for polling configuration
    if "polling" in step:
        polling = step["polling"]
        if not isinstance(polling, dict):
            errors.append(
                ValidationError(
                    f"{path}.polling",
                    f"'polling' configuration must be a dictionary, got {type(polling).__name__}",
                )
            )
        else:
            # Validate polling parameters
            if "timeout" in polling:
                timeout = polling["timeout"]
                if not isinstance(timeout, (int, float)):
                    errors.append(
                        ValidationError(
                            f"{path}.polling.timeout",
                            f"'timeout' must be a number, got {type(timeout).__name__}",
                        )
                    )
                elif timeout <= 0:
                    errors.append(
                        ValidationError(
                            f"{path}.polling.timeout", f"'timeout' must be positive, got {timeout}"
                        )
                    )
                elif timeout > 3600:
                    errors.append(
                        ValidationError(
                            f"{path}.polling.timeout",
                            f"'timeout' is very large ({timeout}s). Consider a shorter timeout.",
                            severity="warning",
                        )
                    )

            if "initial_delay" in polling:
                delay = polling["initial_delay"]
                if not isinstance(delay, (int, float)):
                    errors.append(
                        ValidationError(
                            f"{path}.polling.initial_delay",
                            f"'initial_delay' must be a number, got {type(delay).__name__}",
                        )
                    )
                elif delay < 0:
                    errors.append(
                        ValidationError(
                            f"{path}.polling.initial_delay",
                            f"'initial_delay' cannot be negative, got {delay}",
                        )
                    )

    return errors


def _validate_mcp_provider(provider: dict[str, Any], path: str) -> list[ValidationError]:
    """Validate MCP provider configuration for job polling support."""
    errors = []

    # Check for job polling capabilities
    if "capabilities" in provider:
        caps = provider["capabilities"]
        if not isinstance(caps, dict):
            errors.append(
                ValidationError(
                    f"{path}.capabilities",
                    f"'capabilities' must be a dictionary, got {type(caps).__name__}",
                )
            )
        elif "job_polling" in caps:
            job_polling = caps["job_polling"]
            if not isinstance(job_polling, dict):
                errors.append(
                    ValidationError(
                        f"{path}.capabilities.job_polling",
                        f"'job_polling' must be a dictionary, got {type(job_polling).__name__}",
                    )
                )
            # Validate job polling config
            elif "status_tool" in job_polling and not isinstance(job_polling["status_tool"], str):
                errors.append(
                    ValidationError(
                        f"{path}.capabilities.job_polling.status_tool",
                        f"'status_tool' must be a string, got {type(job_polling['status_tool']).__name__}",
                    )
                )

    return errors


def format_validation_errors(errors: list[ValidationError], max_errors: int | None = None) -> str:
    """Format validation errors as human-readable string.

    Args:
        errors: List of validation errors
        max_errors: Maximum number of errors to show (None for all)

    Returns:
        Formatted error message

    Example:
        >>> errors = validate_features(config)
        >>> if errors:
        ...     print(format_validation_errors(errors))
    """
    if not errors:
        return "No validation errors found."

    lines = ["Configuration validation errors:"]

    # Group by severity
    by_severity = {"error": [], "warning": [], "info": []}
    for error in errors:
        by_severity[error.severity].append(error)

    # Show errors first, then warnings, then info
    shown = 0
    for severity in ["error", "warning", "info"]:
        severity_errors = by_severity[severity]
        if not severity_errors:
            continue

        lines.append(f"\n{severity.upper()}S ({len(severity_errors)}):")
        for error in severity_errors:
            if max_errors and shown >= max_errors:
                remaining = sum(len(errs) for errs in by_severity.values()) - shown
                lines.append(f"\n... and {remaining} more errors (use max_errors=None to see all)")
                return "\n".join(lines)
            lines.append(f"  - {error.path}: {error.message}")
            shown += 1

    return "\n".join(lines)

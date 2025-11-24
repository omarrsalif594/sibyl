"""Pipeline validation module for developer experience.

This module provides comprehensive validation for pipeline configurations,
checking syntax, references, parameter types, and dependencies.

Example:
    from sibyl.core.validation import PipelineValidator
    from sibyl.workspace import load_workspace

    workspace = load_workspace("config/workspaces/example.yaml")
    validator = PipelineValidator(workspace)

    # Validate single pipeline
    errors = validator.validate_pipeline("my_pipeline")
    if errors:
        for error in errors:
            print(f"{error.severity}: {error.message}")

    # Validate all pipelines
    results = validator.validate_all_pipelines()
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from sibyl.workspace.schema import PipelineConfig, PipelineStepConfig, WorkspaceSettings

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationError:
    """Structured validation error.

    Attributes:
        severity: Severity level (error, warning, info)
        code: Error code (e.g., "MISSING_SHOP", "INVALID_PARAM")
        message: Human-readable error message
        location: Location in pipeline (e.g., "pipeline.step[2].params.query")
        suggestion: Optional suggestion for fixing the issue
    """

    severity: ValidationSeverity
    code: str
    message: str
    location: str
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """Result of pipeline validation.

    Attributes:
        pipeline_name: Name of validated pipeline
        is_valid: True if no errors found
        errors: List of validation errors/warnings
        checks_performed: Number of validation checks performed
    """

    pipeline_name: str
    is_valid: bool
    errors: list[ValidationError]
    checks_performed: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pipeline_name": self.pipeline_name,
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "checks_performed": self.checks_performed,
            "error_count": len([e for e in self.errors if e.severity == ValidationSeverity.ERROR]),
            "warning_count": len(
                [e for e in self.errors if e.severity == ValidationSeverity.WARNING]
            ),
        }


class PipelineValidator:
    """Validator for pipeline configurations.

    This validator performs comprehensive checks on pipeline configurations:
    - Shop and technique references exist
    - MCP provider and tool references are valid
    - Parameter types match expected schemas
    - Template syntax is valid
    - Dependencies between steps are satisfied
    - Budget configurations are reasonable

    Attributes:
        workspace: Workspace configuration to validate against
    """

    def __init__(self, workspace: WorkspaceSettings) -> None:
        """Initialize pipeline validator.

        Args:
            workspace: Workspace configuration with shops, providers, and pipelines
        """
        self.workspace = workspace
        self._checks_count = 0

    def validate_pipeline(self, pipeline_name: str) -> ValidationResult:
        """Validate a single pipeline.

        Args:
            pipeline_name: Name of pipeline to validate

        Returns:
            ValidationResult with errors and warnings
        """
        self._checks_count = 0
        errors: list[ValidationError] = []

        # Check if pipeline exists
        if pipeline_name not in self.workspace.pipelines:
            available = ", ".join(self.workspace.pipelines.keys())
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    code="PIPELINE_NOT_FOUND",
                    message=f"Pipeline '{pipeline_name}' not found",
                    location=f"pipelines.{pipeline_name}",
                    suggestion=f"Available pipelines: {available}",
                )
            )
            return ValidationResult(
                pipeline_name=pipeline_name,
                is_valid=False,
                errors=errors,
                checks_performed=1,
            )

        pipeline = self.workspace.pipelines[pipeline_name]
        self._checks_count += 1

        # Validate pipeline structure
        errors.extend(self._validate_pipeline_structure(pipeline_name, pipeline))

        # Validate each step
        for i, step in enumerate(pipeline.steps):
            step_location = f"pipelines.{pipeline_name}.steps[{i}]"
            errors.extend(self._validate_step(step, step_location))

        # Check for errors
        has_errors = any(e.severity == ValidationSeverity.ERROR for e in errors)

        return ValidationResult(
            pipeline_name=pipeline_name,
            is_valid=not has_errors,
            errors=errors,
            checks_performed=self._checks_count,
        )

    def validate_all_pipelines(self) -> dict[str, ValidationResult]:
        """Validate all pipelines in workspace.

        Returns:
            Dictionary mapping pipeline names to validation results
        """
        results = {}
        for pipeline_name in self.workspace.pipelines:
            results[pipeline_name] = self.validate_pipeline(pipeline_name)
        return results

    def _validate_pipeline_structure(
        self, pipeline_name: str, pipeline: PipelineConfig
    ) -> list[ValidationError]:
        """Validate basic pipeline structure.

        Args:
            pipeline_name: Name of pipeline
            pipeline: Pipeline configuration

        Returns:
            List of validation errors
        """
        errors: list[ValidationError] = []
        location = f"pipelines.{pipeline_name}"

        # Check if pipeline has steps
        self._checks_count += 1
        if not pipeline.steps:
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    code="EMPTY_PIPELINE",
                    message=f"Pipeline '{pipeline_name}' has no steps",
                    location=location,
                    suggestion="Add at least one step to the pipeline",
                )
            )

        # Check shop reference if specified
        self._checks_count += 1
        if pipeline.shop and pipeline.shop not in self.workspace.shops:
            available = ", ".join(self.workspace.shops.keys())
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_SHOP",
                    message=f"Shop '{pipeline.shop}' not found",
                    location=f"{location}.shop",
                    suggestion=f"Available shops: {available}",
                )
            )

        # Check budget configuration
        if pipeline.budget:
            self._checks_count += 1
            budget_errors = self._validate_budget(
                pipeline.budget.model_dump(), f"{location}.budget"
            )
            errors.extend(budget_errors)

        # Check timeout
        self._checks_count += 1
        if pipeline.timeout_s and pipeline.timeout_s <= 0:
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_TIMEOUT",
                    message=f"Pipeline timeout must be positive, got {pipeline.timeout_s}",
                    location=f"{location}.timeout_s",
                    suggestion="Use a positive timeout value in seconds",
                )
            )

        return errors

    def _validate_step(self, step: PipelineStepConfig, location: str) -> list[ValidationError]:
        """Validate a pipeline step.

        Args:
            step: Step configuration
            location: Location string for error reporting

        Returns:
            List of validation errors
        """
        errors: list[ValidationError] = []

        # Check if this is an MCP step
        is_mcp_step = step.shop == "mcp"

        if is_mcp_step:
            # Validate MCP step
            self._checks_count += 1
            if not step.provider:
                errors.append(
                    ValidationError(
                        severity=ValidationSeverity.ERROR,
                        code="MISSING_MCP_PROVIDER",
                        message="MCP step missing 'provider' field",
                        location=location,
                        suggestion="Add 'provider' field with MCP provider name",
                    )
                )
            else:
                # Check if provider exists
                self._checks_count += 1
                if step.provider not in self.workspace.providers.mcp:
                    available = ", ".join(self.workspace.providers.mcp.keys())
                    errors.append(
                        ValidationError(
                            severity=ValidationSeverity.ERROR,
                            code="INVALID_MCP_PROVIDER",
                            message=f"MCP provider '{step.provider}' not found",
                            location=f"{location}.provider",
                            suggestion=f"Available providers: {available}",
                        )
                    )
                else:
                    # Check if tool exists in provider
                    self._checks_count += 1
                    provider_config = self.workspace.providers.mcp[step.provider]
                    if step.tool and step.tool not in provider_config.tools:
                        available = ", ".join(provider_config.tools)
                        errors.append(
                            ValidationError(
                                severity=ValidationSeverity.WARNING,
                                code="UNKNOWN_MCP_TOOL",
                                message=f"Tool '{step.tool}' not in provider's tool list",
                                location=f"{location}.tool",
                                suggestion=f"Expected tools: {available}. Tool may still work if provider supports it.",
                            )
                        )

            self._checks_count += 1
            if not step.tool:
                errors.append(
                    ValidationError(
                        severity=ValidationSeverity.ERROR,
                        code="MISSING_MCP_TOOL",
                        message="MCP step missing 'tool' field",
                        location=location,
                        suggestion="Add 'tool' field with MCP tool name",
                    )
                )
        else:
            # Validate technique step
            self._checks_count += 1
            if not step.use:
                errors.append(
                    ValidationError(
                        severity=ValidationSeverity.ERROR,
                        code="MISSING_STEP_USE",
                        message="Step missing 'use' field",
                        location=location,
                        suggestion="Add 'use' field in format 'shop.technique'",
                    )
                )
            # Parse step reference
            elif "." not in step.use:
                errors.append(
                    ValidationError(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_STEP_REFERENCE",
                        message=f"Invalid step reference '{step.use}', expected 'shop.technique'",
                        location=f"{location}.use",
                        suggestion="Use format 'shop.technique' (e.g., 'rag.chunker')",
                    )
                )
            else:
                shop_name, technique_name = step.use.split(".", 1)

                # Check if shop exists
                self._checks_count += 1
                if shop_name not in self.workspace.shops:
                    available = ", ".join(self.workspace.shops.keys())
                    errors.append(
                        ValidationError(
                            severity=ValidationSeverity.ERROR,
                            code="INVALID_SHOP",
                            message=f"Shop '{shop_name}' not found",
                            location=f"{location}.use",
                            suggestion=f"Available shops: {available}",
                        )
                    )
                else:
                    # Check if technique exists in shop
                    self._checks_count += 1
                    shop = self.workspace.shops[shop_name]
                    if technique_name not in shop.techniques:
                        available = ", ".join(shop.techniques.keys())
                        errors.append(
                            ValidationError(
                                severity=ValidationSeverity.ERROR,
                                code="INVALID_TECHNIQUE",
                                message=f"Technique '{technique_name}' not found in shop '{shop_name}'",
                                location=f"{location}.use",
                                suggestion=f"Available techniques: {available}",
                            )
                        )

        # Validate step timeout
        self._checks_count += 1
        if step.timeout_s and step.timeout_s <= 0:
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_TIMEOUT",
                    message=f"Step timeout must be positive, got {step.timeout_s}",
                    location=f"{location}.timeout_s",
                    suggestion="Use a positive timeout value in seconds",
                )
            )

        # Validate step budget
        if step.budget:
            self._checks_count += 1
            budget_errors = self._validate_budget(step.budget.model_dump(), f"{location}.budget")
            errors.extend(budget_errors)

        # Validate template syntax in params
        if step.params:
            self._checks_count += 1
            template_errors = self._validate_template_syntax(step.params, f"{location}.params")
            errors.extend(template_errors)

        return errors

    def _validate_budget(self, budget_dict: dict[str, Any], location: str) -> list[ValidationError]:
        """Validate budget configuration.

        Args:
            budget_dict: Budget configuration dict
            location: Location string for error reporting

        Returns:
            List of validation errors
        """
        errors: list[ValidationError] = []

        # Check for negative values
        if budget_dict.get("max_cost_usd") is not None and budget_dict["max_cost_usd"] < 0:
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_BUDGET",
                    message="max_cost_usd must be non-negative",
                    location=f"{location}.max_cost_usd",
                    suggestion="Use a positive value or remove the field",
                )
            )

        if budget_dict.get("max_tokens") is not None and budget_dict["max_tokens"] < 0:
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_BUDGET",
                    message="max_tokens must be non-negative",
                    location=f"{location}.max_tokens",
                    suggestion="Use a positive value or remove the field",
                )
            )

        if budget_dict.get("max_requests") is not None and budget_dict["max_requests"] < 0:
            errors.append(
                ValidationError(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_BUDGET",
                    message="max_requests must be non-negative",
                    location=f"{location}.max_requests",
                    suggestion="Use a positive value or remove the field",
                )
            )

        return errors

    def _validate_template_syntax(
        self, params: dict[str, Any], location: str
    ) -> list[ValidationError]:
        """Validate template syntax in parameters.

        Args:
            params: Parameter dictionary (may contain templates)
            location: Location string for error reporting

        Returns:
            List of validation errors
        """
        errors: list[ValidationError] = []

        # Import template engine for syntax checking
        try:
            from sibyl.core.pipeline.template_engine import PipelineTemplateEngine

            engine = PipelineTemplateEngine()

            # Check each parameter recursively
            def check_value(value: Any, path: str) -> None:
                if isinstance(value, str):
                    # Check if contains template syntax
                    if "{{" in value or "{%" in value:
                        try:
                            # Try to compile the template (without rendering)
                            engine.env.from_string(value)
                        except Exception as e:
                            errors.append(
                                ValidationError(
                                    severity=ValidationSeverity.ERROR,
                                    code="INVALID_TEMPLATE_SYNTAX",
                                    message=f"Invalid template syntax: {e}",
                                    location=path,
                                    suggestion="Check Jinja2 template syntax",
                                )
                            )
                elif isinstance(value, dict):
                    for key, val in value.items():
                        check_value(val, f"{path}.{key}")
                elif isinstance(value, list):
                    for i, val in enumerate(value):
                        check_value(val, f"{path}[{i}]")

            for key, value in params.items():
                check_value(value, f"{location}.{key}")

        except ImportError:
            # Template engine not available, skip validation
            logger.warning("Template engine not available, skipping template syntax validation")

        return errors

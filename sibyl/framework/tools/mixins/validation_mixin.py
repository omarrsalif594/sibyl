"""
ValidationMixin - Automatic input/output validation against JSON Schema.

Provides schema-based validation using jsonschema library.
Use this for tools that need strict input/output validation.
"""

import logging
from typing import Any

try:
    from jsonschema import ValidationError as JSONSchemaValidationError
    from jsonschema import validate
except ImportError:
    msg = "jsonschema is required for validation. Install with: pip install jsonschema"
    raise ImportError(msg) from None

from sibyl.framework.errors import ToolInputError, ToolOutputError

logger = logging.getLogger(__name__)


class ValidationMixin:
    """
    Mixin that adds automatic input/output validation against JSON Schema.

    Validates:
    - Input data before execution (against metadata.input_schema)
    - Output data after execution (against metadata.output_schema)

    Raises:
    - ToolInputError: If input validation fails
    - ToolOutputError: If output validation fails

    Usage:
        @dataclass
        class MyValidatedTool(ValidationMixin, TimingMixin, SimpleTool):
            metadata = ToolMetadata(
                name="my_tool",
                version="1.0.0",
                category="custom",
                description="...",
                input_schema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "depth": {"type": "integer", "minimum": 1},
                    },
                    "required": ["model_id"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "models": {"type": "array"},
                        "count": {"type": "integer"},
                    },
                    "required": ["models", "count"],
                },
                max_execution_time_ms=5000,
            )

            def _execute_impl(self, ctx, input_data):
                # Input already validated - safe to use
                model_id = input_data["model_id"]
                # ... logic ...
                return {"models": [...], "count": 42}
                # Output will be validated automatically

    MRO Positioning:
        ValidationMixin should come BEFORE TimingMixin/ErrorHandlingMixin:
        - ValidationMixin → TimingMixin → SimpleTool

        This ensures:
        1. Input is validated BEFORE timing starts
        2. Output is validated AFTER execution completes
        3. Validation errors are NOT caught by ErrorHandlingMixin
           (they bubble up as ToolInputError/ToolOutputError)

    Schema Format:
        Uses JSON Schema Draft 7 format.
        See: https://json-schema.org/understanding-json-schema/

    Common Schema Patterns:
        # Required string field
        {"type": "string"}

        # Optional integer with range
        {"type": "integer", "minimum": 1, "maximum": 100}

        # Enum (limited choices)
        {"type": "string", "enum": ["option1", "option2"]}

        # Array of strings
        {"type": "array", "items": {"type": "string"}}

        # Nested object
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        }
    """

    def execute(self, ctx: Any, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute with validation wrapper.

        1. Validate input against input_schema
        2. Execute tool (call next in MRO chain)
        3. Validate output against output_schema
        """
        # Step 1: Validate input
        self._validate_input(input_data)

        # Step 2: Execute (calls next in MRO chain)
        result = super().execute(ctx, input_data)  # type: ignore

        # Step 3: Validate output
        self._validate_output(result)

        return result

    def _validate_input(self, input_data: dict[str, Any]) -> None:
        """
        Validate input data against tool's input_schema.

        Args:
            input_data: Input data to validate

        Raises:
            ToolInputError: If validation fails
        """
        # Get schema from metadata
        if not hasattr(self, "metadata"):
            logger.warning(
                "%s has no metadata - skipping input validation", self.__class__.__name__
            )
            return

        schema = self.metadata.input_schema  # type: ignore

        if not schema:
            logger.debug(
                f"{self.metadata.name} has no input_schema - skipping validation"  # type: ignore
            )
            return

        # Validate using jsonschema
        try:
            validate(instance=input_data, schema=schema)
            logger.debug(
                f"Input validation passed for {self.metadata.name}"  # type: ignore
            )
        except JSONSchemaValidationError as e:
            # Extract path for detailed error message
            path = ".".join(str(p) for p in e.path) if e.path else "root"

            error_msg = f"Invalid input at '{path}': {e.message}"
            logger.warning(
                f"Input validation failed for {self.metadata.name}: {error_msg}"  # type: ignore
            )

            raise ToolInputError(
                error_msg,
                tool_name=self.metadata.name,  # type: ignore
                path=list(e.path) if e.path else None,
            ) from e

    def _validate_output(self, output: dict[str, Any]) -> None:
        """
        Validate output data against tool's output_schema.

        Args:
            output: Output data to validate

        Raises:
            ToolOutputError: If validation fails
        """
        # Get schema from metadata
        if not hasattr(self, "metadata"):
            logger.warning(
                "%s has no metadata - skipping output validation", self.__class__.__name__
            )
            return

        schema = self.metadata.output_schema  # type: ignore

        if not schema:
            logger.debug(
                f"{self.metadata.name} has no output_schema - skipping validation"  # type: ignore
            )
            return

        # Validate using jsonschema
        try:
            validate(instance=output, schema=schema)
            logger.debug(
                f"Output validation passed for {self.metadata.name}"  # type: ignore
            )
        except JSONSchemaValidationError as e:
            # Extract path for detailed error message
            path = ".".join(str(p) for p in e.path) if e.path else "root"

            error_msg = f"Invalid output at '{path}': {e.message}"
            logger.exception(
                f"Output validation failed for {self.metadata.name}: {error_msg}"  # type: ignore
            )

            raise ToolOutputError(
                error_msg,
                tool_name=self.metadata.name,  # type: ignore
                path=list(e.path) if e.path else None,
            ) from e

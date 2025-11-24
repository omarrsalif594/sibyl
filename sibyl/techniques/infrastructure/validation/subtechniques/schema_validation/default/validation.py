"""Generic validation framework - domain-agnostic validation primitives.

This module provides pure generic validation abstractions with NO domain assumptions.

Key features:
- Generic ValidationIssue for any validation problem
- Validator protocol for pluggable validators
- Severity levels (error, warning, info)
- Metadata for context
- Zero coupling to any specific domain

Example usage:
    # Define a validator
    class RequiredFieldsValidator(Validator):
        def __init__(self, fields: List[str]):
            self.fields = fields

        async def validate(self, artifact: dict, context: dict) -> List[ValidationIssue]:
            issues = []
            for field in self.fields:
                if field not in artifact:
                    issues.append(ValidationIssue(
                        type="missing_field",
                        message=f"Required field '{field}' is missing",
                        severity="error"
                    ))
            return issues

    # Use validator
    validator = RequiredFieldsValidator(["name", "id"])
    issues = await validator.validate({"id": "123"}, {})
    # Returns: [ValidationIssue(type="missing_field", message="Required field 'name' is missing")]
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import uuid4

# Type aliases
Severity = Literal["error", "warning", "info"]


@dataclass
class ValidationIssue:
    """Generic validation issue - represents any validation problem.

    This is a domain-agnostic representation of a validation problem.
    It can represent missing fields, invalid values, constraint violations, etc.

    Attributes:
        type: Issue type (e.g., "missing_field", "invalid_value", "constraint_violation")
        message: Human-readable description
        path: Optional path to the problematic field (e.g., "product.price")
        severity: Issue severity ("error", "warning", "info")
        metadata: Additional context
        issue_id: Unique identifier
        timestamp: When issue was detected
    """

    type: str
    message: str
    path: str | None = None
    severity: Severity = "error"
    metadata: dict[str, Any] = field(default_factory=dict)
    issue_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "message": self.message,
            "path": self.path,
            "severity": self.severity,
            "metadata": self.metadata,
            "issue_id": self.issue_id,
            "timestamp": self.timestamp.isoformat(),
        }


class Validator(Protocol):
    """Generic validator protocol - no domain assumptions.

    Validators implement this protocol to validate artifacts, entities, or resources.
    They return a list of ValidationIssue objects describing any problems found.
    """

    async def validate(self, artifact: Any, context: dict[str, Any]) -> list[ValidationIssue]:
        """Validate an artifact.

        Args:
            artifact: The artifact to validate (can be dict, object, etc.)
            context: Additional context for validation

        Returns:
            List of ValidationIssue objects (empty if valid)
        """
        ...


class BaseValidator(ABC):
    """Base class for validators with common functionality.

    Provides a foundation for implementing validators with metadata,
    enabling/disabling, and ordering.
    """

    def __init__(
        self, name: str, description: str = "", enabled: bool = True, severity: Severity = "error"
    ) -> None:
        """Initialize validator.

        Args:
            name: Validator name
            description: Human-readable description
            enabled: Whether validator is active
            severity: Default severity for issues
        """
        self.name = name
        self.description = description
        self.enabled = enabled
        self.severity = severity

    @abstractmethod
    async def validate(self, artifact: Any, context: dict[str, Any]) -> list[ValidationIssue]:
        """Validate an artifact.

        Subclasses must implement this method.

        Args:
            artifact: The artifact to validate
            context: Additional context

        Returns:
            List of ValidationIssue objects
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, enabled={self.enabled})"


# Built-in generic validators


class RequiredFieldsValidator(BaseValidator):
    """Validates that required fields are present.

    Example:
        validator = RequiredFieldsValidator(["name", "id", "type"])
        issues = await validator.validate({"id": "123"}, {})
        # Returns issues for missing "name" and "type"
    """

    def __init__(self, fields: list[str], **kwargs) -> None:
        """Initialize with required fields.

        Args:
            fields: List of required field names
            **kwargs: Additional BaseValidator arguments
        """
        super().__init__(
            name=kwargs.get("name", "required_fields"),
            description=kwargs.get("description", f"Validate required fields: {', '.join(fields)}"),
            **{k: v for k, v in kwargs.items() if k not in ["name", "description"]},
        )
        self.fields = fields

    async def validate(self, artifact: Any, context: dict[str, Any]) -> list[ValidationIssue]:
        """Validate required fields."""
        if not isinstance(artifact, dict):
            return [
                ValidationIssue(
                    type="invalid_artifact_type",
                    message=f"Expected dict, got {type(artifact).__name__}",
                    severity=self.severity,
                )
            ]

        issues = []
        for field in self.fields:
            if field not in artifact:
                issues.append(
                    ValidationIssue(
                        type="missing_field",
                        message=f"Required field '{field}' is missing",
                        path=field,
                        severity=self.severity,
                        metadata={"validator": self.name},
                    )
                )

        return issues


class RangeValidator(BaseValidator):
    """Validates that a numeric field is within a range.

    Example:
        validator = RangeValidator("price", min_value=0, max_value=1000)
        issues = await validator.validate({"price": -10}, {})
        # Returns issue for price below minimum
    """

    def __init__(
        self, field: str, min_value: float | None = None, max_value: float | None = None, **kwargs
    ) -> None:
        """Initialize with field and range.

        Args:
            field: Field name to validate
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
            **kwargs: Additional BaseValidator arguments
        """
        super().__init__(
            name=kwargs.get("name", f"range_{field}"),
            description=kwargs.get(
                "description", f"Validate {field} is in range [{min_value}, {max_value}]"
            ),
            **{k: v for k, v in kwargs.items() if k not in ["name", "description"]},
        )
        self.field = field
        self.min_value = min_value
        self.max_value = max_value

    async def validate(self, artifact: Any, context: dict[str, Any]) -> list[ValidationIssue]:
        """Validate range."""
        if not isinstance(artifact, dict):
            return []

        if self.field not in artifact:
            return []  # Field not present, skip validation

        value = artifact[self.field]

        # Check if numeric
        if not isinstance(value, (int, float)):
            return [
                ValidationIssue(
                    type="invalid_type",
                    message=f"Field '{self.field}' must be numeric, got {type(value).__name__}",
                    path=self.field,
                    severity=self.severity,
                    metadata={"validator": self.name},
                )
            ]

        issues = []

        # Check minimum
        if self.min_value is not None and value < self.min_value:
            issues.append(
                ValidationIssue(
                    type="value_below_minimum",
                    message=f"Field '{self.field}' value {value} is below minimum {self.min_value}",
                    path=self.field,
                    severity=self.severity,
                    metadata={"validator": self.name, "value": value, "min": self.min_value},
                )
            )

        # Check maximum
        if self.max_value is not None and value > self.max_value:
            issues.append(
                ValidationIssue(
                    type="value_above_maximum",
                    message=f"Field '{self.field}' value {value} is above maximum {self.max_value}",
                    path=self.field,
                    severity=self.severity,
                    metadata={"validator": self.name, "value": value, "max": self.max_value},
                )
            )

        return issues


class RegexValidator(BaseValidator):
    """Validates that a field matches a regex pattern.

    Example:
        validator = RegexValidator("email", r"^[\\w.-]+@[\\w.-]+\\.\\w+$")
        issues = await validator.validate({"email": "invalid"}, {})
        # Returns issue for invalid email format
    """

    def __init__(self, field: str, pattern: str, **kwargs) -> None:
        """Initialize with field and pattern.

        Args:
            field: Field name to validate
            pattern: Regex pattern
            **kwargs: Additional BaseValidator arguments
        """
        import re  # can be moved to top

        super().__init__(
            name=kwargs.get("name", f"regex_{field}"),
            description=kwargs.get("description", f"Validate {field} matches pattern"),
            **{k: v for k, v in kwargs.items() if k not in ["name", "description"]},
        )
        self.field = field
        self.pattern = pattern
        self.regex = re.compile(pattern)

    async def validate(self, artifact: Any, context: dict[str, Any]) -> list[ValidationIssue]:
        """Validate regex match."""
        if not isinstance(artifact, dict):
            return []

        if self.field not in artifact:
            return []  # Field not present, skip validation

        value = artifact[self.field]

        if not isinstance(value, str):
            return [
                ValidationIssue(
                    type="invalid_type",
                    message=f"Field '{self.field}' must be string, got {type(value).__name__}",
                    path=self.field,
                    severity=self.severity,
                    metadata={"validator": self.name},
                )
            ]

        if not self.regex.match(value):
            return [
                ValidationIssue(
                    type="pattern_mismatch",
                    message=f"Field '{self.field}' value '{value}' does not match pattern",
                    path=self.field,
                    severity=self.severity,
                    metadata={"validator": self.name, "pattern": self.pattern},
                )
            ]

        return []


class JsonSchemaValidator(BaseValidator):
    """Validates an artifact against a JSON schema.

    Example:
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0}
            },
            "required": ["name"]
        }
        validator = JsonSchemaValidator(schema)
        issues = await validator.validate({"age": -5}, {})
        # Returns issues for missing name and invalid age
    """

    def __init__(self, schema: dict[str, Any], **kwargs) -> None:
        """Initialize with JSON schema.

        Args:
            schema: JSON schema dictionary
            **kwargs: Additional BaseValidator arguments
        """
        super().__init__(
            name=kwargs.get("name", "json_schema"),
            description=kwargs.get("description", "Validate against JSON schema"),
            **{k: v for k, v in kwargs.items() if k not in ["name", "description"]},
        )
        self.schema = schema

        # Import jsonschema if available
        try:
            import jsonschema  # can be moved to top

            self.jsonschema = jsonschema
        except ImportError:
            msg = "jsonschema not installed. Install with: pip install jsonschema"
            raise ImportError(msg) from None

    async def validate(self, artifact: Any, context: dict[str, Any]) -> list[ValidationIssue]:
        """Validate against JSON schema."""
        validator = self.jsonschema.Draft7Validator(self.schema)
        errors = list(validator.iter_errors(artifact))

        issues = []
        for error in errors:
            path = ".".join(str(p) for p in error.path) if error.path else None
            issues.append(
                ValidationIssue(
                    type="schema_violation",
                    message=error.message,
                    path=path,
                    severity=self.severity,
                    metadata={
                        "validator": self.name,
                        "schema_path": ".".join(str(p) for p in error.schema_path)
                        if error.schema_path
                        else None,
                    },
                )
            )

        return issues


# Export public API
__all__ = [
    "BaseValidator",
    "JsonSchemaValidator",
    "RangeValidator",
    "RegexValidator",
    "RequiredFieldsValidator",
    "Severity",
    "ValidationIssue",
    "Validator",
]

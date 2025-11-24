"""Generic validator service - orchestrates validation without domain assumptions.

This service takes a list of validators and runs them against artifacts.
It aggregates issues and provides summary statistics.
"""

import logging
from typing import Any

from sibyl.techniques.ai_generation.domain.validation import ValidationIssue, Validator

logger = logging.getLogger(__name__)


class ValidatorService:
    """Generic validation orchestration service.

    This service runs multiple validators against artifacts and aggregates results.
    It's completely domain-agnostic - validators are plugged in via configuration.
    """

    def __init__(self, validators: list[Validator]) -> None:
        """Initialize with list of validators.

        Args:
            validators: List of Validator instances
        """
        self.validators = validators
        logger.info("Initialized ValidatorService with %s validators", len(validators))

    async def validate(
        self, artifact: Any, context: dict[str, Any] | None = None
    ) -> list[ValidationIssue]:
        """Validate an artifact using all registered validators.

        Args:
            artifact: Artifact to validate
            context: Optional validation context

        Returns:
            List of all ValidationIssue objects from all validators
        """
        context = context or {}
        all_issues = []

        for validator in self.validators:
            try:
                # Check if validator is enabled (if it has that attribute)
                if hasattr(validator, "enabled") and not validator.enabled:
                    continue

                issues = await validator.validate(artifact, context)
                all_issues.extend(issues)

                validator_name = getattr(validator, "name", validator.__class__.__name__)
                logger.debug("Validator %s found %s issues", validator_name, len(issues))
            except Exception as e:
                logger.exception("Validator %s failed: %s", validator.__class__.__name__, e)
                # Add validation error as an issue
                all_issues.append(
                    ValidationIssue(
                        type="validator_error",
                        message=f"Validator failed: {e}",
                        severity="warning",
                        metadata={"validator": validator.__class__.__name__, "error": str(e)},
                    )
                )

        logger.info("Validation complete: %s total issues", len(all_issues))
        return all_issues

    def get_summary(self, issues: list[ValidationIssue]) -> dict[str, Any]:
        """Get summary statistics for validation issues.

        Args:
            issues: List of ValidationIssue objects

        Returns:
            Dictionary with summary statistics
        """
        if not issues:
            return {
                "total_issues": 0,
                "by_severity": {},
                "by_type": {},
                "is_valid": True,
            }

        # Count by severity
        by_severity = {}
        for issue in issues:
            by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1

        # Count by type
        by_type = {}
        for issue in issues:
            by_type[issue.type] = by_type.get(issue.type, 0) + 1

        # Determine if valid (no errors)
        is_valid = by_severity.get("error", 0) == 0

        return {
            "total_issues": len(issues),
            "by_severity": by_severity,
            "by_type": by_type,
            "is_valid": is_valid,
            "has_errors": not is_valid,
            "has_warnings": by_severity.get("warning", 0) > 0,
            "has_info": by_severity.get("info", 0) > 0,
        }

    def filter_issues(
        self,
        issues: list[ValidationIssue],
        severity: str | None = None,
        issue_type: str | None = None,
    ) -> list[ValidationIssue]:
        """Filter issues by criteria.

        Args:
            issues: List of ValidationIssue objects
            severity: Filter by severity (optional)
            issue_type: Filter by type (optional)

        Returns:
            Filtered list of issues
        """
        filtered = issues

        if severity:
            filtered = [i for i in filtered if i.severity == severity]

        if issue_type:
            filtered = [i for i in filtered if i.type == issue_type]

        return filtered

    def add_validator(self, validator: Validator) -> None:
        """Add a validator to the service.

        Args:
            validator: Validator instance
        """
        self.validators.append(validator)
        validator_name = getattr(validator, "name", validator.__class__.__name__)
        logger.info("Added validator: %s", validator_name)

    def remove_validator(self, validator_name: str) -> None:
        """Remove a validator by name.

        Args:
            validator_name: Name of validator to remove
        """
        self.validators = [
            v for v in self.validators if getattr(v, "name", v.__class__.__name__) != validator_name
        ]
        logger.info("Removed validator: %s", validator_name)


# Export public API
__all__ = [
    "ValidatorService",
]

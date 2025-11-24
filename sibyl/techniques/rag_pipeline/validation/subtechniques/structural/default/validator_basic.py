"""
Basic validator for core plugin system.

This validator performs generic checks that apply to most code types:
- Non-empty content
- Maximum length limits
- Basic formatting checks
"""

from typing import Any

from sibyl.core.protocols.rag_pipeline.code_processing import CodeType


class BasicValidator:
    """
    Generic validator for text, markdown, and basic code validation.

    Performs fundamental checks:
    - Content is not empty
    - Content doesn't exceed maximum length
    - Basic formatting is reasonable
    """

    def __init__(
        self, max_length: int = 100000, min_length: int = 1, warn_length: int = 50000
    ) -> None:
        """
        Initialize the basic validator.

        Args:
            max_length: Maximum allowed content length (error)
            min_length: Minimum required content length (error)
            warn_length: Length threshold for warnings
        """
        self.max_length = max_length
        self.min_length = min_length
        self.warn_length = warn_length

    def supports(self, code_type: CodeType) -> bool:
        """Support TEXT, MARKDOWN, and SQL types."""
        return code_type in (CodeType.TEXT, CodeType.MARKDOWN, CodeType.SQL)

    def validate(self, code: str, code_type: CodeType, **opts) -> dict[str, Any]:
        """
        Validate code with basic checks.

        Args:
            code: The code to validate
            code_type: Type of code being validated
            **opts: Optional overrides for max_length, min_length, warn_length

        Returns:
            Dictionary with:
            - ok: bool (True if no errors)
            - issues: List of issue dicts with "message" and "severity"
        """
        if not self.supports(code_type):
            return {
                "ok": False,
                "issues": [
                    {"message": f"BasicValidator does not support {code_type}", "severity": "error"}
                ],
            }

        max_len = opts.get("max_length", self.max_length)
        min_len = opts.get("min_length", self.min_length)
        warn_len = opts.get("warn_length", self.warn_length)

        issues: list[dict[str, str]] = []

        # Check minimum length
        if len(code) < min_len:
            issues.append(
                {
                    "message": f"Content is too short ({len(code)} chars, minimum {min_len})",
                    "severity": "error",
                }
            )

        # Check maximum length
        if len(code) > max_len:
            issues.append(
                {
                    "message": f"Content exceeds maximum length ({len(code)} chars, maximum {max_len})",
                    "severity": "error",
                }
            )

        # Warn on large content
        if warn_len < len(code) <= max_len:
            issues.append(
                {
                    "message": f"Content is large ({len(code)} chars, consider splitting)",
                    "severity": "warning",
                }
            )

        # Check for empty lines only
        if code.strip() == "":
            issues.append({"message": "Content contains only whitespace", "severity": "error"})

        # Check for reasonable line lengths (warning only)
        lines = code.split("\n")
        long_lines = [i + 1 for i, line in enumerate(lines) if len(line) > 500]
        if long_lines:
            issues.append(
                {
                    "message": f"Found {len(long_lines)} lines longer than 500 characters (lines: {long_lines[:5]})",
                    "severity": "warning",
                }
            )

        # Code-type specific checks
        if code_type == CodeType.SQL:
            issues.extend(self._validate_sql_basic(code))
        elif code_type == CodeType.MARKDOWN:
            issues.extend(self._validate_markdown_basic(code))

        # Determine overall status
        has_errors = any(issue["severity"] == "error" for issue in issues)

        return {"ok": not has_errors, "issues": issues}

    def _validate_sql_basic(self, sql: str) -> list[dict[str, str]]:
        """
        Basic SQL-specific validation.

        Args:
            sql: SQL code

        Returns:
            List of issues
        """
        issues = []

        # Check for common SQL keywords (very basic sanity check)
        sql_upper = sql.upper()
        has_sql_keywords = any(
            keyword in sql_upper
            for keyword in ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "WITH"]
        )

        if not has_sql_keywords:
            issues.append(
                {
                    "message": "Content marked as SQL but doesn't contain common SQL keywords",
                    "severity": "warning",
                }
            )

        return issues

    def _validate_markdown_basic(self, markdown: str) -> list[dict[str, str]]:
        """
        Basic markdown-specific validation.

        Args:
            markdown: Markdown content

        Returns:
            List of issues
        """
        issues = []

        # Check for unbalanced code fences
        fence_count = markdown.count("```")
        if fence_count % 2 != 0:
            issues.append(
                {
                    "message": f"Unbalanced code fences (found {fence_count} backtick triplets)",
                    "severity": "warning",
                }
            )

        return issues

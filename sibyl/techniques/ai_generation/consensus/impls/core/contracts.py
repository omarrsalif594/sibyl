"""
Decision Contracts for Quorum Engine

Pydantic models defining the output contracts for each atomic decision agent.
All decisions include confidence scores and provenance for auditability.
"""

import time
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ErrorCategory(str, Enum):
    """Categories of SQL compilation errors"""

    TYPE_MISMATCH = "type_mismatch"
    SYNTAX_ERROR = "syntax_error"
    SCHEMA_ISSUE = "schema_issue"
    MACRO_ERROR = "macro_error"
    REF_ERROR = "ref_error"
    SOURCE_ERROR = "source_error"
    INCREMENTAL_ERROR = "incremental_error"
    PERMISSION_ERROR = "permission_error"
    TIMEOUT_ERROR = "timeout_error"
    JINJA_ERROR = "jinja_error"
    HOOK_ERROR = "hook_error"
    CONFIG_ERROR = "config_error"
    UNKNOWN = "unknown"


class FixStrategy(str, Enum):
    """Strategies for fixing SQL errors"""

    CAST_CHANGE = "cast_change"
    FUNCTION_SWAP = "function_swap"
    SCHEMA_UPDATE = "schema_update"
    MACRO_FIX = "macro_fix"
    REF_FIX = "ref_fix"
    SOURCE_FIX = "source_fix"
    SYNTAX_FIX = "syntax_fix"
    PERMISSION_FIX = "permission_fix"
    CONFIG_FIX = "config_fix"


class ChangeType(str, Enum):
    """Types of code changes"""

    REPLACE_RANGE = "replace_range"
    INSERT_AFTER = "insert_after"
    DELETE_RANGE = "delete_range"


class ValidationIssueCode(str, Enum):
    """Machine-friendly issue codes for validation failures"""

    SYNTAX_ERROR = "syntax_error"
    TYPE_MISMATCH_REMAINING = "type_mismatch_remaining"
    SCHEMA_VIOLATION = "schema_violation"
    INCOMPLETE_FIX = "incomplete_fix"
    INTRODUCES_NEW_ERROR = "introduces_new_error"
    LOGIC_ERROR = "logic_error"
    PERFORMANCE_ISSUE = "performance_issue"


# ============================================================================
# Step 1: Diagnosis Decision
# ============================================================================


class DiagnosisDecision(BaseModel):
    """
    Output contract for ErrorDiagnosisAgent.

    Classifies the error into a category for downstream strategy selection.
    """

    category: ErrorCategory
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in diagnosis (0.0-1.0)")
    reasoning: str = Field(
        max_length=160, description="Brief explanation (max 160 chars, fits in logs/tooltips)"
    )
    provenance: dict = Field(
        default_factory=lambda: {"timestamp": time.time()},
        description="Model, prompt version, timestamp for auditability",
    )

    @field_validator("reasoning")
    @classmethod
    def sanitize_reasoning(cls, v: str) -> str:
        """Remove newlines and extra whitespace for clean logging"""
        return " ".join(v.split())

    @model_validator(mode="after")
    def validate_low_confidence_flag(self) -> Any:
        """Warn if confidence is suspiciously low"""
        if self.confidence < 0.3:
            # This will likely be red-flagged, but document it
            self.provenance["low_confidence_warning"] = True
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "category": "type_mismatch",
                "confidence": 0.92,
                "reasoning": "DATETIME vs TIMESTAMP mismatch in WHERE clause comparison",
                "provenance": {
                    "model": "gpt-4o-mini",
                    "prompt_version": "v1.0",
                    "timestamp": 1704067200.0,
                },
            }
        }


# ============================================================================
# Step 2: Strategy Decision
# ============================================================================


class StrategyDecision(BaseModel):
    """
    Output contract for FixStrategyAgent.

    Chooses the fix approach based on diagnosis.
    """

    strategy: FixStrategy
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(max_length=160)
    provenance: dict = Field(default_factory=lambda: {"timestamp": time.time()})

    @field_validator("reasoning")
    @classmethod
    def sanitize_reasoning(cls, v: str) -> str:
        return " ".join(v.split())

    class Config:
        json_schema_extra = {
            "example": {
                "strategy": "function_swap",
                "confidence": 0.88,
                "reasoning": "Swap TIMESTAMP_SUB to DATETIME_SUB to match column type",
                "provenance": {
                    "model": "gpt-4o-mini",
                    "prompt_version": "v1.0",
                    "timestamp": 1704067200.0,
                },
            }
        }


# ============================================================================
# Step 3: Location Decision
# ============================================================================


class LocationDecision(BaseModel):
    """
    Output contract for CodeLocationAgent.

    Identifies the exact line range to apply the fix.
    """

    start_line: int = Field(ge=1, description="Starting line number (1-indexed)")
    end_line: int = Field(ge=1, description="Ending line number (1-indexed)")
    context_lines: str = Field(max_length=1000, description="Actual code snippet for verification")
    confidence: float = Field(ge=0.0, le=1.0)
    source_hash: str = Field(description="SHA256 of original SQL to detect mid-pipeline changes")
    provenance: dict = Field(default_factory=lambda: {"timestamp": time.time()})

    @field_validator("end_line")
    @classmethod
    def validate_line_order(cls, v: int, info: Any) -> int:
        """Ensure end_line >= start_line"""
        if "start_line" in info.data and v < info.data["start_line"]:
            msg = f"end_line ({v}) must be >= start_line ({info.data['start_line']})"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_reasonable_range(self) -> Any:
        """Warn if range is too large (>50 lines suggests low confidence)"""
        range_size = self.end_line - self.start_line + 1
        if range_size > 50:
            self.provenance["large_range_warning"] = range_size
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "start_line": 47,
                "end_line": 47,
                "context_lines": "WHERE updated_at >= TIMESTAMP_SUB(TIMESTAMP('2025-10-08'), INTERVAL 1 DAY)",
                "confidence": 0.95,
                "source_hash": "a7f3d2e1c8b9...",
                "provenance": {
                    "model": "gpt-4o-mini",
                    "prompt_version": "v1.0",
                    "timestamp": 1704067200.0,
                },
            }
        }


# ============================================================================
# Step 4: Fix Generation Decision
# ============================================================================


class FixDecision(BaseModel):
    """
    Output contract for FixGenerationAgent.

    Generates the exact code change to fix the error.
    """

    old_code: str = Field(max_length=500, description="Code to be replaced (max 500 chars)")
    new_code: str = Field(max_length=500, description="Replacement code (max 500 chars)")
    change_type: ChangeType
    confidence: float = Field(ge=0.0, le=1.0)
    affects_lines: list[int] = Field(description="Line numbers affected by this change")
    char_range: tuple[int, int] | None = Field(
        default=None, description="Absolute character positions (start, end) for precise edits"
    )
    provenance: dict = Field(default_factory=lambda: {"timestamp": time.time()})

    @field_validator("new_code")
    @classmethod
    def validate_new_code_differs(cls, v: str, info: Any) -> str:
        """Ensure new_code is actually different from old_code"""
        if "old_code" in info.data and v == info.data["old_code"]:
            msg = "new_code must differ from old_code"
            raise ValueError(msg)
        return v

    @field_validator("new_code")
    @classmethod
    def check_token_budget(cls, v: str) -> str:
        """Enforce token budget (approximate: 4 chars ≈ 1 token)"""
        estimated_tokens = len(v) / 4
        if estimated_tokens > 125:  # 500 chars / 4 = 125 tokens max
            msg = (
                f"new_code exceeds token budget: {estimated_tokens:.0f} tokens "
                f"(max 125 tokens = 500 chars)"
            )
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_no_multiple_statements(self) -> Any:
        """Detect potential SQL injection (multiple statements)"""
        # Check for semicolons in middle of code (not at end)
        code = self.new_code.strip().rstrip(";")
        if ";" in code:
            msg = (
                "new_code contains multiple SQL statements (semicolon in middle). "
                "Atomic fixes must be single-statement."
            )
            raise ValueError(msg)
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "old_code": "TIMESTAMP_SUB(TIMESTAMP('2025-10-08'), INTERVAL 1 DAY)",
                "new_code": "DATETIME_SUB(DATETIME('2025-10-08'), INTERVAL 1 DAY)",
                "change_type": "replace_range",
                "confidence": 0.93,
                "affects_lines": [47],
                "char_range": (1234, 1295),
                "provenance": {
                    "model": "claude-haiku",
                    "prompt_version": "v1.0",
                    "timestamp": 1704067200.0,
                },
            }
        }


# ============================================================================
# Step 5: Validation Decision
# ============================================================================


class ValidationDecision(BaseModel):
    """
    Output contract for ValidationAgent.

    Validates that the fix is correct and complete.
    """

    is_valid: Literal["yes", "no", "needs_refinement"]
    confidence: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(
        default_factory=list, description="Human-readable issues if not valid"
    )
    issue_codes: list[ValidationIssueCode] = Field(
        default_factory=list, description="Machine-friendly issue codes for analytics"
    )
    auto_next_step: str | None = Field(
        default=None, max_length=200, description="Suggested next action if needs_refinement"
    )
    provenance: dict = Field(default_factory=lambda: {"timestamp": time.time()})

    @model_validator(mode="after")
    def validate_issues_when_invalid(self) -> Any:
        """Ensure issues are provided when validation fails"""
        if self.is_valid in ["no", "needs_refinement"]:
            if not self.issues and not self.issue_codes:
                msg = 'Must provide either issues or issue_codes when is_valid != "yes"'
                raise ValueError(msg)
        return self

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "description": "Valid fix",
                    "value": {
                        "is_valid": "yes",
                        "confidence": 0.97,
                        "issues": [],
                        "issue_codes": [],
                        "auto_next_step": None,
                        "provenance": {
                            "model": "gpt-4o-mini",
                            "prompt_version": "v1.0",
                            "timestamp": 1704067200.0,
                        },
                    },
                },
                {
                    "description": "Needs refinement",
                    "value": {
                        "is_valid": "needs_refinement",
                        "confidence": 0.65,
                        "issues": [
                            "Fix addresses type mismatch but may have off-by-one error in date"
                        ],
                        "issue_codes": ["incomplete_fix"],
                        "auto_next_step": "Re-run diagnosis with expanded context (±10 lines)",
                        "provenance": {
                            "model": "gpt-4o-mini",
                            "prompt_version": "v1.0",
                            "timestamp": 1704067200.0,
                        },
                    },
                },
                {
                    "description": "Invalid fix",
                    "value": {
                        "is_valid": "no",
                        "confidence": 0.85,
                        "issues": [
                            "Introduces syntax error (unclosed parenthesis)",
                            "References non-existent column 'created_date'",
                        ],
                        "issue_codes": ["syntax_error", "schema_violation"],
                        "auto_next_step": None,
                        "provenance": {
                            "model": "gpt-4o-mini",
                            "prompt_version": "v1.0",
                            "timestamp": 1704067200.0,
                        },
                    },
                },
            ]
        }


# ============================================================================
# Utility: Decision Type Registry
# ============================================================================

DECISION_TYPES = {
    "diagnosis": DiagnosisDecision,
    "strategy": StrategyDecision,
    "location": LocationDecision,
    "fix": FixDecision,
    "validation": ValidationDecision,
}


def get_decision_type(step_name: str) -> type[BaseModel]:
    """Get the decision contract type for a step name"""
    if step_name not in DECISION_TYPES:
        msg = f"Unknown step: {step_name}. Valid steps: {', '.join(DECISION_TYPES.keys())}"
        raise ValueError(msg)
    return DECISION_TYPES[step_name]

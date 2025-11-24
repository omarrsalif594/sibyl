"""Learning hook for automatic recording of fix attempts.

This hook integrates the learning system with QC operations:
- Captures compilation attempts and their verdicts
- Records fix outcomes (success/failure/partial)
- Tracks which fixes work for which errors
- Builds historical success patterns

Example:
    from sibyl.mcp_server.infrastructure.learning import (
        LearningHook,
        get_learning_store,
    )
    from sibyl.mcp_server.infrastructure.hooks import HookRegistry

    # Register learning hook
    learning_hook = LearningHook(store=get_learning_store())
    registry = HookRegistry()
    registry.register(learning_hook)

    # Now all QC operations will automatically record learning data
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from sibyl.mcp_server.domain.quality_control import ValidationVerdict, VerdictStatus
from sibyl.mcp_server.infrastructure.hooks.protocol import HookContext
from sibyl.mcp_server.infrastructure.learning.protocol import (
    FixOutcome,
    LearningRecord,
    LearningStore,
)

logger = logging.getLogger(__name__)


class LearningHook:
    """Hook that records learning data from QC operations.

    Attributes:
        name: Hook name
        priority: Execution priority (default 10)
        enabled: Whether hook is enabled
        store: Learning store for persistence
    """

    def __init__(
        self,
        store: LearningStore,
        name: str = "learning",
        priority: int = 10,
        enabled: bool = True,
        config_path: Path | None = None,
    ) -> None:
        """Initialize learning hook.

        Args:
            store: Learning store implementation
            name: Hook name
            priority: Execution priority
            enabled: Whether hook is enabled
            config_path: Optional path to learning technique config
        """
        self.name = name
        self.priority = priority
        self.enabled = enabled
        self.store = store

        # Track operation start times for duration calculation
        self._operation_start_times: dict[str, datetime] = {}
        self._retry_counts: dict[str, int] = {}

        # Load configuration from learning technique
        self._config = self._load_config(config_path)

    async def before(self, context: HookContext) -> HookContext:
        """Before hook - track operation start time.

        Args:
            context: Hook context

        Returns:
            Updated context
        """
        if not self.enabled:
            return context

        # Track start time for this operation
        operation_key = self._get_operation_key(context)
        self._operation_start_times[operation_key] = datetime.utcnow()

        return context

    async def after(self, context: HookContext, result: Any) -> Any:
        """After hook - record learning if result is ValidationVerdict.

        Args:
            context: Hook context
            result: Operation result

        Returns:
            Unmodified result
        """
        if not self.enabled:
            return result

        # Only record learning for QC operations that return verdicts
        if not isinstance(result, ValidationVerdict):
            return result

        # Extract information from context and result
        operation_key = self._get_operation_key(context)
        verdict = result

        # Determine outcome from verdict status
        outcome = self._verdict_to_outcome(verdict)

        # Get operation duration
        start_time = self._operation_start_times.get(operation_key)
        duration_seconds = 0.0
        if start_time:
            duration_seconds = (datetime.utcnow() - start_time).total_seconds()

        # Get retry count
        retry_count = self._retry_counts.get(operation_key, 0)

        # Extract model name from context
        model_name = context.metadata.get("model_name")

        # Create learning record
        record = LearningRecord(
            error_message=verdict.feedback,
            error_category=verdict.error_category or "unknown",
            fix_applied=self._extract_fix_description(verdict),
            outcome=outcome,
            model_name=model_name,
            confidence=self._calculate_confidence(verdict),
            matched_keywords=verdict.metadata.get("matched_keywords", []),
            time_to_fix_seconds=duration_seconds,
            retry_count=retry_count,
            metadata={
                "validator_name": verdict.validator_name,
                "validation_id": verdict.validation_id,
                "tool_name": context.tool_name,
                "args": context.args,
            },
        )

        # Save to store
        try:
            self.store.save_record(record)
            logger.debug("Recorded learning: %s -> %s", record.error_category, record.outcome.value)
        except Exception as e:
            logger.warning(f"Failed to save learning record: {e}", exc_info=True)

        # Clean up tracking data if operation completed
        if outcome != FixOutcome.PARTIAL:
            self._operation_start_times.pop(operation_key, None)
            self._retry_counts.pop(operation_key, None)
        else:
            # Increment retry count for partial outcomes
            self._retry_counts[operation_key] = retry_count + 1

        return result

    async def on_error(self, context: HookContext, error: Exception) -> Exception:
        """On error hook - record failed fix attempt.

        Args:
            context: Hook context
            error: The error that occurred

        Returns:
            Unmodified error
        """
        if not self.enabled:
            return error

        operation_key = self._get_operation_key(context)

        # Get operation duration
        start_time = self._operation_start_times.get(operation_key)
        duration_seconds = 0.0
        if start_time:
            duration_seconds = (datetime.utcnow() - start_time).total_seconds()

        # Get retry count
        retry_count = self._retry_counts.get(operation_key, 0)

        # Extract model name
        model_name = context.metadata.get("model_name")

        # Create learning record for failure
        record = LearningRecord(
            error_message=str(error),
            error_category="unknown",  # Unclassified error
            fix_applied="",  # No fix was applied
            outcome=FixOutcome.FAILURE,
            model_name=model_name,
            confidence=0.0,
            matched_keywords=[],
            time_to_fix_seconds=duration_seconds,
            retry_count=retry_count,
            metadata={
                "tool_name": context.tool_name,
                "args": context.args,
                "error_type": type(error).__name__,
            },
        )

        # Save to store
        try:
            self.store.save_record(record)
            logger.debug("Recorded failed learning attempt: %s", type(error).__name__)
        except Exception as e:
            logger.warning(f"Failed to save learning record: {e}", exc_info=True)

        # Clean up tracking
        self._operation_start_times.pop(operation_key, None)
        self._retry_counts.pop(operation_key, None)

        return error

    def _get_operation_key(self, context: HookContext) -> str:
        """Generate unique key for operation tracking.

        Args:
            context: Hook context

        Returns:
            Operation key
        """
        model_name = context.metadata.get("model_name", "unknown")
        return f"{context.tool_name}:{model_name}:{context.invocation_id}"

    def _verdict_to_outcome(self, verdict: ValidationVerdict) -> FixOutcome:
        """Convert verdict status to fix outcome.

        Args:
            verdict: Validation verdict

        Returns:
            Fix outcome
        """
        if verdict.status == VerdictStatus.GREEN:
            return FixOutcome.SUCCESS
        if verdict.status == VerdictStatus.YELLOW:
            return FixOutcome.PARTIAL
        # RED
        return FixOutcome.FAILURE

    def _extract_fix_description(self, verdict: ValidationVerdict) -> str:
        """Extract fix description from verdict.

        Args:
            verdict: Validation verdict

        Returns:
            Fix description
        """
        # Load config from technique
        fix_config = self._config.get("fix_extraction", {}).get("top_n_fixes", {})
        max_fixes = fix_config.get("max_fixes", 3)
        delimiter = fix_config.get("delimiter", "; ")
        use_feedback_fallback = fix_config.get("use_feedback_fallback", True)

        if verdict.suggested_fixes:
            return delimiter.join(verdict.suggested_fixes[:max_fixes])
        if use_feedback_fallback:
            return verdict.feedback
        return ""

    def _calculate_confidence(self, verdict: ValidationVerdict) -> float:
        """Calculate confidence score from verdict.

        Args:
            verdict: Validation verdict

        Returns:
            Confidence score (0.0-1.0)
        """
        # Extract confidence from metadata if available
        base_confidence = verdict.metadata.get("classification_confidence", 0.0)

        # Load config from technique
        conf_config = self._config.get("confidence_calculation", {}).get("verdict_based", {})
        green_min = conf_config.get("green_min_confidence", 0.8)
        red_max = conf_config.get("red_max_confidence", 0.5)
        yellow_confidence = conf_config.get("yellow_confidence")

        # Adjust based on verdict status
        if verdict.status == VerdictStatus.GREEN:
            return max(base_confidence, green_min)
        if verdict.status == VerdictStatus.RED:
            return min(base_confidence, red_max)
        if verdict.status == VerdictStatus.YELLOW:
            return yellow_confidence if yellow_confidence is not None else base_confidence

        return base_confidence

    def get_statistics(self) -> dict[str, Any]:
        """Get learning statistics from store.

        Returns:
            Statistics dictionary
        """
        return self.store.get_statistics()

    def clear_tracking(self) -> None:
        """Clear operation tracking state."""
        self._operation_start_times.clear()
        self._retry_counts.clear()

    def _load_config(self, config_path: Path | None) -> dict[str, Any]:
        """Load configuration from learning technique.

        Args:
            config_path: Optional path to config file

        Returns:
            Configuration dictionary
        """
        if config_path is None:
            # Default to learning technique config
            config_path = (
                Path(__file__).parent.parent.parent / "techniques" / "learning" / "config.yaml"
            )

        try:
            if config_path.exists():
                with open(config_path) as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("Failed to load learning config from %s: %s", config_path, e)

        # Return defaults matching original hardcoded behavior
        return {
            "confidence_calculation": {
                "verdict_based": {
                    "green_min_confidence": 0.8,
                    "red_max_confidence": 0.5,
                    "yellow_confidence": None,
                }
            },
            "fix_extraction": {
                "top_n_fixes": {"max_fixes": 3, "delimiter": "; ", "use_feedback_fallback": True}
            },
        }

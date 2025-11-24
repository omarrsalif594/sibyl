"""Quality control orchestrator implementing QualityControlProvider protocol.

This module provides the main QC orchestration logic:
- Coordinating multiple validators
- Managing retry logic for RED verdicts
- Tracking QC metrics
- Enforcing timeouts
- Delegating code error fixing to Quorum pipeline (when enabled)

Architecture:
- Standard QC mode: Uses QC validators with retry loop
- Quorum mode: Delegates code error fixing to 5-step Quorum pipeline
- Feature flag: USE_QUORUM_FOR_CODE_FIXES (default: True)
"""

import asyncio
import logging
import os
from collections.abc import Callable
from typing import Any

from sibyl.mcp_server.config import QualityControlConfig
from sibyl.mcp_server.domain.quality_control import (
    QCRetryMetadata,
    ValidationVerdict,
    Validator,
    VerdictStatus,
)
from sibyl.mcp_server.infrastructure.quality_control.errors import (
    RetriesExhaustedError,
    ValidationTimeoutError,
)
from sibyl.mcp_server.infrastructure.quality_control.metrics import (
    MetricsContext,
    record_retry,
    record_verdict,
)
from sibyl.mcp_server.infrastructure.quality_control.validators import (
    AntiPatternValidator,
    CompositeValidator,
    SyntaxValidator,
    TypeCheckValidator,
)

logger = logging.getLogger(__name__)

# Feature flag: Use Quorum pipeline for code error fixing
USE_QUORUM_FOR_CODE_FIXES = os.getenv("USE_QUORUM_FOR_CODE_FIXES", "true").lower() == "true"


class QualityControlOrchestrator:
    """Orchestrator for quality control validation and retry logic.

    Implements the QualityControlProvider protocol.

    Modes:
    - Standard QC mode: Uses QC validators with retry loop
    - Quorum mode: Delegates code error fixing to Quorum pipeline (USE_QUORUM_FOR_CODE_FIXES=true)
    """

    def __init__(
        self,
        config: QualityControlConfig,
        quorum_pipeline: Any | None = None,
    ) -> None:
        """Initialize QC orchestrator.

        Args:
            config: Quality control configuration
            quorum_pipeline: Optional Quorum pipeline instance (lazy-loaded if None)
        """
        self.config = config
        self._default_validators = self._create_default_validators()
        self._quorum_pipeline = quorum_pipeline
        logger.info(
            f"QC Orchestrator initialized with {len(self._default_validators)} validators "
            f"(Quorum mode: {USE_QUORUM_FOR_CODE_FIXES})"
        )

    def _create_default_validators(self) -> list[Validator]:
        """Create default validator instances based on config.

        Returns:
            List of enabled validators
        """
        validators = []

        if self.config.syntax_check_enabled:
            validators.append(SyntaxValidator())

        if self.config.anti_pattern_check_enabled:
            # Use non-strict mode (YELLOW for anti-patterns)
            validators.append(AntiPatternValidator(strict_mode=False))

        if self.config.type_check_enabled:
            validators.append(TypeCheckValidator())

        return validators

    def _should_use_quorum(self, context: dict[str, Any]) -> bool:
        """Determine if Quorum pipeline should be used for this validation.

        Args:
            context: Validation context

        Returns:
            True if Quorum should be used, False for standard QC
        """
        if not USE_QUORUM_FOR_CODE_FIXES:
            return False

        # Check if this is a code error fixing scenario
        # Quorum is designed for code error fixing with error messages and source code
        has_error = context.get("error_message") is not None
        has_code = context.get("sql") is not None or context.get("code") is not None
        is_compile_or_test = context.get("tool_name") in ["compile_model", "test_model"]

        return has_error and has_code and is_compile_or_test

    async def _delegate_to_quorum(
        self,
        context: dict[str, Any],
        max_retries: int,
    ) -> tuple[Any, ValidationVerdict, QCRetryMetadata]:
        """Delegate code error fixing to Quorum pipeline.

        Args:
            context: Validation context (must include error_message, code/sql, model_name)
            max_retries: Maximum retry attempts

        Returns:
            Tuple of (output, verdict, retry_metadata)
        """
        logger.info("Delegating to Quorum pipeline for code error fixing")

        # Lazy-load Quorum pipeline if needed
        if self._quorum_pipeline is None:
            try:
                from sibyl.mcp_server.infrastructure.quorum.pipeline import (
                    QuorumPipeline,
                    QuorumPipelineConfig,
                )
                from sibyl.mcp_server.infrastructure.quorum.protocol import VotingPolicy

                # Create default Quorum pipeline
                voting_policy = VotingPolicy(k=3, max_spawns=10)
                quorum_config = QuorumPipelineConfig(
                    voting_policy=voting_policy,
                    enable_red_flagging=True,
                    enable_fallbacks=True,
                    max_cost_per_pipeline_cents=5.0,
                )
                self._quorum_pipeline = QuorumPipeline()
                self._quorum_config = quorum_config
            except ImportError as e:
                logger.exception("Failed to load Quorum pipeline: %s", e)
                msg = "Quorum pipeline not available, falling back to standard QC"
                raise ValidationTimeoutError(msg) from e

        # Execute Quorum pipeline
        try:
            result_state = await self._quorum_pipeline.execute(
                error_message=context["error_message"],
                model_name=context.get("model_name", "unknown"),
                sql=context["sql"],
                config=self._quorum_config,
            )

            # Convert Quorum result to QC verdict
            if result_state.validation and result_state.validation.verdict == "GREEN":
                verdict = ValidationVerdict(
                    status=VerdictStatus.GREEN,
                    feedback=f"Quorum pipeline succeeded: {result_state.fix.code_change if result_state.fix else 'No fix needed'}",
                    validator_name="quorum_pipeline",
                    suggested_fixes=[result_state.fix.code_change] if result_state.fix else [],
                    metadata={
                        "total_cost_cents": result_state.total_cost_cents,
                        "steps_completed": len([s for s in result_state.step_traces if s]),
                        "quorum_mode": True,
                    },
                )
            else:
                verdict = ValidationVerdict(
                    status=VerdictStatus.RED,
                    feedback="Quorum pipeline failed to fix code error",
                    validator_name="quorum_pipeline",
                    metadata={
                        "total_cost_cents": result_state.total_cost_cents,
                        "quorum_mode": True,
                    },
                )

            # Create retry metadata
            retry_metadata = QCRetryMetadata(
                attempt=1,
                max_attempts=1,  # Quorum handles retries internally
                previous_verdicts=[verdict],
                operation_id=result_state.operation_id,
            )

            # Output is the fixed code if successful
            output = {
                "status": "success" if verdict.status == VerdictStatus.GREEN else "failed",
                "fixed_code": result_state.fix.code_change if result_state.fix else None,
                "quorum_result": result_state,
            }

            return output, verdict, retry_metadata

        except Exception as e:
            logger.exception("Quorum pipeline execution failed: %s", e)
            # Return RED verdict
            verdict = ValidationVerdict(
                status=VerdictStatus.RED,
                feedback=f"Quorum pipeline error: {e!s}",
                validator_name="quorum_pipeline",
                error_category="quorum_error",
            )
            retry_metadata = QCRetryMetadata(attempt=1, max_attempts=1)
            return None, verdict, retry_metadata

    async def validate_output(
        self,
        output: Any,
        context: dict[str, Any],
        validators: list[Validator] | None = None,
    ) -> ValidationVerdict:
        """Validate output using configured validators.

        Args:
            output: Tool output to validate
            context: Validation context (tool_name, model_name, etc.)
            validators: Optional list of validators (uses defaults if None)

        Returns:
            Aggregated validation verdict
        """
        if not self.config.enabled:
            # QC disabled, return GREEN verdict
            return ValidationVerdict(
                status=VerdictStatus.GREEN,
                feedback="Quality control disabled",
                validator_name="qc_orchestrator",
                metadata={"qc_enabled": False},
            )

        validators_to_use = validators if validators is not None else self._default_validators

        if not validators_to_use:
            logger.warning("No validators enabled, returning GREEN by default")
            return ValidationVerdict(
                status=VerdictStatus.GREEN,
                feedback="No validators enabled",
                validator_name="qc_orchestrator",
                metadata={"validator_count": 0},
            )

        # Create composite validator
        composite = CompositeValidator(validators_to_use)

        # Run validation with timeout and metrics tracking
        try:
            with MetricsContext():
                verdict = await asyncio.wait_for(
                    composite.validate(output, context),
                    timeout=self.config.timeout_seconds,
                )

            # Record verdict in metrics
            record_verdict(verdict)

            logger.debug(
                f"QC validation complete: {verdict.status.value} "
                f"({len(validators_to_use)} validators)"
            )
            return verdict

        except TimeoutError:
            logger.exception("QC validation timed out after %ss", self.config.timeout_seconds)
            msg = f"Validation timed out after {self.config.timeout_seconds} seconds"
            raise ValidationTimeoutError(msg)

    async def validate_with_retry(
        self,
        operation: Callable[[], Any],
        context: dict[str, Any],
        max_retries: int | None = None,
        validators: list[Validator] | None = None,
    ) -> tuple[Any, ValidationVerdict, QCRetryMetadata]:
        """Execute operation with automatic QC retry on RED verdicts.

        Architecture:
        - If context indicates code error fixing AND USE_QUORUM_FOR_CODE_FIXES=true:
          → Delegate to Quorum pipeline (5-step consensus)
        - Otherwise:
          → Use standard QC validators with retry loop

        Args:
            operation: Callable that produces output to validate
            context: Validation context (include error_message + code/sql for Quorum mode)
            max_retries: Maximum retry attempts (uses config default if None)
            validators: Optional list of validators

        Returns:
            Tuple of (output, final_verdict, retry_metadata)

        Raises:
            RetriesExhaustedError: If all retry attempts exhausted with RED verdict
        """
        # Check if Quorum should be used for this validation
        if self._should_use_quorum(context):
            logger.info("Using Quorum pipeline for code error fixing")
            max_attempts = max_retries if max_retries is not None else self.config.max_retries
            return await self._delegate_to_quorum(context, max_attempts)

        # Standard QC validation path
        if not self.config.enabled:
            # QC disabled, just run operation once
            output = await operation() if asyncio.iscoroutinefunction(operation) else operation()
            verdict = ValidationVerdict(
                status=VerdictStatus.GREEN,
                feedback="Quality control disabled",
                validator_name="qc_orchestrator",
            )
            metadata = QCRetryMetadata(attempt=1, max_attempts=1)
            return output, verdict, metadata

        max_attempts = max_retries if max_retries is not None else self.config.max_retries
        max_attempts = max(1, max_attempts)  # At least 1 attempt

        retry_metadata = QCRetryMetadata(
            attempt=1,
            max_attempts=max_attempts,
            previous_verdicts=[],
            previous_fixes_tried=[],
        )

        for attempt in range(1, max_attempts + 1):
            logger.info("QC attempt %s/%s", attempt, max_attempts)

            # Execute operation
            try:
                if asyncio.iscoroutinefunction(operation):
                    output = await operation()
                else:
                    output = operation()
            except Exception as e:
                logger.exception("Operation failed on attempt %s: %s", attempt, e)
                # Create RED verdict for operation failure
                verdict = ValidationVerdict(
                    status=VerdictStatus.RED,
                    feedback=f"Operation failed: {e!s}",
                    error_category="operation_error",
                    validator_name="qc_orchestrator",
                )
                retry_metadata = QCRetryMetadata(
                    attempt=attempt,
                    max_attempts=max_attempts,
                    previous_verdicts=[*retry_metadata.previous_verdicts, verdict],
                    previous_fixes_tried=retry_metadata.previous_fixes_tried,
                    operation_id=retry_metadata.operation_id,
                )

                if attempt >= max_attempts:
                    msg = f"Operation failed after {max_attempts} attempts"
                    raise RetriesExhaustedError(
                        msg,
                        verdicts=[verdict],
                        retry_metadata=retry_metadata.to_dict(),
                    ) from e
                continue

            # Validate output
            verdict = await self.validate_output(output, context, validators)

            # Update retry metadata
            retry_metadata = QCRetryMetadata(
                attempt=attempt,
                max_attempts=max_attempts,
                previous_verdicts=[*retry_metadata.previous_verdicts, verdict],
                previous_fixes_tried=retry_metadata.previous_fixes_tried + verdict.suggested_fixes,
                operation_id=retry_metadata.operation_id,
            )

            # Check verdict
            if verdict.status == VerdictStatus.GREEN:
                logger.info("QC passed on attempt %s", attempt)
                # Record retry metrics (success)
                if attempt > 1:
                    record_retry(retry_metadata, success=True)
                return output, verdict, retry_metadata

            if verdict.status == VerdictStatus.YELLOW:
                if self.config.retry_on_yellow and attempt < max_attempts:
                    logger.warning(
                        "QC returned YELLOW on attempt %s, retrying (retry_on_yellow=True)", attempt
                    )
                    # Enrich context with previous verdict feedback
                    context["previous_verdict"] = verdict.feedback
                    context["suggested_fixes"] = verdict.suggested_fixes
                    continue
                logger.info(
                    f"QC returned YELLOW on attempt {attempt}, accepting "
                    f"(retry_on_yellow=False or final attempt)"
                )
                # Record retry metrics (success with warnings)
                if attempt > 1:
                    record_retry(retry_metadata, success=True)
                return output, verdict, retry_metadata

            if verdict.status == VerdictStatus.RED:
                if attempt >= max_attempts:
                    logger.error(
                        f"QC returned RED on final attempt {attempt}/{max_attempts}, "
                        f"retries exhausted"
                    )
                    # Record retry metrics (failure)
                    if attempt > 1:
                        record_retry(retry_metadata, success=False)
                    msg = f"Validation failed after {max_attempts} attempts: {verdict.feedback}"
                    raise RetriesExhaustedError(
                        msg,
                        verdicts=retry_metadata.previous_verdicts,
                        retry_metadata=retry_metadata.to_dict(),
                    )
                logger.warning("QC returned RED on attempt %s/%s, retrying", attempt, max_attempts)
                # Enrich context with previous verdict feedback
                context["previous_verdict"] = verdict.feedback
                context["suggested_fixes"] = verdict.suggested_fixes
                context["error_category"] = verdict.error_category
                continue

        # Should not reach here, but handle gracefully
        msg = f"Validation failed after {max_attempts} attempts"
        raise RetriesExhaustedError(
            msg,
            verdicts=retry_metadata.previous_verdicts,
            retry_metadata=retry_metadata.to_dict(),
        )


def create_default_qc_orchestrator(config: QualityControlConfig) -> QualityControlOrchestrator:
    """Factory function to create default QC orchestrator.

    Args:
        config: Quality control configuration

    Returns:
        Configured QualityControlOrchestrator instance
    """
    return QualityControlOrchestrator(config)

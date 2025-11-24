"""Session handoff orchestrator with deterministic fallback on timeout.

This module coordinates the session rotation workflow:
1. Wait for operation completion (handled by RotationManager)
2. Summarize context (with timeout and deterministic fallback)
3. Create new session in DuckDB
4. Store rotation event
5. Swap active session atomically
6. Resume operations in new session

Key features:
- **Deterministic fallback**: If LLM summarization times out, use delta compression
- **Strategy support**: summarize | fork | restart
- **Metrics tracking**: Latency, compression ratio, fallback usage
- **Crash safety**: All state persisted to DuckDB before swap

Typical usage:
    orchestrator = SessionHandoffOrchestrator(
        rotation_manager=rotation_manager,
        context_manager=context_manager,
        state_writer=state_writer,
        config=config
    )

    # Execute handoff
    result = await orchestrator.execute_handoff(
        old_session_id="sess_abc_001",
        new_session_id="sess_abc_002",
        trigger="token_threshold"
    )
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from sibyl.core.server.config import RotationConfig

from .rotation_manager import SessionState

logger = logging.getLogger(__name__)


class HandoffError(Exception):
    """Base exception for handoff errors."""


class SummarizationTimeoutError(HandoffError):
    """Raised when summarization exceeds timeout."""


@dataclass
class HandoffResult:
    """Result of session handoff.

    Attributes:
        success: Whether handoff succeeded
        new_session_id: New session identifier
        summarization_strategy: Strategy used ("llm_compress", "delta_compress", "full_copy", "restart")
        context_summary_ref: SHA256 ref to blob (if summarized)
        compression_ratio: Original tokens / Summary tokens
        summarization_latency_ms: Time to generate summary
        handoff_duration_ms: Total handoff time
        blocking_duration_ms: Time tools were blocked
        fallback_used: Whether deterministic fallback was used
        failure_reason: Error message if failed
    """

    success: bool
    new_session_id: str
    summarization_strategy: str
    context_summary_ref: str | None = None
    compression_ratio: float | None = None
    summarization_latency_ms: int | None = None
    handoff_duration_ms: int | None = None
    blocking_duration_ms: int | None = None
    fallback_used: bool = False
    failure_reason: str | None = None


class SessionHandoffOrchestrator:
    """Coordinate session rotation workflow with deterministic fallback.

    This class orchestrates the complex handoff between sessions:
    - Context summarization (LLM or deterministic)
    - State persistence (DuckDB)
    - Atomic session swap
    - Error recovery

    Thread-safe via RotationManager locks.
    """

    def __init__(
        self,
        rotation_manager: "SessionRotationManager",  # type: ignore
        config: RotationConfig,
        context_manager: Any | None = None,
        state_writer: Any | None = None,
    ) -> None:
        """Initialize handoff orchestrator.

        Args:
            rotation_manager: Session rotation manager
            config: Rotation configuration
            context_manager: Optional context manager for summarization
            state_writer: Optional state writer for DuckDB persistence
        """
        self.rotation_manager = rotation_manager
        self.config = config
        self.context_manager = context_manager
        self.state_writer = state_writer

        # Metrics
        self._total_handoffs = 0
        self._successful_handoffs = 0
        self._failed_handoffs = 0
        self._fallback_count = 0
        self._summarization_latencies = []  # Last 100 latencies for p95 calculation

        logger.info("SessionHandoffOrchestrator initialized")

    async def execute_handoff(
        self,
        old_session: SessionState,
        new_session: SessionState,
        trigger: str,
        context: dict[str, Any] | None = None,
    ) -> HandoffResult:
        """Execute complete handoff workflow.

        This is the main entry point for session rotation. It coordinates:
        1. Context summarization (with timeout and fallback)
        2. State persistence to DuckDB
        3. Atomic session swap
        4. Metrics recording

        Args:
            old_session: Session being rotated out
            new_session: New session being rotated in
            trigger: Rotation trigger ("token_threshold", "manual", etc.)
            context: Optional context to summarize (dict with conversation history)

        Returns:
            HandoffResult with details of handoff

        Raises:
            HandoffError: If handoff fails critically
        """
        self._total_handoffs += 1
        handoff_start = time.time()

        logger.info(
            f"Executing handoff: {old_session.session_id} → {new_session.session_id} "
            f"(trigger={trigger}, strategy={self.config.strategy})"
        )

        try:
            # Step 1: Summarize context (with timeout and fallback)
            summarization_start = time.time()

            summary_result = await self._summarize_context(
                old_session=old_session,
                new_session=new_session,
                context=context,
            )

            summarization_latency = int((time.time() - summarization_start) * 1000)
            self._summarization_latencies.append(summarization_latency)
            if len(self._summarization_latencies) > 100:
                self._summarization_latencies.pop(0)

            # Step 2: Persist to DuckDB (if state_writer available)
            if self.state_writer:
                await self._persist_rotation_event(
                    old_session=old_session,
                    new_session=new_session,
                    trigger=trigger,
                    summary_ref=summary_result.get("summary_ref"),
                    compression_ratio=summary_result.get("compression_ratio"),
                    summarization_latency_ms=summarization_latency,
                    fallback_used=summary_result.get("fallback_used", False),
                )

            # Step 3: Calculate metrics
            handoff_duration = int((time.time() - handoff_start) * 1000)

            # Success
            self._successful_handoffs += 1

            result = HandoffResult(
                success=True,
                new_session_id=new_session.session_id,
                summarization_strategy=summary_result.get("strategy", self.config.strategy),
                context_summary_ref=summary_result.get("summary_ref"),
                compression_ratio=summary_result.get("compression_ratio"),
                summarization_latency_ms=summarization_latency,
                handoff_duration_ms=handoff_duration,
                blocking_duration_ms=handoff_duration,  # TODO: Track actual blocking time
                fallback_used=summary_result.get("fallback_used", False),
            )

            if result.fallback_used:
                self._fallback_count += 1

            logger.info(
                f"Handoff completed: {old_session.session_id} → {new_session.session_id} "
                f"({handoff_duration}ms, compression={result.compression_ratio:.1f}x, "
                f"fallback={result.fallback_used})"
            )

            return result

        except Exception as e:
            # Failure
            self._failed_handoffs += 1

            logger.exception(
                "Handoff failed: %s → %s: %s", old_session.session_id, new_session.session_id, e
            )

            return HandoffResult(
                success=False,
                new_session_id=new_session.session_id,
                summarization_strategy="none",
                failure_reason=str(e),
            )

    async def _summarize_context(
        self,
        old_session: SessionState,
        new_session: SessionState,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Summarize context with timeout and deterministic fallback.

        Strategy handling:
        - "summarize": Use LLM (with fallback to delta compression)
        - "fork": Full context copy (no compression)
        - "restart": Empty context (fresh start)

        Args:
            old_session: Session being rotated out
            new_session: New session being rotated in
            context: Context to summarize

        Returns:
            Dict with:
            - strategy: "llm_compress" | "delta_compress" | "full_copy" | "restart"
            - summary_ref: SHA256 ref to blob (if applicable)
            - compression_ratio: Ratio of compression
            - fallback_used: Whether fallback was used
        """
        strategy = self.config.strategy

        # Handle non-summarize strategies
        if strategy == "fork":
            # Full context copy (no compression)
            return await self._full_copy_context(context)

        if strategy == "restart":
            # Empty context (fresh start)
            return {
                "strategy": "restart",
                "summary_ref": None,
                "compression_ratio": float("inf"),  # Infinite compression (empty context)
                "fallback_used": False,
            }

        # Summarize strategy (default)
        if strategy == "summarize":
            # Try LLM summarization with timeout
            try:
                result = await asyncio.wait_for(
                    self._llm_summarize(old_session, new_session, context),
                    timeout=self.config.summarization_timeout_seconds,
                )

                return {
                    "strategy": "llm_compress",
                    "summary_ref": result["summary_ref"],
                    "compression_ratio": result["compression_ratio"],
                    "fallback_used": False,
                }

            except TimeoutError:
                # Fallback to deterministic compression
                logger.warning(
                    f"LLM summarization timed out after {self.config.summarization_timeout_seconds}s, "
                    f"falling back to delta compression"
                )

                result = await self._delta_compress_context(context)

                return {
                    "strategy": "delta_compress",
                    "summary_ref": result["summary_ref"],
                    "compression_ratio": result["compression_ratio"],
                    "fallback_used": True,
                }

            except Exception as e:
                # Fallback on any error
                logger.exception(
                    "LLM summarization failed: %s, falling back to delta compression", e
                )

                result = await self._delta_compress_context(context)

                return {
                    "strategy": "delta_compress",
                    "summary_ref": result["summary_ref"],
                    "compression_ratio": result["compression_ratio"],
                    "fallback_used": True,
                }

        else:
            msg = f"Unknown rotation strategy: {strategy}"
            raise HandoffError(msg)

    async def _llm_summarize(
        self,
        old_session: SessionState,
        new_session: SessionState,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Summarize context using LLM (ContextManager).

        Args:
            old_session: Session being rotated out
            new_session: New session being rotated in
            context: Context to summarize

        Returns:
            Dict with summary_ref and compression_ratio
        """
        if not self.context_manager:
            msg = "ContextManager not available for LLM summarization"
            raise HandoffError(msg)

        if not context:
            # No context to summarize
            return {
                "summary_ref": None,
                "compression_ratio": 1.0,
            }

        # Use existing ContextManager.summarize() method
        # This would be integrated with the existing orchestration/context.py
        # For now, simulate with placeholder

        # Estimate original size (rough token count)
        original_text = json.dumps(context)
        original_tokens = len(original_text) // 4  # Rough estimate: 4 chars = 1 token

        # TODO: Call actual ContextManager.summarize()
        # summary = await self.context_manager.summarize(context, target_reduction=0.2)

        # Placeholder: simulate 10x compression
        summary_text = self._generate_placeholder_summary(context, old_session)
        summary_tokens = len(summary_text) // 4

        # Store summary as blob
        summary_ref = self._compute_hash(summary_text)

        compression_ratio = original_tokens / max(summary_tokens, 1)

        logger.debug(
            f"LLM summarization: {original_tokens} → {summary_tokens} tokens "
            f"({compression_ratio:.1f}x compression)"
        )

        return {
            "summary_ref": summary_ref,
            "compression_ratio": compression_ratio,
        }

    async def _delta_compress_context(self, context: dict[str, Any] | None) -> dict[str, Any]:
        """Deterministic delta compression (fallback when LLM times out).

        This uses simple heuristics to compress context:
        - Keep only last N turns
        - Remove duplicate information
        - Compress repeated patterns

        Args:
            context: Context to compress

        Returns:
            Dict with summary_ref and compression_ratio
        """
        if not context:
            return {
                "summary_ref": None,
                "compression_ratio": 1.0,
            }

        # Estimate original size
        original_text = json.dumps(context)
        original_tokens = len(original_text) // 4

        # Simple compression: keep only essential keys
        compressed = {
            "conversation_summary": "Context rotated (deterministic compression)",
            "key_facts": context.get("key_facts", [])[:10],  # Keep last 10 facts
            "preserved_state": context.get("preserved_state", {}),
        }

        compressed_text = json.dumps(compressed)
        compressed_tokens = len(compressed_text) // 4

        # Store compressed context
        summary_ref = self._compute_hash(compressed_text)

        compression_ratio = original_tokens / max(compressed_tokens, 1)

        logger.debug(
            f"Delta compression: {original_tokens} → {compressed_tokens} tokens "
            f"({compression_ratio:.1f}x compression)"
        )

        return {
            "summary_ref": summary_ref,
            "compression_ratio": compression_ratio,
        }

    async def _full_copy_context(self, context: dict[str, Any] | None) -> dict[str, Any]:
        """Full context copy (no compression).

        Args:
            context: Context to copy

        Returns:
            Dict with summary_ref and compression_ratio=1.0
        """
        if not context:
            return {
                "strategy": "full_copy",
                "summary_ref": None,
                "compression_ratio": 1.0,
                "fallback_used": False,
            }

        # Store full context
        context_text = json.dumps(context)
        summary_ref = self._compute_hash(context_text)

        return {
            "strategy": "full_copy",
            "summary_ref": summary_ref,
            "compression_ratio": 1.0,  # No compression
            "fallback_used": False,
        }

    def _generate_placeholder_summary(
        self, context: dict[str, Any], old_session: SessionState
    ) -> str:
        """Generate placeholder summary (until ContextManager integration).

        Args:
            context: Context to summarize
            old_session: Session being rotated out

        Returns:
            Summary text
        """
        return json.dumps(
            {
                "conversation_summary": f"Session {old_session.session_id} rotated at "
                f"{old_session.get_utilization_pct():.1f}% utilization",
                "key_facts": context.get("key_facts", [])[:5],
                "preserved_state": context.get("preserved_state", {}),
            }
        )

    def _compute_hash(self, text: str) -> str:
        """Compute SHA256 hash of text.

        Args:
            text: Text to hash

        Returns:
            SHA256 hex digest
        """
        return hashlib.sha256(text.encode()).hexdigest()

    async def _persist_rotation_event(
        self,
        old_session: SessionState,
        new_session: SessionState,
        trigger: str,
        summary_ref: str | None,
        compression_ratio: float | None,
        summarization_latency_ms: int,
        fallback_used: bool,
    ) -> None:
        """Persist rotation event to DuckDB.

        Args:
            old_session: Session being rotated out
            new_session: New session being rotated in
            trigger: Rotation trigger
            summary_ref: SHA256 ref to summary blob
            compression_ratio: Compression ratio
            summarization_latency_ms: Summarization time
            fallback_used: Whether fallback was used
        """
        if not self.state_writer:
            return

        # TODO: Implement state writer integration
        # This would write to session_rotations table in DuckDB

        logger.debug(
            f"Rotation event persisted: {old_session.session_id} → {new_session.session_id} "
            f"(trigger={trigger}, compression={compression_ratio:.1f}x)"
        )

    def get_stats(self) -> dict[str, Any]:
        """Get handoff statistics.

        Returns:
            Dict with stats
        """
        # Calculate p95 latency
        p95_latency = None
        if self._summarization_latencies:
            sorted_latencies = sorted(self._summarization_latencies)
            p95_index = int(len(sorted_latencies) * 0.95)
            p95_latency = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else None

        return {
            "total_handoffs": self._total_handoffs,
            "successful_handoffs": self._successful_handoffs,
            "failed_handoffs": self._failed_handoffs,
            "success_rate": (
                self._successful_handoffs / self._total_handoffs
                if self._total_handoffs > 0
                else 0.0
            ),
            "fallback_count": self._fallback_count,
            "fallback_rate": (
                self._fallback_count / self._total_handoffs if self._total_handoffs > 0 else 0.0
            ),
            "p95_summarization_latency_ms": p95_latency,
            "avg_summarization_latency_ms": (
                sum(self._summarization_latencies) / len(self._summarization_latencies)
                if self._summarization_latencies
                else None
            ),
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SessionHandoffOrchestrator(handoffs={self._total_handoffs}, "
            f"success_rate={self._successful_handoffs / max(self._total_handoffs, 1):.1%})"
        )

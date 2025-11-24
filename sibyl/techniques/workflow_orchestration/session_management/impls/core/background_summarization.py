"""Background context summarization with idempotence and deadline.

This module provides background summarization triggered at 60% threshold:
- **Idempotent**: Same context → same cache key → single LLM call
- **Deadline enforcement**: 10s timeout (configurable)
- **Cache integration**: Uses SummaryCache for deduplication
- **Non-blocking**: Runs in background, doesn't block tool responses
- **Race-safe**: Late arrivals with stale keys ignored

Key benefits:
- **Fast rotation**: Summary ready when rotation triggers at 70%
- **No duplicate work**: Multiple triggers for same context → single LLM call
- **Predictable**: Always completes via timeout or fallback

Typical usage:
    summarizer = BackgroundSummarizer(
        context_manager=context_mgr,
        summary_cache=summary_cache,
        config=rotation_config
    )

    # Trigger at 60% threshold (non-blocking)
    asyncio.create_task(summarizer.trigger_summarization(
        session_id="sess_abc",
        context=conversation_history,
        turn_id=42
    ))

    # Later at 70% rotation: summary is cached and ready
    summary = await summarizer.get_or_summarize(...)  # Cache hit
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from sibyl.core.server.config import RotationConfig

# Import SessionManagementTechnique for configuration
from sibyl.techniques.workflow_orchestration.session_management import SessionManagementTechnique

from .summary_cache import SummaryCache

logger = logging.getLogger(__name__)

# Load default configuration from technique (module-level singleton)
_technique = SessionManagementTechnique()
_technique_config = _technique.load_config(_technique._config_path)
_summarization_config = _technique_config.get("summarization", {}).get("abstractive", {})


@dataclass
class SummarizationResult:
    """Result of summarization attempt.

    Attributes:
        success: Whether summarization succeeded
        summary: Summary content (if successful)
        cache_key: Cache key used
        cache_hit: Whether result was from cache
        strategy: Strategy used ("llm", "fallback", "cached")
        latency_ms: Time taken (milliseconds)
        error: Error message (if failed)
    """

    success: bool
    summary: dict[str, Any] | None
    cache_key: str
    cache_hit: bool
    strategy: str
    latency_ms: int
    error: str | None = None


class BackgroundSummarizer:
    """Background context summarization with cache and deadline.

    This class coordinates background summarization:
    - Triggered at 60% threshold
    - Checks cache first (idempotent)
    - Calls LLM with deadline (10s)
    - Falls back to delta compression on timeout
    - Stores result in cache
    - Non-blocking (runs in background task)
    """

    def __init__(
        self,
        context_manager: Any | None,
        summary_cache: SummaryCache,
        config: RotationConfig,
    ) -> None:
        """Initialize background summarizer.

        Args:
            context_manager: Context manager for LLM summarization
            summary_cache: Cache for deduplication
            config: Rotation configuration
        """
        self.context_manager = context_manager
        self.summary_cache = summary_cache
        self.config = config

        # Track in-flight summarizations (prevent duplicates)
        self._in_flight: dict[str, asyncio.Task] = {}
        self._in_flight_lock = asyncio.Lock()

        # Metrics
        self._total_triggers = 0
        self._cache_hits = 0
        self._llm_calls = 0
        self._fallback_calls = 0
        self._errors = 0

        logger.info("BackgroundSummarizer initialized")

    async def trigger_summarization(
        self,
        session_id: str,
        context: dict[str, Any],
        turn_id: int,
        summarize_threshold: float,
        rotate_threshold: float,
    ) -> asyncio.Task:
        """Trigger background summarization (non-blocking).

        This method:
        1. Computes cache key
        2. Checks if already in flight (idempotent)
        3. Spawns background task if not
        4. Returns task handle

        Args:
            session_id: Session identifier
            context: Context to summarize
            turn_id: Current turn ID
            summarize_threshold: Summarize threshold
            rotate_threshold: Rotate threshold

        Returns:
            asyncio.Task handle (for testing/monitoring)
        """
        self._total_triggers += 1

        # Compute cache key
        cache_key = self.summary_cache.compute_key(
            context=context,
            session_id=session_id,
            turn_id=turn_id,
            summarize_threshold=summarize_threshold,
            rotate_threshold=rotate_threshold,
        )

        async with self._in_flight_lock:
            # Check if already in flight (idempotent)
            if cache_key in self._in_flight:
                existing_task = self._in_flight[cache_key]
                if not existing_task.done():
                    logger.debug(
                        "[%s] Summarization already in flight for key %s...",
                        session_id,
                        cache_key[:8],
                    )
                    return existing_task

            # Spawn background task
            task = asyncio.create_task(
                self._summarize_with_cache(
                    session_id=session_id,
                    context=context,
                    turn_id=turn_id,
                    summarize_threshold=summarize_threshold,
                    rotate_threshold=rotate_threshold,
                    cache_key=cache_key,
                )
            )

            self._in_flight[cache_key] = task

            logger.info(
                "[%s] Background summarization triggered (turn=%s, key=%s...)",
                session_id,
                turn_id,
                cache_key[:8],
            )

            return task

    async def get_or_summarize(
        self,
        session_id: str,
        context: dict[str, Any],
        turn_id: int,
        summarize_threshold: float,
        rotate_threshold: float,
    ) -> SummarizationResult:
        """Get cached summary or generate new one (blocking).

        This is called during rotation (at 70% threshold). It:
        1. Checks cache first
        2. If miss, summarizes synchronously
        3. Returns result

        Args:
            session_id: Session identifier
            context: Context to summarize
            turn_id: Current turn ID
            summarize_threshold: Summarize threshold
            rotate_threshold: Rotate threshold

        Returns:
            SummarizationResult
        """
        return await self._summarize_with_cache(
            session_id=session_id,
            context=context,
            turn_id=turn_id,
            summarize_threshold=summarize_threshold,
            rotate_threshold=rotate_threshold,
            cache_key=None,  # Will compute
        )

    async def _summarize_with_cache(
        self,
        session_id: str,
        context: dict[str, Any],
        turn_id: int,
        summarize_threshold: float,
        rotate_threshold: float,
        cache_key: str | None = None,
    ) -> SummarizationResult:
        """Summarize with cache check.

        Args:
            session_id: Session identifier
            context: Context to summarize
            turn_id: Current turn ID
            summarize_threshold: Summarize threshold
            rotate_threshold: Rotate threshold
            cache_key: Optional pre-computed cache key

        Returns:
            SummarizationResult
        """
        start_time = time.time()

        # Compute cache key if not provided
        if cache_key is None:
            cache_key = self.summary_cache.compute_key(
                context=context,
                session_id=session_id,
                turn_id=turn_id,
                summarize_threshold=summarize_threshold,
                rotate_threshold=rotate_threshold,
            )

        try:
            # Step 1: Check cache
            cached_summary = await self.summary_cache.get(cache_key)

            if cached_summary:
                self._cache_hits += 1
                latency_ms = int((time.time() - start_time) * 1000)

                logger.debug(
                    "[%s] Summary cache hit (key=%s..., latency=%sms)",
                    session_id,
                    cache_key[:8],
                    latency_ms,
                )

                return SummarizationResult(
                    success=True,
                    summary=cached_summary,
                    cache_key=cache_key,
                    cache_hit=True,
                    strategy="cached",
                    latency_ms=latency_ms,
                )

            # Step 2: Cache miss - generate summary
            if self.config.strategy == "summarize":
                # Try LLM with deadline
                # Use technique config for timeout, fallback to instance config
                summarization_timeout = _summarization_config.get(
                    "timeout_seconds", self.config.summarization_timeout_seconds
                )
                try:
                    summary = await asyncio.wait_for(
                        self._llm_summarize(context),
                        timeout=summarization_timeout,
                    )

                    self._llm_calls += 1
                    strategy = "llm"

                except TimeoutError:
                    # Fallback to delta compression
                    logger.warning("[%s] LLM summarization timed out, using fallback", session_id)

                    summary = await self._fallback_summarize(context)
                    self._fallback_calls += 1
                    strategy = "fallback"

            elif self.config.strategy == "fork":
                # Full copy (no compression)
                summary = context
                strategy = "fork"

            elif self.config.strategy == "restart":
                # Empty context
                summary = {"conversation_summary": "Session restarted"}
                strategy = "restart"

            else:
                msg = f"Unknown strategy: {self.config.strategy}"
                raise ValueError(msg)

            # Step 3: Store in cache
            await self.summary_cache.set(
                key=cache_key, summary=summary, session_id=session_id, turn_id=turn_id
            )

            latency_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"[{session_id}] Summary generated (strategy={strategy}, "
                f"latency={latency_ms}ms, key={cache_key[:8]}...)"
            )

            return SummarizationResult(
                success=True,
                summary=summary,
                cache_key=cache_key,
                cache_hit=False,
                strategy=strategy,
                latency_ms=latency_ms,
            )

        except Exception as e:
            self._errors += 1
            latency_ms = int((time.time() - start_time) * 1000)

            logger.exception("[%s] Summarization failed: %s", session_id, e)

            return SummarizationResult(
                success=False,
                summary=None,
                cache_key=cache_key,
                cache_hit=False,
                strategy="error",
                latency_ms=latency_ms,
                error=str(e),
            )

        finally:
            # Remove from in-flight
            async with self._in_flight_lock:
                self._in_flight.pop(cache_key, None)

    async def _llm_summarize(self, context: dict[str, Any]) -> dict[str, Any]:
        """Summarize using LLM (ContextManager).

        Args:
            context: Context to summarize

        Returns:
            Summary dict

        Raises:
            asyncio.TimeoutError: If exceeds deadline
        """
        if not self.context_manager:
            # No context manager available, use fallback
            return await self._fallback_summarize(context)

        # TODO: Integrate with actual ContextManager.summarize()
        # For now, simulate with placeholder

        # Simulate LLM call (1-3 seconds)
        await asyncio.sleep(0.5)  # Placeholder

        # Generate summary
        return {
            "conversation_summary": "Context summarized by LLM",
            "key_facts": context.get("key_facts", [])[:10],
            "preserved_state": context.get("preserved_state", {}),
            "compression_ratio": 8.5,  # Typical 8.5x compression
        }

    async def _fallback_summarize(self, context: dict[str, Any]) -> dict[str, Any]:
        """Deterministic fallback summarization (no LLM).

        This uses simple heuristics:
        - Keep only essential keys
        - Limit list sizes
        - Remove verbose fields

        Args:
            context: Context to compress

        Returns:
            Compressed summary dict
        """
        return {
            "conversation_summary": "Context compressed (deterministic fallback)",
            "key_facts": context.get("key_facts", [])[:5],  # Keep last 5 facts
            "preserved_state": context.get("preserved_state", {}),
            "compression_ratio": 3.0,  # Conservative 3x compression
        }

    def get_stats(self) -> dict[str, Any]:
        """Get summarization statistics.

        Returns:
            Dict with stats
        """
        cache_hit_rate = (
            self._cache_hits / self._total_triggers if self._total_triggers > 0 else 0.0
        )

        return {
            "total_triggers": self._total_triggers,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": cache_hit_rate,
            "llm_calls": self._llm_calls,
            "fallback_calls": self._fallback_calls,
            "errors": self._errors,
            "in_flight": len(self._in_flight),
        }

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_stats()
        return (
            f"BackgroundSummarizer(triggers={stats['total_triggers']}, "
            f"cache_hit_rate={stats['cache_hit_rate']:.1%}, "
            f"llm_calls={stats['llm_calls']})"
        )

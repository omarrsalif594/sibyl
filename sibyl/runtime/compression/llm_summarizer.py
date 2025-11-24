"""LLM-based summarization compressor.

Adapts existing session management summarization techniques for use
in compression chains.
"""

import logging
import time
from typing import Any

from sibyl.core.compression import CompressionMetrics, CompressionResult
from sibyl.core.contracts.providers import CompletionOptions, LLMProvider

logger = logging.getLogger(__name__)


class LLMSummarizer:
    """LLM-based text summarization compressor.

    Uses an LLM to generate concise summaries of long prompts while
    preserving key intent and context.

    Features:
    - Configurable compression target ratio
    - Timeout protection
    - Fallback to extractive summarization
    - Token counting for accurate metrics
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        target_compression_ratio: float = 0.3,
        max_summary_tokens: int = 500,
        timeout_seconds: float = 10.0,
        temperature: float = 0.3,
    ) -> None:
        """Initialize LLM summarizer.

        Args:
            llm_provider: LLM provider for summarization
            target_compression_ratio: Target ratio (0.3 = 70% reduction)
            max_summary_tokens: Maximum tokens in summary
            timeout_seconds: Timeout for LLM call
            temperature: LLM temperature for summarization
        """
        self.name = "llm_summarizer"
        self.llm_provider = llm_provider
        self.target_compression_ratio = target_compression_ratio
        self.max_summary_tokens = max_summary_tokens
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    async def compress(self, text: str, **metadata: Any) -> CompressionResult:
        """Compress text using LLM summarization.

        Args:
            text: Input text to compress
            **metadata: Additional context (user_intent, domain, etc.)

        Returns:
            CompressionResult with summary and metrics
        """
        start_time = time.time()
        original_size = len(text)

        try:
            # Build summarization prompt
            prompt = self._build_prompt(text, metadata)

            # Call LLM if available
            if self.llm_provider:
                summary = await self._llm_summarize(prompt)
            else:
                logger.warning("No LLM provider available, using extractive fallback")
                summary = self._extractive_fallback(text)

            compressed_size = len(summary)
            duration_ms = (time.time() - start_time) * 1000

            # Extract key points and tags from summary
            key_points = self._extract_key_points(summary)
            tags = metadata.get("tags", [])

            metrics = CompressionMetrics(
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compressed_size / original_size if original_size > 0 else 1.0,
                tokens_saved=self._estimate_tokens_saved(original_size, compressed_size),
                duration_ms=duration_ms,
                compressor_name=self.name,
                metadata={
                    "method": "llm" if self.llm_provider else "extractive_fallback",
                    "target_ratio": self.target_compression_ratio,
                    "max_tokens": self.max_summary_tokens,
                },
            )

            return CompressionResult(
                original_text=text,
                compressed_text=summary,
                summary=summary,
                key_points=key_points,
                tags=tags,
                compression_ratio=metrics.compression_ratio,
                metrics=metrics,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception("LLM summarization failed: %s", e)

            # Return fallback
            fallback = self._extractive_fallback(text)

            metrics = CompressionMetrics(
                original_size=original_size,
                compressed_size=len(fallback),
                compression_ratio=len(fallback) / original_size if original_size > 0 else 1.0,
                tokens_saved=0,
                duration_ms=duration_ms,
                compressor_name=self.name,
                metadata={"error": str(e), "method": "error_fallback"},
            )

            return CompressionResult(
                original_text=text,
                compressed_text=fallback,
                summary=fallback,
                key_points=[],
                tags=[],
                compression_ratio=metrics.compression_ratio,
                metrics=metrics,
                error=str(e),
            )

    def _build_prompt(self, text: str, metadata: dict) -> str:
        """Build summarization prompt.

        Args:
            text: Text to summarize
            metadata: Context metadata

        Returns:
            Formatted prompt for LLM
        """
        user_intent = metadata.get("user_intent", "")
        domain = metadata.get("domain", "")

        context_hints = []
        if user_intent:
            context_hints.append(f"User intent: {user_intent}")
        if domain:
            context_hints.append(f"Domain: {domain}")

        context_section = "\n".join(context_hints) if context_hints else ""

        return f"""Summarize the following text concisely while preserving all key information and intent.
Target: Reduce to approximately {int(self.target_compression_ratio * 100)}% of original length.
Maximum: {self.max_summary_tokens} tokens.

{context_section}

Text to summarize:
{text}

Concise summary:"""

    async def _llm_summarize(self, prompt: str) -> str:
        """Call LLM for summarization.

        Args:
            prompt: Summarization prompt

        Returns:
            Summary text
        """
        if not self.llm_provider:
            msg = "No LLM provider configured"
            raise ValueError(msg)

        options = CompletionOptions(
            temperature=self.temperature,
            max_tokens=self.max_summary_tokens,
            timeout_seconds=self.timeout_seconds,
        )

        result = await self.llm_provider.complete_async(prompt, options)
        return result.get("text", "")

    def _extractive_fallback(self, text: str) -> str:
        """Simple extractive summarization fallback.

        Takes first and last portions of text with middle context.

        Args:
            text: Text to compress

        Returns:
            Compressed text
        """
        target_length = int(len(text) * self.target_compression_ratio)

        if len(text) <= target_length:
            return text

        # Take proportional chunks from beginning, middle, and end
        chunk_size = target_length // 3

        beginning = text[:chunk_size]
        middle_start = (len(text) - chunk_size) // 2
        middle = text[middle_start : middle_start + chunk_size]
        end = text[-chunk_size:]

        return f"{beginning}\n...\n{middle}\n...\n{end}"

    def _extract_key_points(self, summary: str) -> list[str]:
        """Extract key points from summary.

        Simple heuristic: look for bullet points or numbered lists.

        Args:
            summary: Summary text

        Returns:
            List of key points
        """
        key_points = []
        lines = summary.split("\n")

        for line in lines:
            line = line.strip()
            # Look for bullet points or numbered items
            if line.startswith(("-", "*", "•")) or (
                len(line) > 2 and line[0].isdigit() and line[1] in ".):"
            ):
                # Remove bullet/number prefix
                point = line.lstrip("-*•0123456789.): ").strip()
                if point:
                    key_points.append(point)

        return key_points

    def _estimate_tokens_saved(self, original_size: int, compressed_size: int) -> int:
        """Estimate tokens saved based on character reduction.

        Rough approximation: 4 characters ≈ 1 token.

        Args:
            original_size: Original text size in characters
            compressed_size: Compressed text size in characters

        Returns:
            Estimated tokens saved
        """
        chars_saved = original_size - compressed_size
        return chars_saved // 4  # Rough approximation

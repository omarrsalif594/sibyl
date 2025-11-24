"""Algorithmic text compression.

Provides deterministic compression without requiring LLM calls.
Useful for quick compression or fallback scenarios.
"""

import logging
import re
import time
from typing import Any

from sibyl.core.compression import CompressionMetrics, CompressionResult

logger = logging.getLogger(__name__)


class AlgorithmicCompressor:
    """Algorithmic text compressor.

    Uses deterministic algorithms to compress text:
    - Whitespace normalization
    - Duplicate sentence removal
    - Common phrase deduplication
    - Optional abbreviation expansion

    No LLM required - fast and deterministic.
    """

    def __init__(
        self,
        normalize_whitespace: bool = True,
        remove_duplicates: bool = True,
        deduplicate_phrases: bool = True,
        min_compression_ratio: float = 0.7,
    ) -> None:
        """Initialize algorithmic compressor.

        Args:
            normalize_whitespace: Normalize excess whitespace
            remove_duplicates: Remove duplicate sentences
            deduplicate_phrases: Remove repeated phrases
            min_compression_ratio: Minimum compression to attempt
        """
        self.name = "algorithmic_compressor"
        self.normalize_whitespace = normalize_whitespace
        self.remove_duplicates = remove_duplicates
        self.deduplicate_phrases = deduplicate_phrases
        self.min_compression_ratio = min_compression_ratio

    async def compress(self, text: str, **metadata: Any) -> CompressionResult:
        """Compress text using algorithmic methods.

        Args:
            text: Input text to compress
            **metadata: Additional context (not used)

        Returns:
            CompressionResult with compressed text
        """
        start_time = time.time()
        original_size = len(text)
        compressed = text

        steps = []

        try:
            # Step 1: Normalize whitespace
            if self.normalize_whitespace:
                before_size = len(compressed)
                compressed = self._normalize_whitespace(compressed)
                after_size = len(compressed)
                steps.append(
                    {
                        "step": "normalize_whitespace",
                        "before": before_size,
                        "after": after_size,
                        "saved": before_size - after_size,
                    }
                )

            # Step 2: Remove duplicate sentences
            if self.remove_duplicates:
                before_size = len(compressed)
                compressed = self._remove_duplicates(compressed)
                after_size = len(compressed)
                steps.append(
                    {
                        "step": "remove_duplicates",
                        "before": before_size,
                        "after": after_size,
                        "saved": before_size - after_size,
                    }
                )

            # Step 3: Deduplicate repeated phrases
            if self.deduplicate_phrases:
                before_size = len(compressed)
                compressed = self._deduplicate_phrases(compressed)
                after_size = len(compressed)
                steps.append(
                    {
                        "step": "deduplicate_phrases",
                        "before": before_size,
                        "after": after_size,
                        "saved": before_size - after_size,
                    }
                )

            compressed_size = len(compressed)
            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
            duration_ms = (time.time() - start_time) * 1000

            # If compression didn't meet minimum threshold, return original
            if compression_ratio > self.min_compression_ratio:
                logger.debug(
                    f"Compression ratio {compression_ratio:.2f} exceeds minimum "
                    f"{self.min_compression_ratio:.2f}, returning original"
                )
                compressed = text
                compressed_size = original_size
                compression_ratio = 1.0

            metrics = CompressionMetrics(
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                tokens_saved=(original_size - compressed_size) // 4,  # Rough estimate
                duration_ms=duration_ms,
                compressor_name=self.name,
                metadata={
                    "steps": steps,
                    "total_bytes_saved": sum(s["saved"] for s in steps),
                    "methods": {
                        "normalize_whitespace": self.normalize_whitespace,
                        "remove_duplicates": self.remove_duplicates,
                        "deduplicate_phrases": self.deduplicate_phrases,
                    },
                },
            )

            return CompressionResult(
                original_text=text,
                compressed_text=compressed,
                summary=compressed,
                key_points=[],  # Algorithmic compression doesn't extract key points
                tags=[],
                compression_ratio=compression_ratio,
                metrics=metrics,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception("Algorithmic compression failed: %s", e)

            metrics = CompressionMetrics(
                original_size=original_size,
                compressed_size=original_size,
                compression_ratio=1.0,
                tokens_saved=0,
                duration_ms=duration_ms,
                compressor_name=self.name,
                metadata={"error": str(e)},
            )

            return CompressionResult(
                original_text=text,
                compressed_text=text,
                summary=text,
                key_points=[],
                tags=[],
                compression_ratio=1.0,
                metrics=metrics,
                error=str(e),
            )

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize excess whitespace.

        - Replace multiple spaces with single space
        - Remove trailing/leading whitespace
        - Collapse multiple newlines to max 2

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        # Replace multiple spaces with single space
        text = re.sub(r" +", " ", text)

        # Collapse multiple newlines to max 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)

        return text.strip()

    def _remove_duplicates(self, text: str) -> str:
        """Remove duplicate sentences.

        Keeps first occurrence of each unique sentence.

        Args:
            text: Input text

        Returns:
            Text with duplicates removed
        """
        # Split into sentences (simple approach)
        sentences = re.split(r"[.!?]+", text)

        seen = set()
        unique_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Normalize for comparison (lowercase, remove extra spaces)
            normalized = " ".join(sentence.lower().split())

            if normalized not in seen:
                seen.add(normalized)
                unique_sentences.append(sentence)

        # Reconstruct with periods
        return ". ".join(unique_sentences) + "." if unique_sentences else ""

    def _deduplicate_phrases(self, text: str) -> str:
        """Remove repeated phrases (5+ word sequences).

        Keeps first occurrence of repeated phrase.

        Args:
            text: Input text

        Returns:
            Text with repeated phrases removed
        """
        words = text.split()
        if len(words) < 10:
            return text

        # Look for repeated 5-word phrases
        phrase_length = 5
        seen_phrases = {}
        indices_to_remove = set()

        for i in range(len(words) - phrase_length + 1):
            phrase = " ".join(words[i : i + phrase_length])
            phrase_normalized = phrase.lower()

            if phrase_normalized in seen_phrases:
                # Mark these words for removal
                for j in range(i, i + phrase_length):
                    indices_to_remove.add(j)
            else:
                seen_phrases[phrase_normalized] = i

        # Rebuild text without removed indices
        if indices_to_remove:
            filtered_words = [word for i, word in enumerate(words) if i not in indices_to_remove]
            return " ".join(filtered_words)

        return text

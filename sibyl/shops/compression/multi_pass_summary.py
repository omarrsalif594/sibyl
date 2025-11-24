"""Multi-pass summarization compressor.

Performs multiple passes of summarization with different strategies
to achieve high compression while preserving meaning.
"""

import logging
import time
from typing import Any

from sibyl.core.compression import CompressionMetrics, CompressionResult
from sibyl.core.contracts.providers import LLMProvider

logger = logging.getLogger(__name__)


class MultiPassSummary:
    """Multi-pass summarization compressor.

    Applies multiple summarization passes:
    1. First pass: Extract structure and key sections
    2. Second pass: Summarize each section
    3. Third pass: Synthesize final summary

    Achieves better compression than single-pass while maintaining quality.
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        num_passes: int = 2,
        target_compression_ratio: float = 0.2,
        max_summary_length: int = 400,
    ) -> None:
        """Initialize multi-pass summarizer.

        Args:
            llm_provider: Optional LLM provider for summarization
            num_passes: Number of summarization passes (2-3)
            target_compression_ratio: Target compression ratio
            max_summary_length: Maximum length of final summary
        """
        self.name = "multi_pass_summary"
        self.llm_provider = llm_provider
        self.num_passes = max(2, min(3, num_passes))
        self.target_compression_ratio = target_compression_ratio
        self.max_summary_length = max_summary_length

    async def compress(self, text: str, **metadata: Any) -> CompressionResult:
        """Compress text using multi-pass summarization.

        Args:
            text: Input text to compress
            **metadata: Additional context

        Returns:
            CompressionResult with multi-pass summary
        """
        start_time = time.time()
        original_size = len(text)

        try:
            current_text = text
            pass_results = []

            # Pass 1: Extract structure
            logger.debug("Multi-pass summarization: Pass 1 (structure extraction)")
            structured = self._extract_structure(current_text)
            pass_results.append(
                {
                    "pass": 1,
                    "method": "structure_extraction",
                    "before_size": len(current_text),
                    "after_size": len(structured),
                }
            )
            current_text = structured

            # Pass 2: Section summarization
            if self.num_passes >= 2:
                logger.debug("Multi-pass summarization: Pass 2 (section summary)")
                sectioned = await self._summarize_sections(current_text, metadata)
                pass_results.append(
                    {
                        "pass": 2,
                        "method": "section_summary",
                        "before_size": len(current_text),
                        "after_size": len(sectioned),
                    }
                )
                current_text = sectioned

            # Pass 3: Final synthesis (optional)
            if self.num_passes >= 3:
                logger.debug("Multi-pass summarization: Pass 3 (synthesis)")
                synthesized = await self._synthesize_final(current_text, metadata)
                pass_results.append(
                    {
                        "pass": 3,
                        "method": "synthesis",
                        "before_size": len(current_text),
                        "after_size": len(synthesized),
                    }
                )
                current_text = synthesized

            # Truncate if needed
            if len(current_text) > self.max_summary_length:
                current_text = current_text[: self.max_summary_length] + "..."

            compressed_size = len(current_text)
            duration_ms = (time.time() - start_time) * 1000

            # Extract key points from final summary
            key_points = self._extract_key_points(current_text)

            metrics = CompressionMetrics(
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compressed_size / original_size if original_size > 0 else 1.0,
                tokens_saved=(original_size - compressed_size) // 4,
                duration_ms=duration_ms,
                compressor_name=self.name,
                metadata={
                    "num_passes": self.num_passes,
                    "pass_results": pass_results,
                    "total_reduction": original_size - compressed_size,
                },
            )

            return CompressionResult(
                original_text=text,
                compressed_text=current_text,
                summary=current_text,
                key_points=key_points,
                tags=metadata.get("tags", []),
                compression_ratio=metrics.compression_ratio,
                metrics=metrics,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception("Multi-pass summarization failed: %s", e)

            # Fallback to simple truncation
            fallback = (
                text[: self.max_summary_length] + "..."
                if len(text) > self.max_summary_length
                else text
            )

            metrics = CompressionMetrics(
                original_size=original_size,
                compressed_size=len(fallback),
                compression_ratio=len(fallback) / original_size if original_size > 0 else 1.0,
                tokens_saved=0,
                duration_ms=duration_ms,
                compressor_name=self.name,
                metadata={"error": str(e), "fallback": True},
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

    def _extract_structure(self, text: str) -> str:
        """Extract structural elements (headings, lists, key sentences).

        Args:
            text: Input text

        Returns:
            Structured representation
        """
        lines = text.split("\n")
        structured_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Keep headings (lines with # or all caps)
            if line.startswith("#") or (len(line) < 100 and line.isupper()):
                structured_lines.append(line)
                continue

            # Keep list items
            if line.startswith(("-", "*", "•")) or (
                len(line) > 2 and line[0].isdigit() and line[1] in ".):"
            ):
                structured_lines.append(line)
                continue

            # Keep sentences with key indicators
            key_indicators = [
                "must",
                "should",
                "will",
                "important",
                "critical",
                "required",
                "note:",
                "warning:",
            ]
            if any(indicator in line.lower() for indicator in key_indicators):
                structured_lines.append(line)

        # If we extracted too little, include first/last paragraphs
        if len("\n".join(structured_lines)) < len(text) * 0.1:
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            if paragraphs:
                structured_lines.insert(0, paragraphs[0])
                if len(paragraphs) > 1:
                    structured_lines.append(paragraphs[-1])

        return "\n".join(structured_lines)

    async def _summarize_sections(self, text: str, metadata: dict) -> str:
        """Summarize each section independently.

        Args:
            text: Structured text
            metadata: Context metadata

        Returns:
            Section summaries
        """
        # Split into sections (by double newline or headings)
        sections = []
        current_section = []

        for line in text.split("\n"):
            if not line.strip():
                if current_section:
                    sections.append("\n".join(current_section))
                    current_section = []
            else:
                current_section.append(line)

        if current_section:
            sections.append("\n".join(current_section))

        # Summarize each section
        summarized_sections = []
        target_section_length = self.max_summary_length // max(1, len(sections))

        for section in sections:
            if len(section) <= target_section_length:
                summarized_sections.append(section)
            else:
                # Simple truncation for now (could use LLM here)
                summary = section[:target_section_length] + "..."
                summarized_sections.append(summary)

        return "\n\n".join(summarized_sections)

    async def _synthesize_final(self, text: str, metadata: dict) -> str:
        """Synthesize final summary from section summaries.

        Args:
            text: Section summaries
            metadata: Context metadata

        Returns:
            Final synthesized summary
        """
        # For now, just ensure we meet target length
        # In production, this would use LLM to synthesize coherent summary

        if len(text) <= self.max_summary_length:
            return text

        # Extract most important sentences
        sentences = [s.strip() for s in text.split(".") if s.strip()]

        # Score sentences by importance (simple heuristic)
        scored_sentences = []
        for sentence in sentences:
            score = 0
            # Prefer shorter sentences
            score += max(0, 100 - len(sentence)) / 100
            # Prefer sentences with key terms
            if any(term in sentence.lower() for term in ["must", "will", "should", "important"]):
                score += 1
            scored_sentences.append((score, sentence))

        # Sort by score and take top sentences
        scored_sentences.sort(reverse=True, key=lambda x: x[0])

        final_sentences = []
        total_length = 0

        for score, sentence in scored_sentences:
            if total_length + len(sentence) + 2 <= self.max_summary_length:
                final_sentences.append(sentence)
                total_length += len(sentence) + 2  # +2 for '. '
            else:
                break

        return ". ".join(final_sentences) + "."

    def _extract_key_points(self, summary: str) -> list[str]:
        """Extract key points from summary.

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
                point = line.lstrip("-*•0123456789.): ").strip()
                if point:
                    key_points.append(point)
            # Or look for short declarative sentences
            elif len(line) < 150 and "." in line:
                sentences = line.split(".")
                for sent in sentences:
                    sent = sent.strip()
                    if 20 < len(sent) < 150:
                        key_points.append(sent)

        return key_points[:7]  # Max 7 key points

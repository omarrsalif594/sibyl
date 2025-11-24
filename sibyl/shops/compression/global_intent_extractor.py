"""Global intent extraction compressor.

Extracts high-level user intent from long prompts, discarding
implementation details while preserving the core request.
"""

import logging
import re
import time
from typing import Any

from sibyl.core.compression import CompressionMetrics, CompressionResult

logger = logging.getLogger(__name__)


class GlobalIntentExtractor:
    """Extract global user intent from prompts.

    This compressor focuses on:
    - Identifying the user's primary goal
    - Extracting key constraints and requirements
    - Removing verbose examples and explanations
    - Preserving critical context

    Ideal for first-stage compression before more detailed summarization.
    """

    def __init__(
        self,
        extract_constraints: bool = True,
        extract_examples: bool = False,
        max_intent_length: int = 300,
    ) -> None:
        """Initialize global intent extractor.

        Args:
            extract_constraints: Include constraints in intent
            extract_examples: Include key examples (default: remove them)
            max_intent_length: Maximum length of extracted intent
        """
        self.name = "global_intent_extractor"
        self.extract_constraints = extract_constraints
        self.extract_examples = extract_examples
        self.max_intent_length = max_intent_length

    async def compress(self, text: str, **metadata: Any) -> CompressionResult:
        """Extract global intent from text.

        Args:
            text: Input text to compress
            **metadata: Additional context

        Returns:
            CompressionResult with extracted intent
        """
        start_time = time.time()
        original_size = len(text)

        try:
            # Extract components
            intent = self._extract_primary_intent(text)
            constraints = self._extract_constraints(text) if self.extract_constraints else []
            examples = self._extract_examples(text) if self.extract_examples else []
            tags = self._extract_tags(text)

            # Build compressed representation
            compressed_parts = [f"Intent: {intent}"]

            if constraints:
                compressed_parts.append(f"Constraints: {', '.join(constraints)}")

            if examples:
                compressed_parts.append(f"Examples: {', '.join(examples[:2])}")  # Max 2 examples

            compressed = "\n".join(compressed_parts)

            # Truncate if needed
            if len(compressed) > self.max_intent_length:
                compressed = compressed[: self.max_intent_length] + "..."

            compressed_size = len(compressed)
            duration_ms = (time.time() - start_time) * 1000

            metrics = CompressionMetrics(
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compressed_size / original_size if original_size > 0 else 1.0,
                tokens_saved=(original_size - compressed_size) // 4,
                duration_ms=duration_ms,
                compressor_name=self.name,
                metadata={
                    "intent_length": len(intent),
                    "num_constraints": len(constraints),
                    "num_examples": len(examples),
                    "num_tags": len(tags),
                },
            )

            key_points = [intent] + constraints[:3]  # Intent + top 3 constraints

            return CompressionResult(
                original_text=text,
                compressed_text=compressed,
                summary=compressed,
                key_points=key_points,
                tags=tags,
                compression_ratio=metrics.compression_ratio,
                metrics=metrics,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception("Intent extraction failed: %s", e)

            # Fallback: use first N characters
            fallback = (
                text[: self.max_intent_length] + "..."
                if len(text) > self.max_intent_length
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

    def _extract_primary_intent(self, text: str) -> str:
        """Extract primary user intent.

        Looks for imperative sentences and questions at the beginning.

        Args:
            text: Input text

        Returns:
            Primary intent statement
        """
        # Split into sentences
        sentences = re.split(r"[.!?]+", text)

        # Look for imperative/question sentences in first few sentences
        for sentence in sentences[:5]:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if it's a question
            if "?" in sentence or any(
                sentence.lower().startswith(q)
                for q in ["what", "how", "why", "when", "where", "who", "which"]
            ):
                return sentence

            # Check if it's an imperative (starts with verb)
            imperative_verbs = [
                "create",
                "build",
                "implement",
                "write",
                "generate",
                "design",
                "develop",
                "add",
                "update",
                "fix",
                "refactor",
                "analyze",
                "explain",
                "summarize",
            ]
            if any(sentence.lower().startswith(verb) for verb in imperative_verbs):
                return sentence

        # Fallback: return first non-empty sentence
        for sentence in sentences[:3]:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:
                return sentence

        # Last resort: first 100 chars
        return text[:100].strip()

    def _extract_constraints(self, text: str) -> list[str]:
        """Extract constraints and requirements.

        Looks for patterns like "must", "should", "need to", etc.

        Args:
            text: Input text

        Returns:
            List of constraints
        """
        constraints = []

        # Pattern matching for constraints
        constraint_patterns = [
            r"must\s+([^.!?]+)",
            r"should\s+([^.!?]+)",
            r"need(?:s)?\s+to\s+([^.!?]+)",
            r"required?\s+([^.!?]+)",
            r"ensure\s+([^.!?]+)",
        ]

        for pattern in constraint_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                constraint = match.group(0).strip()
                if constraint and len(constraint) < 100:  # Skip very long matches
                    constraints.append(constraint)

        return constraints[:5]  # Max 5 constraints

    def _extract_examples(self, text: str) -> list[str]:
        """Extract key examples.

        Looks for phrases like "for example", "e.g.", "such as".

        Args:
            text: Input text

        Returns:
            List of examples
        """
        examples = []

        # Pattern matching for examples
        example_patterns = [
            r"for example[,:]\s*([^.!?]+)",
            r"e\.g\.[,:]\s*([^.!?]+)",
            r"such as\s+([^.!?]+)",
            r"example:\s*([^.!?]+)",
        ]

        for pattern in example_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                example = match.group(1).strip()
                if example and len(example) < 80:
                    examples.append(example)

        return examples[:3]  # Max 3 examples

    def _extract_tags(self, text: str) -> list[str]:
        """Extract topic tags from text.

        Identifies key technical terms and topics.

        Args:
            text: Input text

        Returns:
            List of tags
        """
        tags = set()

        # Common technical domains
        domain_keywords = {
            "api",
            "database",
            "frontend",
            "backend",
            "testing",
            "deployment",
            "authentication",
            "authorization",
            "caching",
            "routing",
            "validation",
            "compression",
            "optimization",
            "refactoring",
            "debugging",
            "monitoring",
            "logging",
            "security",
            "performance",
            "scalability",
            "architecture",
        }

        # Find domain keywords
        text_lower = text.lower()
        for keyword in domain_keywords:
            if keyword in text_lower:
                tags.add(keyword)

        # Programming languages
        languages = ["python", "javascript", "typescript", "java", "go", "rust", "c++", "sql"]
        for lang in languages:
            if lang in text_lower:
                tags.add(lang)

        return sorted(tags)[:10]  # Max 10 tags

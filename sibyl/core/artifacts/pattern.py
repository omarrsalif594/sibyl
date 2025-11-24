"""Pattern Artifact for learned code patterns from In-Memoria.

This module provides typed artifacts for code patterns learned by In-Memoria MCP.
It enables tracking of coding conventions, architectural patterns, and naming patterns
with confidence scores and frequency analysis.

Example:
    from sibyl.core.artifacts.pattern import PatternArtifact, PatternCategory

    # Create from In-Memoria response
    pattern = PatternArtifact.from_mcp_response(
        response={"pattern": "use_snake_case", "confidence": 0.95, ...},
        provider="in_memoria"
    )

    # Check pattern strength
    if pattern.is_high_confidence():
        print(f"Strong pattern: {pattern.pattern_name}")
        print(f"Found in {len(pattern.similar_files)} files")
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PatternCategory(Enum):
    """Categories of code patterns that can be learned.

    These categories cover the main types of patterns that In-Memoria
    and other pattern-detection tools can identify in codebases.
    """

    NAMING = "naming"  # Naming conventions (snake_case, camelCase, etc.)
    ARCHITECTURAL = "architectural"  # Architectural patterns (MVC, layered, etc.)
    CODING_CONVENTION = "coding_convention"  # Coding conventions (imports, formatting, etc.)
    API_USAGE = "api_usage"  # Common API usage patterns
    ERROR_HANDLING = "error_handling"  # Error handling patterns
    TESTING = "testing"  # Testing patterns
    DOCUMENTATION = "documentation"  # Documentation patterns
    OTHER = "other"  # Uncategorized patterns


@dataclass
class PatternArtifact:
    """Artifact for learned code patterns.

    This artifact represents a code pattern learned from analyzing a codebase,
    typically produced by In-Memoria MCP. It includes confidence metrics,
    examples, and frequency information.

    Attributes:
        pattern_name: Human-readable pattern name (e.g., "use_snake_case", "import_logging_first")
        category: Pattern category (naming, architectural, etc.)
        confidence: Confidence score (0.0 to 1.0) - how certain the system is about this pattern
        description: Human-readable description of the pattern
        code_examples: List of code snippets demonstrating the pattern
        similar_files: List of file paths where this pattern was observed
        frequency: Number of times this pattern was observed
        learned_at: Timestamp when the pattern was learned
        metadata: Additional pattern metadata (language, context, etc.)

    Example:
        pattern = PatternArtifact(
            pattern_name="use_snake_case",
            category=PatternCategory.NAMING,
            confidence=0.95,
            description="Function names use snake_case convention",
            code_examples=["def calculate_total():", "def parse_input():"],
            similar_files=["src/utils.py", "src/helpers.py"],
            frequency=42,
            learned_at=datetime.now(),
            metadata={"language": "python"}
        )

        if pattern.is_high_confidence():
            print(f"Strong pattern with {pattern.frequency} occurrences")
    """

    pattern_name: str
    category: PatternCategory
    confidence: float
    description: str
    code_examples: list[str] = field(default_factory=list)
    similar_files: list[str] = field(default_factory=list)
    frequency: int = 1
    learned_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set learned_at to now if not provided."""
        if self.learned_at is None:
            self.learned_at = datetime.now()

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if pattern has high confidence.

        Args:
            threshold: Confidence threshold (default 0.8)

        Returns:
            True if confidence >= threshold

        Example:
            if pattern.is_high_confidence():
                apply_pattern_to_codebase(pattern)
        """
        return self.confidence >= threshold

    def is_frequent(self, min_frequency: int = 10) -> bool:
        """Check if pattern is frequently observed.

        Args:
            min_frequency: Minimum frequency threshold (default 10)

        Returns:
            True if frequency >= min_frequency

        Example:
            if pattern.is_frequent(min_frequency=20):
                print("This pattern is widely used")
        """
        return self.frequency >= min_frequency

    def get_top_examples(self, n: int = 3) -> list[str]:
        """Get top N code examples.

        Args:
            n: Number of examples to return (default 3)

        Returns:
            List of up to n code examples

        Example:
            examples = pattern.get_top_examples(n=5)
            for example in examples:
                print(example)
        """
        return self.code_examples[:n]

    def summarize_for_llm(self, max_examples: int = 3) -> str:
        """Generate LLM-friendly summary of the pattern.

        Creates a concise text summary suitable for inclusion in LLM prompts,
        including pattern description, confidence, frequency, and examples.

        Args:
            max_examples: Maximum number of code examples to include

        Returns:
            Formatted string summary

        Example:
            summary = pattern.summarize_for_llm(max_examples=2)
            llm_prompt = f"Based on these patterns:\\n{summary}\\nSuggest improvements..."
        """
        lines = [
            f"Pattern: {self.pattern_name}",
            f"Category: {self.category.value}",
            f"Confidence: {self.confidence:.2%}",
            f"Frequency: {self.frequency} occurrences in {len(self.similar_files)} files",
            f"Description: {self.description}",
        ]

        if self.code_examples:
            examples = self.get_top_examples(max_examples)
            lines.append("Examples:")
            for i, example in enumerate(examples, 1):
                # Truncate long examples
                example_text = example[:100] + "..." if len(example) > 100 else example
                lines.append(f"  {i}. {example_text}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize artifact to dictionary.

        Returns:
            Dictionary representation of the artifact

        Example:
            data = pattern.to_dict()
            json.dumps(data, default=str)
        """
        return {
            "pattern_name": self.pattern_name,
            "category": self.category.value,
            "confidence": self.confidence,
            "description": self.description,
            "code_examples": self.code_examples,
            "similar_files": self.similar_files,
            "frequency": self.frequency,
            "learned_at": self.learned_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_mcp_response(
        cls, response: dict[str, Any], provider: str = "in_memoria"
    ) -> "PatternArtifact":
        """Create PatternArtifact from MCP response.

        This factory method handles various response formats from pattern-detection
        MCP tools like In-Memoria, normalizing them to a standard artifact structure.

        Args:
            response: Raw response dictionary from MCP pattern detection tool
            provider: Pattern detection provider name (default "in_memoria")

        Returns:
            PatternArtifact instance

        Example:
            # From In-Memoria
            mcp_result = await mcp_adapter(
                provider="in_memoria",
                tool="detect_patterns",
                params={"directory": "src/"}
            )

            # Response might contain a list of patterns
            patterns = []
            for pattern_data in mcp_result.get("patterns", [mcp_result]):
                pattern = PatternArtifact.from_mcp_response(
                    pattern_data,
                    provider="in_memoria"
                )
                patterns.append(pattern)

        Note:
            Expected response format:
            {
                "pattern": "use_snake_case",
                "category": "naming",
                "confidence": 0.95,
                "description": "Function names use snake_case",
                "examples": ["def foo_bar():", "def baz_qux():"],
                "files": ["src/a.py", "src/b.py"],
                "frequency": 42
            }
        """
        # Extract pattern name
        pattern_name = response.get("pattern", response.get("name", "unknown_pattern"))

        # Parse category with fallback
        category_str = response.get("category", response.get("type", "other")).lower()
        category_mapping = {
            "naming": PatternCategory.NAMING,
            "architectural": PatternCategory.ARCHITECTURAL,
            "architecture": PatternCategory.ARCHITECTURAL,
            "coding_convention": PatternCategory.CODING_CONVENTION,
            "convention": PatternCategory.CODING_CONVENTION,
            "api_usage": PatternCategory.API_USAGE,
            "api": PatternCategory.API_USAGE,
            "error_handling": PatternCategory.ERROR_HANDLING,
            "error": PatternCategory.ERROR_HANDLING,
            "testing": PatternCategory.TESTING,
            "test": PatternCategory.TESTING,
            "documentation": PatternCategory.DOCUMENTATION,
            "docs": PatternCategory.DOCUMENTATION,
            "other": PatternCategory.OTHER,
        }
        category = category_mapping.get(category_str, PatternCategory.OTHER)

        # Parse confidence (0.0 to 1.0)
        confidence = float(response.get("confidence", response.get("score", 1.0)))
        # Normalize if confidence is out of range
        if confidence > 1.0:
            confidence = confidence / 100.0  # Assume percentage
        confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]

        # Extract description
        description = response.get(
            "description", response.get("summary", f"Pattern: {pattern_name}")
        )

        # Extract code examples
        code_examples = response.get("examples", response.get("code_examples", []))
        if not isinstance(code_examples, list):
            code_examples = [str(code_examples)] if code_examples else []

        # Extract similar files
        similar_files = response.get("files", response.get("similar_files", []))
        if not isinstance(similar_files, list):
            similar_files = []

        # Extract frequency
        frequency = int(response.get("frequency", response.get("count", len(code_examples))))

        # Parse timestamp
        learned_at = datetime.now()
        if "learned_at" in response or "timestamp" in response:
            ts_str = response.get("learned_at", response.get("timestamp"))
            if ts_str:
                try:
                    learned_at = datetime.fromisoformat(str(ts_str))
                except (ValueError, TypeError):
                    pass  # Use default

        # Extract metadata
        metadata = {
            "provider": provider,
        }
        # Include language if present
        if "language" in response:
            metadata["language"] = response["language"]
        # Include context if present
        if "context" in response:
            metadata["context"] = response["context"]
        # Include any additional fields not already captured
        for key in ["project", "repository", "version", "tags"]:
            if key in response:
                metadata[key] = response[key]

        return cls(
            pattern_name=pattern_name,
            category=category,
            confidence=confidence,
            description=description,
            code_examples=code_examples,
            similar_files=similar_files,
            frequency=frequency,
            learned_at=learned_at,
            metadata=metadata,
        )

"""
Core protocols for code processing in RAG pipelines.

This module defines the fundamental types and protocols for processing code:
- CodeType: Enumeration of supported code types
- Chunk: Data structure for code chunks
- Plugin protocols: CodeChunker, CodeValidator, ComplexityScorer

These are pure protocol definitions with no runtime logic or registry behavior.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class CodeType(str, Enum):
    """Supported code types for processing."""

    SQL = "sql"
    TEXT = "text"
    MARKDOWN = "markdown"
    PYTHON = "python"
    YAML = "yaml"


@dataclass
class Chunk:
    """
    Represents a chunk of code with metadata.

    This is a simple, AST-free representation that works across
    all code types. Plugins can add domain-specific metadata.
    """

    chunk_id: str
    content: str
    metadata: dict[str, Any]  # e.g. {"code_type": "sql", "source": "ExampleDomain"}
    start_line: int | None = None
    end_line: int | None = None
    description: str | None = None


class CodeChunker(Protocol):
    """
    Protocol for code chunking plugins.

    Implementations split code into logical chunks based on the code type.
    """

    def supports(self, code_type: CodeType) -> bool:
        """Check if this chunker supports the given code type."""
        ...

    def chunk(self, code: str, code_type: CodeType, **opts) -> list[Chunk]:
        """
        Split code into chunks.

        Args:
            code: The code to chunk
            code_type: Type of code being chunked
            **opts: Additional options (chunker-specific)

        Returns:
            List of Chunk objects
        """
        ...


class CodeValidator(Protocol):
    """
    Protocol for code validation plugins.

    Implementations perform domain-specific validation checks.
    """

    def supports(self, code_type: CodeType) -> bool:
        """Check if this validator supports the given code type."""
        ...

    def validate(self, code: str, code_type: CodeType, **opts) -> dict[str, Any]:
        """
        Validate code and return results.

        Args:
            code: The code to validate
            code_type: Type of code being validated
            **opts: Additional options (validator-specific)

        Returns:
            Dictionary with keys:
            - ok: bool indicating if validation passed
            - issues: List of issue dicts with "message" and "severity"
        """
        ...


class ComplexityScorer(Protocol):
    """
    Protocol for complexity scoring plugins.

    Implementations assess code complexity using domain-specific heuristics.
    """

    def supports(self, code_type: CodeType) -> bool:
        """Check if this scorer supports the given code type."""
        ...

    def score(self, code: str, code_type: CodeType, **opts) -> dict[str, Any]:
        """
        Score code complexity.

        Args:
            code: The code to score
            code_type: Type of code being scored
            **opts: Additional options (scorer-specific)

        Returns:
            Dictionary with keys:
            - level: "low" | "medium" | "high"
            - metrics: Dict of specific measurements
        """
        ...


__all__ = [
    "Chunk",
    "CodeChunker",
    "CodeType",
    "CodeValidator",
    "ComplexityScorer",
]

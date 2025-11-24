"""Compression result artifacts.

Defines the standard output format for compression operations.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompressionMetrics:
    """Metrics from compression operation.

    Attributes:
        original_size: Size of original text in characters
        compressed_size: Size of compressed text in characters
        compression_ratio: Ratio of compressed to original (lower is better)
        tokens_saved: Estimated tokens saved (if available)
        duration_ms: Time taken for compression in milliseconds
        compressor_name: Name of compressor used
        metadata: Additional compressor-specific metrics
    """

    original_size: int
    compressed_size: int
    compression_ratio: float
    tokens_saved: int
    duration_ms: float
    compressor_name: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def bytes_saved(self) -> int:
        """Calculate bytes saved by compression."""
        return self.original_size - self.compressed_size

    @property
    def space_saved_percent(self) -> float:
        """Calculate percentage of space saved."""
        if self.original_size == 0:
            return 0.0
        return (1 - self.compression_ratio) * 100


@dataclass
class CompressionResult:
    """Result of compression operation.

    Attributes:
        original_text: Original uncompressed text
        compressed_text: Compressed text
        summary: Human-readable summary (may be same as compressed_text)
        key_points: List of key points extracted (if applicable)
        tags: List of tags/topics identified (if applicable)
        compression_ratio: Ratio of compressed to original size
        metrics: Detailed compression metrics
        error: Error message if compression failed
    """

    original_text: str
    compressed_text: str
    summary: str
    key_points: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    compression_ratio: float = 1.0
    metrics: CompressionMetrics | None = None
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if compression was successful."""
        return self.error is None

    @property
    def effective_compression(self) -> bool:
        """Check if compression actually reduced size."""
        return self.compression_ratio < 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "original_text": self.original_text,
            "compressed_text": self.compressed_text,
            "summary": self.summary,
            "key_points": self.key_points,
            "tags": self.tags,
            "compression_ratio": self.compression_ratio,
            "metrics": {
                "original_size": self.metrics.original_size
                if self.metrics
                else len(self.original_text),
                "compressed_size": self.metrics.compressed_size
                if self.metrics
                else len(self.compressed_text),
                "compression_ratio": self.compression_ratio,
                "tokens_saved": self.metrics.tokens_saved if self.metrics else 0,
                "duration_ms": self.metrics.duration_ms if self.metrics else 0,
                "compressor_name": self.metrics.compressor_name if self.metrics else "unknown",
                "bytes_saved": self.metrics.bytes_saved if self.metrics else 0,
                "space_saved_percent": self.metrics.space_saved_percent if self.metrics else 0,
                "metadata": self.metrics.metadata if self.metrics else {},
            }
            if self.metrics
            else None,
            "error": self.error,
            "success": self.success,
            "effective_compression": self.effective_compression,
        }

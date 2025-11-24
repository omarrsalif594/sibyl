"""Compression protocol interfaces.

Defines the standard interface for compressors and compression chains.
"""

from typing import Any, Protocol

from .artifacts import CompressionResult


class Compressor(Protocol):
    """Protocol for text compression implementations.

    All compressors must implement this interface to be usable in
    compression chains and routing pipelines.

    Attributes:
        name: Unique identifier for this compressor
    """

    name: str

    async def compress(self, text: str, **metadata: Any) -> CompressionResult:
        """Compress input text.

        Args:
            text: Input text to compress
            **metadata: Additional context (e.g., user_intent, domain, etc.)

        Returns:
            CompressionResult with compressed text and metrics

        Raises:
            CompressionError: If compression fails
        """
        ...


class CompressionChain:
    """Chain multiple compressors in sequence.

    Applies compressors in order, passing output of each as input to the next.
    Accumulates metrics from all stages.

    Example:
        chain = CompressionChain([
            GlobalIntentExtractor(),
            MultiPassSummary(),
        ])
        result = await chain.compress(long_prompt)
    """

    def __init__(self, compressors: list[Compressor]) -> None:
        """Initialize compression chain.

        Args:
            compressors: List of compressors to apply in sequence
        """
        self.compressors = compressors
        self.name = "chain:" + ",".join(c.name for c in compressors)

    async def compress(self, text: str, **metadata: Any) -> CompressionResult:
        """Apply compression chain.

        Args:
            text: Input text
            **metadata: Additional context

        Returns:
            CompressionResult from final stage with accumulated metrics
        """
        current_text = text
        original_size = len(text)
        stages = []

        for compressor in self.compressors:
            result = await compressor.compress(current_text, **metadata)
            current_text = result.compressed_text
            stages.append(
                {
                    "compressor": compressor.name,
                    "input_size": len(result.original_text),
                    "output_size": len(result.compressed_text),
                    "compression_ratio": result.compression_ratio,
                    "duration_ms": result.duration_ms,
                }
            )

        # Build final result with accumulated metrics
        from .artifacts import CompressionMetrics, CompressionResult

        final_metrics = CompressionMetrics(
            original_size=original_size,
            compressed_size=len(current_text),
            compression_ratio=len(current_text) / original_size if original_size > 0 else 1.0,
            tokens_saved=0,  # Will be computed if token counter available
            duration_ms=sum(s["duration_ms"] for s in stages),
            compressor_name=self.name,
            metadata={
                "stages": stages,
                "num_stages": len(stages),
            },
        )

        return CompressionResult(
            original_text=text,
            compressed_text=current_text,
            summary=current_text,
            key_points=[],  # Chain doesn't extract key points itself
            tags=[],
            compression_ratio=final_metrics.compression_ratio,
            metrics=final_metrics,
        )

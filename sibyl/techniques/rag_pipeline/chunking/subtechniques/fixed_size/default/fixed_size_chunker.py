"""
Fixed Size Chunking Subtechnique

This module provides fixed-size chunking that splits text into chunks
of a specified size with optional overlap.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FixedSizeChunking:
    """
    Fixed-size chunking implementation.

    This subtechnique chunks text into fixed-size pieces with configurable
    overlap and boundary handling.
    """

    def __init__(self) -> None:
        """Initialize fixed-size chunking."""
        self._name = "fixed_size"
        self._description = "Chunk into fixed-size pieces with overlap"
        self._config_path = Path(__file__).parent / "config.yaml"

    @property
    def name(self) -> str:
        """Get subtechnique name."""
        return self._name

    @property
    def description(self) -> str:
        """Get subtechnique description."""
        return self._description

    def execute(self, input_data: Any, config: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Execute fixed-size chunking.

        Args:
            input_data: Text or code to chunk (string or dict with 'content' key)
            config: Merged configuration

        Returns:
            List of chunk dictionaries with content and metadata

        Raises:
            ValueError: If input_data is invalid
        """
        # Extract content
        if isinstance(input_data, str):
            content = input_data
            metadata = {}
        elif isinstance(input_data, dict):
            content = input_data.get("content", "")
            metadata = {k: v for k, v in input_data.items() if k != "content"}
        else:
            msg = f"Invalid input_data type: {type(input_data)}"
            raise TypeError(msg)

        if not content:
            return []

        # Get configuration
        chunk_size = config.get("chunk_size", 512)
        overlap = config.get("overlap", 50)
        split_on_whitespace = config.get("split_on_whitespace", True)
        respect_word_boundaries = config.get("respect_word_boundaries", True)

        logger.debug(
            f"Fixed-size chunking: size={chunk_size}, overlap={overlap}, "
            f"whitespace={split_on_whitespace}"
        )

        # Perform chunking
        if respect_word_boundaries and split_on_whitespace:
            chunks = self._chunk_by_words(content, chunk_size, overlap, metadata)
        else:
            chunks = self._chunk_by_characters(content, chunk_size, overlap, metadata)

        logger.info("Created %s fixed-size chunks", len(chunks))
        return chunks

    def _chunk_by_characters(
        self, text: str, chunk_size: int, overlap: int, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Chunk by character count.

        Args:
            text: Input text
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks in characters
            metadata: Base metadata for chunks

        Returns:
            List of chunks
        """
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + chunk_size
            chunk_content = text[start:end]

            # Calculate line numbers (approximate)
            lines_before = text[:start].count("\n")
            lines_in_chunk = chunk_content.count("\n")

            chunks.append(
                self._create_chunk(
                    chunk_content,
                    chunk_index,
                    lines_before + 1,
                    lines_before + lines_in_chunk + 1,
                    metadata,
                )
            )

            chunk_index += 1
            start += chunk_size - overlap

        return chunks

    def _chunk_by_words(
        self, text: str, chunk_size: int, overlap: int, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Chunk by word count, respecting word boundaries.

        Args:
            text: Input text
            chunk_size: Approximate size of each chunk in characters
            overlap: Overlap between chunks in characters
            metadata: Base metadata for chunks

        Returns:
            List of chunks
        """
        chunks = []
        words = text.split()
        current_chunk = []
        current_size = 0
        chunk_index = 0
        start_line = 1
        current_line = 1

        for word in words:
            word_size = len(word) + 1  # +1 for space

            # Check if adding this word would exceed chunk size
            if current_size + word_size > chunk_size and current_chunk:
                # Finalize current chunk
                chunk_content = " ".join(current_chunk)
                chunks.append(
                    self._create_chunk(
                        chunk_content, chunk_index, start_line, current_line, metadata
                    )
                )

                # Calculate overlap
                if overlap > 0:
                    # Keep last few words for overlap
                    overlap_words = []
                    overlap_size = 0
                    for w in reversed(current_chunk):
                        if overlap_size + len(w) + 1 <= overlap:
                            overlap_words.insert(0, w)
                            overlap_size += len(w) + 1
                        else:
                            break

                    current_chunk = [*overlap_words, word]
                    current_size = overlap_size + word_size
                else:
                    current_chunk = [word]
                    current_size = word_size

                chunk_index += 1
                start_line = current_line
            else:
                # Add to current chunk
                current_chunk.append(word)
                current_size += word_size

            # Update line count
            current_line += word.count("\n")

        # Finalize last chunk if it exists
        if current_chunk:
            chunk_content = " ".join(current_chunk)
            chunks.append(
                self._create_chunk(chunk_content, chunk_index, start_line, current_line, metadata)
            )

        return chunks

    def _create_chunk(
        self,
        content: str,
        index: int,
        start_line: int,
        end_line: int,
        base_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create a chunk dictionary.

        Args:
            content: Chunk content
            index: Chunk index
            start_line: Starting line number
            end_line: Ending line number
            base_metadata: Base metadata to include

        Returns:
            Chunk dictionary
        """
        chunk_id = hashlib.sha256(f"{content[:100]}_{index}".encode()).hexdigest()[:16]

        return {
            "chunk_id": chunk_id,
            "content": content,
            "start_line": start_line,
            "end_line": end_line,
            "metadata": {
                **base_metadata,
                "chunk_type": "fixed_size",
                "chunk_index": index,
                "subtechnique": self.name,
            },
        }

    def get_config(self) -> dict[str, Any]:
        """
        Get default configuration for this subtechnique.

        Returns:
            Default configuration
        """
        import yaml

        if self._config_path.exists():
            with open(self._config_path) as f:
                config = yaml.safe_load(f)
                return config if config is not None else {}
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        chunk_size = config.get("chunk_size")
        if chunk_size is not None and chunk_size <= 0:
            msg = f"chunk_size must be positive, got {chunk_size}"
            raise ValueError(msg)

        overlap = config.get("overlap")
        if overlap is not None:
            if overlap < 0:
                msg = f"overlap must be non-negative, got {overlap}"
                raise ValueError(msg)

            if chunk_size is not None and overlap >= chunk_size:
                msg = f"overlap ({overlap}) must be less than chunk_size ({chunk_size})"
                raise ValueError(msg)

        return True

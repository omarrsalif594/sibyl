"""
Semantic Chunking Subtechnique

This module provides semantic-based chunking that groups related content
based on semantic similarity.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SemanticChunking:
    """
    Semantic-based chunking implementation.

    This subtechnique chunks text based on semantic similarity,
    creating chunks that group semantically related content together.
    """

    def __init__(self) -> None:
        """Initialize semantic chunking."""
        self._name = "semantic"
        self._description = "Chunk based on semantic similarity"
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
        Execute semantic chunking.

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
        similarity_threshold = config.get("similarity_threshold", 0.7)
        min_cluster_size = config.get("min_cluster_size", 50)
        max_cluster_size = config.get("max_cluster_size", 1500)
        use_sentence_boundaries = config.get("use_sentence_boundaries", True)

        logger.debug(
            f"Semantic chunking: threshold={similarity_threshold}, "
            f"min={min_cluster_size}, max={max_cluster_size}"
        )

        # Split into sentences if configured
        sentences = self._split_into_sentences(content) if use_sentence_boundaries else [content]

        # For now, implement a simple version
        # In production, this would use embeddings and similarity calculation
        chunks = self._simple_semantic_chunking(
            sentences, min_cluster_size, max_cluster_size, metadata
        )

        logger.info("Created %s semantic chunks", len(chunks))
        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved with NLP)
        import re  # can be moved to top

        # Split on sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _simple_semantic_chunking(
        self, sentences: list[str], min_size: int, max_size: int, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Simple semantic chunking implementation.

        This is a placeholder that groups sentences into chunks of appropriate size.
        In production, this would use embeddings and semantic similarity.

        Args:
            sentences: List of sentences
            min_size: Minimum chunk size
            max_size: Maximum chunk size
            metadata: Base metadata for chunks

        Returns:
            List of chunks
        """
        chunks = []
        current_chunk = []
        current_size = 0
        start_line = 1
        current_line = 1

        for sentence in sentences:
            sentence_size = len(sentence)

            # Check if adding this sentence would exceed max size
            if current_size + sentence_size > max_size and current_size >= min_size:
                # Finalize current chunk
                chunk_content = " ".join(current_chunk)
                chunks.append(
                    self._create_chunk(
                        chunk_content, len(chunks), start_line, current_line - 1, metadata
                    )
                )

                # Start new chunk
                current_chunk = [sentence]
                current_size = sentence_size
                start_line = current_line
            else:
                # Add to current chunk
                current_chunk.append(sentence)
                current_size += sentence_size

            current_line += sentence.count("\n") + 1

        # Finalize last chunk if it exists
        if current_chunk:
            chunk_content = " ".join(current_chunk)
            chunks.append(
                self._create_chunk(
                    chunk_content, len(chunks), start_line, current_line - 1, metadata
                )
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
                "chunk_type": "semantic",
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
        # Check required fields
        similarity_threshold = config.get("similarity_threshold")
        if similarity_threshold is not None and not 0 <= similarity_threshold <= 1:
            msg = f"similarity_threshold must be between 0 and 1, got {similarity_threshold}"
            raise ValueError(msg)

        min_cluster_size = config.get("min_cluster_size")
        max_cluster_size = config.get("max_cluster_size")

        if min_cluster_size is not None and max_cluster_size is not None:
            if min_cluster_size > max_cluster_size:
                msg = (
                    f"min_cluster_size ({min_cluster_size}) cannot be greater than "
                    f"max_cluster_size ({max_cluster_size})"
                )
                raise ValueError(msg)

        return True

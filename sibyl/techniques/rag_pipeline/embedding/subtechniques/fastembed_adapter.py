"""
FastEmbed Adapter Subtechnique

This module provides backward compatibility with the existing FastEmbed
implementation used in the chunk embedder.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class FastEmbedAdapter:
    """
    Adapter for FastEmbed-based embedding.

    This subtechnique wraps the existing FastEmbed implementation
    to make it compatible with the new technique/subtechnique architecture.
    """

    def __init__(self) -> None:
        """Initialize FastEmbed adapter."""
        self._name = "fastembed"
        self._description = "FastEmbed library adapter"
        self._model = None

    @property
    def name(self) -> str:
        """Get subtechnique name."""
        return self._name

    @property
    def description(self) -> str:
        """Get subtechnique description."""
        return self._description

    def execute(
        self, input_data: str | list[str] | dict[str, Any], config: dict[str, Any]
    ) -> np.ndarray | list[np.ndarray]:
        """
        Execute embedding generation using FastEmbed.

        Args:
            input_data: Text(s) to embed
            config: Merged configuration

        Returns:
            Embedding vector(s)

        Raises:
            ValueError: If input_data is invalid
            RuntimeError: If FastEmbed is not available or embedding fails
        """
        # Extract texts
        if isinstance(input_data, str):
            texts = [input_data]
            return_single = True
        elif isinstance(input_data, list):
            texts = input_data
            return_single = False
        elif isinstance(input_data, dict):
            if "texts" in input_data:
                texts = input_data["texts"]
                return_single = False
            elif "text" in input_data:
                texts = [input_data["text"]]
                return_single = True
            else:
                msg = "Dict input must contain 'text' or 'texts' key"
                raise ValueError(msg)
        else:
            msg = f"Invalid input_data type: {type(input_data)}"
            raise TypeError(msg)

        if not texts:
            return [] if not return_single else np.array([])

        # Load model if needed
        if self._model is None:
            self._load_model(config)

        logger.debug("Generating embeddings for %s text(s)", len(texts))

        try:
            # Generate embeddings
            embeddings = list(self._model.embed(texts))

            # Convert to numpy arrays
            embeddings = [np.array(emb) for emb in embeddings]

            logger.info("Generated %s embeddings", len(embeddings))

            if return_single:
                return embeddings[0]
            return embeddings

        except Exception as e:
            logger.exception("FastEmbed generation failed: %s", e)
            msg = f"FastEmbed generation failed: {e}"
            raise RuntimeError(msg) from e

    def _load_model(self, config: dict[str, Any]) -> None:
        """
        Load FastEmbed model.

        Args:
            config: Configuration dictionary

        Raises:
            RuntimeError: If FastEmbed is not available or loading fails
        """
        try:
            from fastembed import TextEmbedding  # optional dependency

        except ImportError:
            msg = "FastEmbed library not installed. Install with: pip install fastembed"
            raise RuntimeError(msg) from None

        model_name = config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")

        logger.info("Loading FastEmbed model: %s", model_name)

        try:
            self._model = TextEmbedding(model_name=model_name)
            logger.info("FastEmbed model loaded successfully")
        except Exception as e:
            msg = f"Failed to load FastEmbed model {model_name}: {e}"
            raise RuntimeError(msg) from e

    def get_config(self) -> dict[str, Any]:
        """
        Get default configuration for this subtechnique.

        Returns:
            Default configuration
        """
        return {
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        }

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
        # Validate model_name
        model_name = config.get("model_name")
        if model_name is not None and (not isinstance(model_name, str) or not model_name):
            msg = "model_name must be a non-empty string"
            raise ValueError(msg)

        return True

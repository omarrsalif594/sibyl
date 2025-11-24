"""
Sentence Transformer Embedding Subtechnique

This module provides embedding generation using Sentence Transformers models.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedding:
    """
    Sentence Transformer-based embedding implementation.

    This subtechnique generates embeddings using sentence-transformers library.
    """

    def __init__(self) -> None:
        """Initialize sentence transformer embedding."""
        self._name = "sentence_transformer"
        self._description = "Sentence-Transformers based embedding"
        self._config_path = Path(__file__).parent / "config.yaml"
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
        Execute embedding generation.

        Args:
            input_data: Text(s) to embed (string, list of strings, or dict)
            config: Merged configuration

        Returns:
            Embedding vector(s) as numpy array(s)

        Raises:
            ValueError: If input_data is invalid
            RuntimeError: If embedding fails
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

        # Get configuration
        batch_size = config.get("batch_size", 32)
        normalize_embeddings = config.get("normalize_embeddings", True)

        logger.debug(f"Generating embeddings for {len(texts)} text(s) with batch_size={batch_size}")

        try:
            # Generate embeddings
            embeddings = self._model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=normalize_embeddings,
                show_progress_bar=config.get("show_progress", False),
            )

            logger.info("Generated %s embeddings", len(embeddings))

            if return_single:
                return embeddings[0]
            return embeddings

        except Exception as e:
            logger.exception("Embedding generation failed: %s", e)
            msg = f"Embedding generation failed: {e}"
            raise RuntimeError(msg) from e

    def _load_model(self, config: dict[str, Any]) -> None:
        """
        Load sentence transformer model.

        Args:
            config: Configuration dictionary

        Raises:
            RuntimeError: If model loading fails
        """
        try:
            from sentence_transformers import SentenceTransformer  # optional dependency

        except ImportError:
            msg = (
                "sentence-transformers library not installed. "
                "Install with: pip install sentence-transformers"
            )
            raise RuntimeError(msg) from None

        model_name = config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")
        device = config.get("device", "cpu")

        logger.info("Loading sentence transformer model: %s", model_name)

        try:
            self._model = SentenceTransformer(model_name, device=device)
            logger.info("Model loaded successfully on %s", device)
        except Exception as e:
            msg = f"Failed to load model {model_name}: {e}"
            raise RuntimeError(msg) from e

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
        # Validate batch_size
        batch_size = config.get("batch_size")
        if batch_size is not None and (not isinstance(batch_size, int) or batch_size <= 0):
            msg = f"batch_size must be a positive integer, got {batch_size}"
            raise ValueError(msg)

        # Validate max_seq_length
        max_seq_length = config.get("max_seq_length")
        if max_seq_length is not None:
            if not isinstance(max_seq_length, int) or max_seq_length <= 0:
                msg = f"max_seq_length must be a positive integer, got {max_seq_length}"
                raise ValueError(msg)

        # Validate device
        device = config.get("device")
        if device is not None:
            valid_devices = ["cpu", "cuda", "mps"]
            if device not in valid_devices:
                msg = f"device must be one of {valid_devices}, got {device}"
                raise ValueError(msg)

        return True

"""
Specialist Registry - Maps specialist IDs to loaded models and configurations.

This module provides a registry for managing locally trained specialist models,
including loading, caching, and configuration management.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class SpecialistConfig:
    """Configuration for a specialist model."""

    specialist_id: str
    model_path: str
    config_path: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpecialistConfig":
        """Create SpecialistConfig from dictionary."""
        return cls(
            specialist_id=data["specialist_id"],
            model_path=data["model_path"],
            config_path=data.get("config_path"),
            description=data.get("description"),
            tags=data.get("tags"),
            metadata=data.get("metadata"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert SpecialistConfig to dictionary."""
        return {
            "specialist_id": self.specialist_id,
            "model_path": self.model_path,
            "config_path": self.config_path,
            "description": self.description,
            "tags": self.tags,
            "metadata": self.metadata,
        }


class SpecialistWrapper:
    """
    Wrapper for a loaded specialist model.

    This wrapper provides a unified interface for interacting with specialist
    models, regardless of the underlying framework (Unsloth, Transformers, etc.).
    """

    def __init__(
        self,
        specialist_id: str,
        model: Any,
        tokenizer: Any,
        config: SpecialistConfig,
    ) -> None:
        """
        Initialize specialist wrapper.

        Args:
            specialist_id: Unique identifier for the specialist
            model: Loaded model instance
            tokenizer: Loaded tokenizer instance
            config: Specialist configuration
        """
        self.specialist_id = specialist_id
        self.model = model
        self.tokenizer = tokenizer
        self.config = config

    def generate(
        self, prompt: str, max_new_tokens: int = 512, temperature: float = 0.7, **kwargs
    ) -> str:
        """
        Generate text using the specialist model.

        Args:
            prompt: Input prompt
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        try:
            # Tokenize input
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=2048,
            )

            # Move to device (MPS for M1 Macs, CUDA for GPUs)
            device = self.model.device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            # Generate
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                **kwargs,
            )

            # Decode output
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Remove the prompt from the output
            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt) :].strip()

            return generated_text

        except Exception as e:
            logger.exception("Generation failed for specialist %s: %s", self.specialist_id, e)
            raise

    def unload(self) -> None:
        """Unload the model from memory."""
        # Clear references to allow garbage collection
        self.model = None
        self.tokenizer = None
        logger.info("Unloaded specialist: %s", self.specialist_id)


class SpecialistRegistry:
    """
    Registry for managing locally trained specialist models.

    This registry provides:
    - Loading specialists from configuration files
    - Caching loaded models in memory
    - Looking up specialists by ID or tags
    - Unloading specialists to free memory
    """

    def __init__(self, registry_path: Path | None = None) -> None:
        """
        Initialize specialist registry.

        Args:
            registry_path: Optional path to registry configuration YAML
        """
        self._specialists: dict[str, SpecialistWrapper] = {}
        self._configs: dict[str, SpecialistConfig] = {}
        self._registry_path = registry_path

        if registry_path and registry_path.exists():
            self.load_registry(registry_path)

    def load_registry(self, registry_path: Path) -> None:
        """
        Load specialist configurations from a registry file.

        The registry file should be a YAML file with the following structure:
        ```yaml
        specialists:
          - specialist_id: northwind_analytics
            model_path: specialists/models/northwind_analytics
            config_path: specialists/config/northwind_analytics.yaml
            description: Specialist for Northwind analytics queries
            tags: [analytics, sql]
        ```

        Args:
            registry_path: Path to registry YAML file
        """
        logger.info("Loading specialist registry from %s", registry_path)

        try:
            with open(registry_path) as f:
                registry_data = yaml.safe_load(f)

            specialists = registry_data.get("specialists", [])

            for spec_data in specialists:
                config = SpecialistConfig.from_dict(spec_data)
                self._configs[config.specialist_id] = config

            logger.info("Loaded %s specialist configurations", len(self._configs))

        except Exception as e:
            logger.exception("Failed to load registry from %s: %s", registry_path, e)
            raise

    def register_specialist(
        self,
        config: SpecialistConfig,
        load_immediately: bool = False,
    ) -> None:
        """
        Register a specialist configuration.

        Args:
            config: Specialist configuration
            load_immediately: If True, load the model immediately
        """
        self._configs[config.specialist_id] = config
        logger.info("Registered specialist: %s", config.specialist_id)

        if load_immediately:
            self.load_specialist(config.specialist_id)

    def load_specialist(self, specialist_id: str) -> SpecialistWrapper:
        """
        Load a specialist model into memory.

        Args:
            specialist_id: Specialist identifier

        Returns:
            Loaded specialist wrapper

        Raises:
            ValueError: If specialist not found in registry
        """
        # Check if already loaded
        if specialist_id in self._specialists:
            logger.debug("Specialist already loaded: %s", specialist_id)
            return self._specialists[specialist_id]

        # Get configuration
        config = self._configs.get(specialist_id)
        if not config:
            msg = f"Specialist not found in registry: {specialist_id}"
            raise ValueError(msg)

        logger.info("Loading specialist: %s from %s", specialist_id, config.model_path)

        try:
            # Import here to avoid dependency issues
            from transformers import AutoModelForCausalLM, AutoTokenizer  # expensive import

            # Load model and tokenizer
            model_path = Path(config.model_path)

            if not model_path.exists():
                msg = f"Model path not found: {model_path}"
                raise FileNotFoundError(msg)

            tokenizer = AutoTokenizer.from_pretrained(str(model_path))
            model = AutoModelForCausalLM.from_pretrained(
                str(model_path),
                device_map="auto",
                torch_dtype="auto",
            )

            # Wrap in specialist wrapper
            specialist = SpecialistWrapper(
                specialist_id=specialist_id,
                model=model,
                tokenizer=tokenizer,
                config=config,
            )

            # Cache loaded specialist
            self._specialists[specialist_id] = specialist

            logger.info("Successfully loaded specialist: %s", specialist_id)
            return specialist

        except Exception as e:
            logger.exception("Failed to load specialist %s: %s", specialist_id, e)
            raise

    def get_specialist(self, specialist_id: str) -> SpecialistWrapper | None:
        """
        Get a loaded specialist.

        This will load the specialist if not already loaded.

        Args:
            specialist_id: Specialist identifier

        Returns:
            Specialist wrapper, or None if not found
        """
        try:
            return self.load_specialist(specialist_id)
        except (ValueError, FileNotFoundError) as e:
            logger.warning("Could not get specialist %s: %s", specialist_id, e)
            return None

    def unload_specialist(self, specialist_id: str) -> None:
        """
        Unload a specialist from memory.

        Args:
            specialist_id: Specialist identifier
        """
        specialist = self._specialists.pop(specialist_id, None)
        if specialist:
            specialist.unload()
            logger.info("Unloaded specialist: %s", specialist_id)
        else:
            logger.warning("Specialist not loaded: %s", specialist_id)

    def unload_all(self) -> None:
        """Unload all specialists from memory."""
        logger.info("Unloading %s specialists", len(self._specialists))

        for specialist_id in list(self._specialists.keys()):
            self.unload_specialist(specialist_id)

    def list_specialists(self) -> list[str]:
        """
        List all registered specialist IDs.

        Returns:
            List of specialist IDs
        """
        return list(self._configs.keys())

    def list_loaded_specialists(self) -> list[str]:
        """
        List currently loaded specialist IDs.

        Returns:
            List of loaded specialist IDs
        """
        return list(self._specialists.keys())

    def find_by_tags(self, tags: list[str]) -> list[SpecialistConfig]:
        """
        Find specialists matching given tags.

        Args:
            tags: List of tags to match

        Returns:
            List of matching specialist configurations
        """
        matches = []

        for config in self._configs.values():
            if config.tags and any(tag in config.tags for tag in tags):
                matches.append(config)

        return matches

    def get_config(self, specialist_id: str) -> SpecialistConfig | None:
        """
        Get specialist configuration.

        Args:
            specialist_id: Specialist identifier

        Returns:
            Specialist configuration, or None if not found
        """
        return self._configs.get(specialist_id)

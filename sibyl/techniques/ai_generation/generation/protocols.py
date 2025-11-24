"""
Protocols and Types for Generation Technique

Defines the interfaces for text generation strategies.
"""

from abc import abstractmethod
from typing import Any, Protocol


class GenerationStrategy(Protocol):
    """
    Protocol for generation strategies.

    Each strategy produces text output based on input prompts and context.
    """

    @abstractmethod
    def generate(self, prompt: str, context: dict[str, Any] | None = None, **kwargs) -> str:
        """
        Generate text based on prompt and context.

        Args:
            prompt: The input prompt
            context: Optional context dictionary
            **kwargs: Additional generation parameters

        Returns:
            Generated text output
        """
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name used for generation"""
        ...

"""Embedding providers."""

from .api import OpenAIEmbeddingClient
from .base_client import BaseEmbeddingClient
from .local import FastEmbedClient

__all__ = [
    "BaseEmbeddingClient",
    "FastEmbedClient",
    "OpenAIEmbeddingClient",
]

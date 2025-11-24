"""
Embedding Subtechniques

This module contains various embedding strategies:
- sentence_transformer: Sentence-Transformers based embedding
- openai: OpenAI API embeddings
- fastembed_adapter: Adapter for existing FastEmbed implementation
"""

from .fastembed_adapter import FastEmbedAdapter
from .sentence_transformer import SentenceTransformerEmbedding

__all__ = [
    "FastEmbedAdapter",
    "SentenceTransformerEmbedding",
]

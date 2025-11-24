"""
RAG shop: high-level access to retrieval-augmented generation techniques.

This module provides convenient access to the core RAG pipeline techniques,
including chunking, embedding, search, retrieval, reranking, and query processing.
"""

from sibyl.techniques.rag_pipeline.augmentation.technique import AugmentationTechnique
from sibyl.techniques.rag_pipeline.chunking.technique import ChunkingTechnique
from sibyl.techniques.rag_pipeline.embedding.technique import EmbeddingTechnique
from sibyl.techniques.rag_pipeline.query_processing.technique import (
    QueryProcessingTechnique,
)
from sibyl.techniques.rag_pipeline.reranking.technique import RerankingTechnique
from sibyl.techniques.rag_pipeline.retrieval.technique import RetrievalTechnique
from sibyl.techniques.rag_pipeline.search.technique import SearchTechnique

__all__ = [
    "AugmentationTechnique",
    "ChunkingTechnique",
    "EmbeddingTechnique",
    "QueryProcessingTechnique",
    "RerankingTechnique",
    "RetrievalTechnique",
    "SearchTechnique",
]

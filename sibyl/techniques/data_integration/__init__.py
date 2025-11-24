"""Data integration techniques for document loading and vector storage.

This module provides techniques for integrating data providers (DocumentSourceProvider,
VectorStoreProvider, SQLDataProvider) with the Sibyl RAG pipeline.

These techniques bridge the gap between data connectors and RAG pipelines,
enabling end-to-end document ingestion and retrieval workflows.

All techniques now follow the canonical structure:
- load_documents: Load documents from DocumentSourceProvider
- query_sql: Query and execute SQL operations
- store_vectors: Store and manage vectors in vector databases
"""

from sibyl.techniques.data_integration.load_documents import build_technique as build_load_documents
from sibyl.techniques.data_integration.query_sql import build_technique as build_query_sql
from sibyl.techniques.data_integration.store_vectors import build_technique as build_store_vectors

__all__ = [
    "build_load_documents",
    "build_query_sql",
    "build_store_vectors",
]

# RAG Pipeline

This category contains all techniques related to Retrieval-Augmented Generation (RAG) pipelines.

## Overview

RAG pipeline components handle the complete flow from query processing through document retrieval
to context augmentation. These techniques work together to provide high-quality context for
AI generation.

## Techniques

- **augmentation**: Context augmentation
- **chunking**: Text chunking
- **embedding**: Vector embeddings
- **query_processing**: Query processing
- **reranking**: Result reranking
- **retrieval**: Document retrieval
- **search**: Search functionality

## Architecture

```
Query → Query Processing → Retrieval → Reranking → Context Augmentation → Generation
         ↓
      Embedding
         ↓
      Chunking
         ↓
      Search
```

## Usage

Each technique in this category can be used independently or as part of a complete RAG pipeline:

```python
from sibyl.techniques.rag_pipeline.chunking import ChunkingTechnique
from sibyl.techniques.rag_pipeline.embedding import EmbeddingTechnique
from sibyl.techniques.rag_pipeline.retrieval import RetrievalTechnique

# Use individual techniques
chunker = ChunkingTechnique(...)
embedder = EmbeddingTechnique(...)
retriever = RetrievalTechnique(...)
```

## Core Integration

Core engines for these techniques are located in:
- `sibyl/core/rag_pipeline/`

Each core engine provides a thin coordination layer that routes to technique implementations.

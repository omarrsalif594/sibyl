# Data Flow

Understanding how data flows through Sibyl helps you design effective pipelines and debug issues.

## Overview

Data in Sibyl flows through the layered architecture, being transformed at each stage:

```
User Input → Application → Runtime → Techniques → Providers → External Services
                ↓             ↓          ↓            ↓             ↓
            Parse/Route   Orchestrate  Process     Interface    Interact
                ↓             ↓          ↓            ↓             ↓
External Services → Providers → Techniques → Runtime → Application → User Output
```

## RAG Pipeline Data Flow

Let's trace data through a complete RAG pipeline:

### 1. Document Indexing Flow

```
┌──────────────────────────────────────────────────────────────┐
│ USER: Run build_docs_index pipeline                         │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER                                            │
│ CLI parses command, loads workspace configuration           │
│ Input: {pipeline: "build_docs_index", source: "./docs"}     │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ RUNTIME LAYER                                                │
│ - Load workspace from YAML                                   │
│ - Initialize providers (document source, embeddings, vector) │
│ - Initialize shops (RAG shop)                                │
│ - Start budget tracker                                       │
│ - Begin observability (logs, metrics, traces)                │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 1: Load Documents (RAG Shop - Document Loading)        │
│                                                              │
│ Technique: data.load_documents                              │
│ Input: {source: "./docs"}                                   │
│         ↓                                                    │
│ Provider: FilesystemMarkdownSource                          │
│ Action: Scan filesystem, read markdown files                │
│         ↓                                                    │
│ Output: {                                                    │
│   documents: [                                              │
│     {id: "doc1", content: "...", metadata: {...}},         │
│     {id: "doc2", content: "...", metadata: {...}}          │
│   ]                                                         │
│ }                                                           │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 2: Chunk Documents (RAG Shop - Chunking)               │
│                                                              │
│ Technique: rag.chunking (subtechnique: semantic)            │
│ Input: {documents: [...]}                                   │
│         ↓                                                    │
│ Process: Split documents into overlapping chunks            │
│ - Analyze semantic boundaries                               │
│ - Create chunks of ~512 tokens                              │
│ - Add 50 token overlap between chunks                       │
│ - Preserve metadata                                         │
│         ↓                                                    │
│ Output: {                                                    │
│   chunks: [                                                 │
│     {id: "chunk1", content: "...", doc_id: "doc1", ...},   │
│     {id: "chunk2", content: "...", doc_id: "doc1", ...},   │
│     {id: "chunk3", content: "...", doc_id: "doc2", ...}    │
│   ]                                                         │
│ }                                                           │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 3: Generate Embeddings (RAG Shop - Embedding)          │
│                                                              │
│ Technique: rag.embedding                                    │
│ Input: {chunks: [...]}                                      │
│         ↓                                                    │
│ Provider: SentenceTransformerProvider                       │
│ Action: Generate 384-dim vectors for each chunk             │
│ - Batch chunks for efficiency (32 per batch)                │
│ - Call embedding model                                      │
│ - Check cache first (if enabled)                            │
│         ↓                                                    │
│ Output: {                                                    │
│   chunks: [                                                 │
│     {id: "chunk1", content: "...", embedding: [0.1, ...]}, │
│     {id: "chunk2", content: "...", embedding: [0.2, ...]}, │
│     {id: "chunk3", content: "...", embedding: [0.3, ...]}  │
│   ]                                                         │
│ }                                                           │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 4: Store Vectors (Data Operation)                      │
│                                                              │
│ Technique: data.store_vectors                               │
│ Input: {chunks: [...], vector_store: "docs_index"}         │
│         ↓                                                    │
│ Provider: DuckDBVectorStore                                 │
│ Action: Upsert vectors into database                        │
│ - Prepare vector data                                       │
│ - Batch upsert (1000 vectors per batch)                    │
│ - Create/update indexes                                     │
│         ↓                                                    │
│ Output: {                                                    │
│   status: "success",                                        │
│   vectors_stored: 3,                                        │
│   collection: "embeddings"                                  │
│ }                                                           │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ RUNTIME LAYER                                                │
│ - Collect metrics (execution time, tokens used, cost)        │
│ - Update budget tracker                                      │
│ - Persist state to DuckDB                                    │
│ - Emit success logs                                          │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER                                            │
│ Format response for user                                     │
│ Output: "Successfully indexed 2 documents, 3 chunks"         │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ USER: View results                                           │
└──────────────────────────────────────────────────────────────┘
```

### 2. Query Answering Flow

```
┌──────────────────────────────────────────────────────────────┐
│ USER: "What is machine learning?"                           │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER                                            │
│ Input: {pipeline: "qa_over_docs", query: "What is ML?"}     │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ RUNTIME LAYER                                                │
│ Initialize pipeline execution                                │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 1: Query Processing (RAG Shop)                         │
│                                                              │
│ Technique: rag.query_processing (subtechnique: multi-query) │
│ Input: {query: "What is machine learning?"}                │
│         ↓                                                    │
│ Provider: OpenAIProvider (for query expansion)              │
│ Process: Generate query variations                          │
│ - Original: "What is machine learning?"                     │
│ - Variation 1: "Define machine learning"                    │
│ - Variation 2: "Explain ML concepts"                        │
│ - Variation 3: "Machine learning overview"                  │
│         ↓                                                    │
│ Output: {                                                    │
│   original_query: "What is machine learning?",             │
│   queries: ["What is ML?", "Define ML", ...]               │
│ }                                                           │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 2: Retrieval (RAG Shop)                                │
│                                                              │
│ Technique: rag.retrieval                                    │
│ Input: {queries: [...], top_k: 5}                          │
│         ↓                                                    │
│ Provider: SentenceTransformerProvider                       │
│ Action: Embed each query                                    │
│         ↓                                                    │
│ Provider: DuckDBVectorStore                                 │
│ Action: Vector similarity search                            │
│ - Search for each query variant                             │
│ - Combine results (fusion)                                  │
│ - Retrieve top_k=5 chunks                                   │
│         ↓                                                    │
│ Output: {                                                    │
│   retrieved_chunks: [                                       │
│     {id: "chunk2", content: "...", score: 0.92},           │
│     {id: "chunk5", content: "...", score: 0.88},           │
│     {id: "chunk1", content: "...", score: 0.85},           │
│     {id: "chunk7", content: "...", score: 0.82},           │
│     {id: "chunk3", content: "...", score: 0.80}            │
│   ]                                                         │
│ }                                                           │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 3: Reranking (RAG Shop)                                │
│                                                              │
│ Technique: rag.reranking (subtechnique: cross-encoder)     │
│ Input: {query: "...", chunks: [...]}                       │
│         ↓                                                    │
│ Provider: CrossEncoderProvider                              │
│ Action: Re-score query-chunk pairs                         │
│ - Score each (query, chunk) pair                           │
│ - Re-sort by new scores                                    │
│ - Keep top 3 after reranking                               │
│         ↓                                                    │
│ Output: {                                                    │
│   reranked_chunks: [                                        │
│     {id: "chunk5", content: "...", score: 0.95},           │
│     {id: "chunk2", content: "...", score: 0.91},           │
│     {id: "chunk1", content: "...", score: 0.87}            │
│   ]                                                         │
│ }                                                           │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 4: Augmentation (RAG Shop)                             │
│                                                              │
│ Technique: rag.augmentation (subtechnique: citation)       │
│ Input: {chunks: [...]}                                      │
│         ↓                                                    │
│ Process: Add metadata, citations, context                   │
│ - Extract source documents                                  │
│ - Add citation markers                                      │
│ - Include metadata (date, author, etc.)                     │
│         ↓                                                    │
│ Output: {                                                    │
│   context: "...[1] ... [2] ...",                           │
│   citations: [                                              │
│     {id: 1, source: "ml.md", chunk: "chunk5"},            │
│     {id: 2, source: "ai.md", chunk: "chunk2"}             │
│   ]                                                         │
│ }                                                           │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 5: Generation (AI Generation Shop)                     │
│                                                              │
│ Technique: ai_generation.generation (subtechnique: CoT)     │
│ Input: {query: "...", context: "...", citations: [...]}    │
│         ↓                                                    │
│ Provider: OpenAIProvider                                    │
│ Action: Generate answer with chain-of-thought               │
│ Prompt:                                                     │
│   "Based on the following context:                         │
│    [context with citations]                                │
│                                                             │
│    Question: What is machine learning?                     │
│                                                             │
│    Think step by step:                                     │
│    1. What information is relevant?                        │
│    2. How does it answer the question?                     │
│    3. What's the best way to explain it?"                  │
│         ↓                                                    │
│ LLM Response:                                               │
│   "Reasoning:                                               │
│    1. The context defines ML as a subset of AI...          │
│    2. It mentions three types...                           │
│    3. Clear explanation with examples...                   │
│                                                             │
│    Answer: Machine learning is a subset of                 │
│    artificial intelligence that enables systems...         │
│    The three main types are [1]..."                        │
│         ↓                                                    │
│ Output: {                                                    │
│   answer: "Machine learning is...",                        │
│   reasoning: "...",                                        │
│   citations: [...]                                         │
│ }                                                           │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ RUNTIME LAYER                                                │
│ - Collect metrics                                            │
│ - Update budget: $0.015 spent                                │
│ - Log completion                                              │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER                                            │
│ Format response with answer and metadata                     │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ USER: View answer with sources                              │
│ "Machine learning is a subset of AI... [1]                  │
│  Sources: ml.md, ai.md"                                     │
└──────────────────────────────────────────────────────────────┘
```

## Data Transformations

### Document → Chunks

```python
# Input
Document(
    id="doc1",
    content="# Machine Learning\n\nMachine learning is...",
    metadata={"source": "ml.md", "date": "2024-01-01"}
)

# After Chunking
[
    Chunk(
        id="chunk1",
        content="# Machine Learning\n\nMachine learning is...",
        doc_id="doc1",
        metadata={"source": "ml.md", "chunk_index": 0}
    ),
    Chunk(
        id="chunk2",
        content="...supervised learning involves...",
        doc_id="doc1",
        metadata={"source": "ml.md", "chunk_index": 1}
    )
]
```

### Chunks → Embeddings

```python
# Input
Chunk(id="chunk1", content="Machine learning is...")

# After Embedding
Chunk(
    id="chunk1",
    content="Machine learning is...",
    embedding=[0.023, -0.145, 0.892, ...],  # 384-dim vector
    metadata={...}
)
```

### Query → Retrieval Results

```python
# Input
{
    "query": "What is machine learning?"
}

# After Query Processing
{
    "original_query": "What is machine learning?",
    "queries": [
        "What is machine learning?",
        "Define machine learning",
        "Explain ML"
    ]
}

# After Retrieval
{
    "query": "What is machine learning?",
    "retrieved_chunks": [
        {"id": "chunk2", "content": "...", "score": 0.92},
        {"id": "chunk5", "content": "...", "score": 0.88}
    ]
}

# After Reranking
{
    "query": "What is machine learning?",
    "reranked_chunks": [
        {"id": "chunk5", "content": "...", "score": 0.95},  # Reordered!
        {"id": "chunk2", "content": "...", "score": 0.91}
    ]
}
```

## State Management

Sibyl maintains state throughout pipeline execution:

```
┌─────────────────────────────────────────┐
│         Execution State (DuckDB)        │
├─────────────────────────────────────────┤
│ Pipeline ID: uuid-1234                  │
│ Status: running                         │
│ Current Step: 3/5                       │
│ Budget Used: $0.012                     │
│ Start Time: 2024-01-15 10:30:00        │
│                                         │
│ Step History:                           │
│ 1. query_processing: completed (0.5s)   │
│ 2. retrieval: completed (1.2s)          │
│ 3. reranking: in_progress               │
│                                         │
│ Checkpoint Data:                        │
│ - Retrieved chunks: [...]               │
│ - Intermediate results: {...}           │
└─────────────────────────────────────────┘
```

## Caching Layers

Multiple cache levels optimize data flow:

```
Query Input
    ↓
┌────────────────────────┐
│   Semantic Cache       │ ← Similar query? Return cached answer
│   (Query-level)        │
└────────┬───────────────┘
         ↓ (miss)
┌────────────────────────┐
│   Query Cache          │ ← Exact query? Return cached results
│   (Exact match)        │
└────────┬───────────────┘
         ↓ (miss)
┌────────────────────────┐
│   Embedding Cache      │ ← Text embedded before? Return cached vector
│   (Text → Vector)      │
└────────┬───────────────┘
         ↓ (miss)
┌────────────────────────┐
│   Retrieval Cache      │ ← Vector searched before? Return cached results
│   (Vector → Docs)      │
└────────┬───────────────┘
         ↓ (miss)
    Execute Full Pipeline
```

## Error Flow

When errors occur, data flows through error handlers:

```
Pipeline Step Error
    ↓
┌────────────────────────┐
│   Error Handler        │
│   - Classify error     │
│   - Check retry policy │
│   - Log error          │
└────────┬───────────────┘
         ↓
    Retryable? ────Yes───→ Retry with backoff
         ↓
        No
         ↓
┌────────────────────────┐
│   Fallback Strategy    │
│   - Use cached result? │
│   - Use default value? │
│   - Skip step?         │
└────────┬───────────────┘
         ↓
    Recover or Fail
         ↓
┌────────────────────────┐
│   Return Error Result  │
│   {                    │
│     status: "error",   │
│     error: "...",      │
│     step: 3,           │
│     partial_results    │
│   }                    │
└────────────────────────┘
```

## Observability Data Flow

Alongside the main data flow, observability data is collected:

```
Pipeline Execution
    ↓
┌──────────────────────────────────────────┐
│         Metrics Collection               │
│  - Execution time per step               │
│  - Token usage                           │
│  - Cost tracking                         │
│  - Error rates                           │
└───────────┬──────────────────────────────┘
            ↓
┌──────────────────────────────────────────┐
│         Prometheus Metrics               │
│  sibyl_pipeline_duration_seconds         │
│  sibyl_tokens_used_total                 │
│  sibyl_cost_usd                          │
└───────────┬──────────────────────────────┘
            ↓
┌──────────────────────────────────────────┐
│         Logs (Structured JSON)           │
│  {                                       │
│    "timestamp": "...",                   │
│    "level": "INFO",                      │
│    "pipeline": "qa_over_docs",           │
│    "step": "reranking",                  │
│    "duration_ms": 1234                   │
│  }                                       │
└───────────┬──────────────────────────────┘
            ↓
┌──────────────────────────────────────────┐
│         Loki (Log Aggregation)           │
│         Grafana (Visualization)          │
└──────────────────────────────────────────┘
```

## Summary

Key points about data flow in Sibyl:

1. **Layered Flow**: Data flows through distinct architectural layers
2. **Transformative**: Each step transforms data for the next
3. **Stateful**: State is maintained throughout execution
4. **Cached**: Multiple cache levels optimize performance
5. **Observable**: Metrics and logs track data movement
6. **Resilient**: Error handling and fallback strategies

Understanding data flow helps you:
- Design efficient pipelines
- Debug issues quickly
- Optimize performance
- Monitor system health

## Further Reading

- **[Architecture Overview](overview.md)** - System architecture
- **[Core Concepts](core-concepts.md)** - Fundamental concepts
- **[Pipeline Configuration](../workspaces/configuration.md)** - Configure pipelines

---

**Previous**: [Core Concepts](core-concepts.md) | **Next**: [Design Patterns](design-patterns.md)

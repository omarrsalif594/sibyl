# RAG Pipeline Deep Dive

Complete guide to Retrieval-Augmented Generation (RAG) techniques in Sibyl.

## Overview

RAG (Retrieval-Augmented Generation) is a technique that enhances LLM responses by retrieving relevant information from a knowledge base. Sibyl provides a complete RAG pipeline with 8 modular techniques that can be composed to build powerful document Q&A, search, and analysis applications.

## RAG Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    RAG Pipeline                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Query Processing                                    │
│     └─> Expansion │ Decomposition │ Rewriting          │
│                                                         │
│  2. Retrieval                                           │
│     └─> Vector │ Hybrid │ Keyword                      │
│                                                         │
│  3. Reranking                                           │
│     └─> Cross-Encoder │ LLM │ ColBERT                  │
│                                                         │
│  4. Augmentation                                        │
│     └─> Context Stuffing │ Map-Reduce │ Refine         │
│                                                         │
│  5. Generation                                          │
│     └─> LLM generates answer from context              │
│                                                         │
│  6. Validation                                          │
│     └─> Fact Check │ Citation │ Hallucination          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Indexing Pipeline

Before querying, documents must be indexed:

### 1. Chunking

Splits documents into smaller, semantically meaningful chunks.

#### Recursive Chunking (Recommended)

```yaml
pipelines:
  index_docs:
    steps:
      - use: rag.chunking
        config:
          subtechnique: recursive
          chunk_size: 512              # Tokens per chunk
          chunk_overlap: 50            # Overlap for context
          separators:
            - "\n\n"                   # Paragraph breaks
            - "\n"                     # Line breaks
            - ". "                     # Sentences
            - " "                      # Words
            - ""                       # Characters
```

**How it works**:
1. Try splitting by first separator (`\n\n`)
2. If chunks still too large, try next separator (`\n`)
3. Continue until chunk size met
4. Maintains semantic coherence

**Best for**: General documents, articles, documentation

#### Semantic Chunking

```yaml
steps:
  - use: rag.chunking
    config:
      subtechnique: semantic
      chunk_size: 512
      similarity_threshold: 0.5        # Sentence similarity threshold
      model: all-MiniLM-L6-v2         # Embedding model
```

**How it works**:
1. Embed each sentence
2. Group sentences with similar embeddings
3. Create chunks from groups
4. Preserves semantic topics

**Best for**: Long-form content, books, research papers

#### Markdown-Aware Chunking

```yaml
steps:
  - use: rag.chunking
    config:
      subtechnique: markdown
      chunk_size: 512
      respect_headers: true            # Don't split across headers
      include_hierarchy: true          # Include header path
```

**How it works**:
1. Parse markdown structure
2. Respect heading hierarchy
3. Never split across sections
4. Include heading context in chunks

**Best for**: Technical documentation, API docs, README files

**Example**:
```markdown
# Installation

## Prerequisites

You need Python 3.11+

## Installation Steps

Run pip install...
```

Chunks:
- `# Installation > ## Prerequisites: You need Python 3.11+`
- `# Installation > ## Installation Steps: Run pip install...`

#### Code-Aware Chunking

```yaml
steps:
  - use: rag.chunking
    config:
      subtechnique: code
      chunk_size: 512
      language: python                 # python, javascript, java, etc.
      respect_functions: true          # Keep functions together
      respect_classes: true            # Keep classes together
```

**Best for**: Code repositories, API implementations

### 2. Embedding

Convert text chunks into vector representations.

```yaml
steps:
  - use: rag.embedding
    config:
      provider: local                  # Which embedding provider
      batch_size: 32                   # Process in batches
      normalize: true                  # Normalize vectors
      show_progress: true
```

**Provider Options**:

**Local (Free)**:
```yaml
providers:
  embedding:
    local:
      kind: sentence-transformer
      model: all-MiniLM-L6-v2          # 384 dimensions, fast
      # model: all-mpnet-base-v2       # 768 dimensions, better quality
```

**OpenAI (Paid)**:
```yaml
providers:
  embedding:
    openai:
      kind: openai
      model: text-embedding-3-small    # 1536 dimensions
      # model: text-embedding-3-large  # 3072 dimensions, best quality
```

### 3. Vector Storage

Store embeddings in vector database.

```yaml
steps:
  - use: data.store_vectors
    config:
      provider: main
      collection: documents
      batch_size: 1000                 # Batch inserts
      metadata_fields:                 # Store metadata
        - title
        - source
        - created_at
```

### Complete Indexing Pipeline

```yaml
pipelines:
  build_docs_index:
    shop: rag
    description: "Index documents for search"
    steps:
      # Load documents
      - use: data.load_documents
        config:
          source: filesystem_markdown
          path: ./docs

      # Chunk documents
      - use: rag.chunking
        config:
          subtechnique: markdown
          chunk_size: 512
          chunk_overlap: 50

      # Generate embeddings
      - use: rag.embedding
        config:
          provider: local
          batch_size: 32

      # Store in vector database
      - use: data.store_vectors
        config:
          provider: main
          collection: documents
          batch_size: 1000
```

**Run indexing**:
```bash
sibyl pipeline run \
  --workspace config/workspaces/my_workspace.yaml \
  --pipeline build_docs_index \
  --param source_path=./docs
```

## Query Pipeline

### 1. Query Processing

Enhance the user's query for better retrieval.

#### Query Expansion

Generate multiple variations of the query.

```yaml
steps:
  - use: rag.query_processing
    config:
      subtechnique: expansion
      num_queries: 3                   # Generate 3 variations
      provider: primary
      temperature: 0.7
```

**Example**:
```
Original: "machine learning"

Expanded:
1. "machine learning algorithms"
2. "supervised and unsupervised learning"
3. "neural networks and deep learning"
```

#### Query Decomposition

Break complex queries into sub-queries.

```yaml
steps:
  - use: rag.query_processing
    config:
      subtechnique: decomposition
      max_subqueries: 5
      provider: primary
```

**Example**:
```
Original: "Compare Python and JavaScript for web development"

Decomposed:
1. "Python web development frameworks"
2. "JavaScript web development frameworks"
3. "Python vs JavaScript performance"
4. "Python vs JavaScript syntax"
```

#### Query Rewriting

Rewrite query for better retrieval.

```yaml
steps:
  - use: rag.query_processing
    config:
      subtechnique: rewriting
      provider: primary
      template: |
        Rewrite this query for better search results:
        Query: {query}
        Rewritten:
```

**Example**:
```
Original: "How do I make my code faster?"

Rewritten: "Code performance optimization techniques and best practices"
```

### 2. Retrieval

Retrieve relevant documents from the vector store.

#### Vector Similarity Search

Pure vector-based retrieval.

```yaml
steps:
  - use: rag.retrieval
    config:
      subtechnique: similarity
      top_k: 10                        # Retrieve top 10
      similarity_threshold: 0.7        # Minimum similarity
      provider: main
```

**How it works**:
1. Embed the query
2. Find nearest vectors using cosine similarity
3. Return top K results above threshold

#### Hybrid Search

Combines vector and keyword search.

```yaml
steps:
  - use: rag.retrieval
    config:
      subtechnique: hybrid
      top_k: 10
      vector_weight: 0.7               # 70% vector, 30% keyword
      keyword_weight: 0.3
```

**How it works**:
1. Vector search retrieves candidates
2. Keyword (BM25) search retrieves candidates
3. Combine scores with weights
4. Return top K combined results

**Best for**: Queries with specific terms or entities

#### MMR (Maximal Marginal Relevance)

Balances relevance with diversity.

```yaml
steps:
  - use: rag.retrieval
    config:
      subtechnique: mmr
      top_k: 5                         # Final results
      fetch_k: 20                      # Initial retrieval
      lambda_param: 0.5                # Balance (0=diverse, 1=relevant)
```

**How it works**:
1. Retrieve fetch_k candidates (20)
2. Select most relevant
3. For each subsequent selection, maximize:
   - Relevance to query
   - Diversity from already selected
4. Return top_k diverse results

**Best for**: Avoiding redundant results, comprehensive answers

#### Contextual Retrieval

Includes surrounding context.

```yaml
steps:
  - use: rag.retrieval
    config:
      subtechnique: contextual
      top_k: 5
      context_window: 2                # Include 2 chunks before/after
```

**Best for**: Code search, sequential content

### 3. Reranking

Reorder retrieved results for better quality.

#### Cross-Encoder Reranking

Uses cross-encoder model for precise ranking.

```yaml
steps:
  - use: rag.reranking
    config:
      subtechnique: cross_encoder
      top_k: 3                         # Final results after reranking
      model: cross-encoder/ms-marco-MiniLM-L-6-v2
```

**How it works**:
1. For each (query, document) pair
2. Cross-encoder scores relevance
3. Rerank by score
4. Return top K

**Performance**:
- Slower than bi-encoder
- Much more accurate
- Use after initial retrieval to rerank top candidates

**Models**:
- `cross-encoder/ms-marco-MiniLM-L-6-v2` - Fast, good quality
- `cross-encoder/ms-marco-MiniLM-L-12-v2` - Better quality, slower
- `cross-encoder/ms-marco-electra-base` - Best quality, slowest

#### LLM Reranking

Uses LLM to judge relevance.

```yaml
steps:
  - use: rag.reranking
    config:
      subtechnique: llm
      top_k: 3
      provider: primary
      temperature: 0.0                 # Deterministic
```

**How it works**:
1. For each document, ask LLM:
   "On a scale of 1-10, how relevant is this document to the query?"
2. Rerank by LLM scores
3. Return top K

**Best for**: Complex relevance criteria, domain-specific ranking

#### ColBERT Reranking

Token-level late interaction.

```yaml
steps:
  - use: rag.reranking
    config:
      subtechnique: colbert
      top_k: 3
      model: colbert-ir/colbertv2.0
```

**Best for**: High accuracy, research applications

### 4. Augmentation

Prepare context for LLM generation.

#### Context Stuffing (Most Common)

Include all retrieved context in the prompt.

```yaml
steps:
  - use: rag.augmentation
    config:
      subtechnique: context_stuffing
      max_context_length: 4000         # Max tokens
      template: |
        Context:
        {% for doc in documents %}
        {{ doc.content }}
        ---
        {% endfor %}

        Question: {{ query }}

        Answer based only on the context above:
```

**Best for**: Most use cases, simple, effective

#### Map-Reduce

Process chunks separately, then combine.

```yaml
steps:
  - use: rag.augmentation
    config:
      subtechnique: map_reduce
      map_template: |
        Document: {{ document }}
        Question: {{ query }}
        Summary:

      reduce_template: |
        Summaries:
        {% for summary in summaries %}
        {{ summary }}
        {% endfor %}

        Final Answer:
```

**How it works**:
1. **Map**: For each document, generate a summary
2. **Reduce**: Combine summaries into final answer

**Best for**: Long contexts that don't fit in prompt, many documents

#### Refine

Iteratively refine the answer.

```yaml
steps:
  - use: rag.augmentation
    config:
      subtechnique: refine
      initial_template: |
        Document: {{ document }}
        Question: {{ query }}
        Answer:

      refine_template: |
        Previous Answer: {{ previous_answer }}
        New Document: {{ document }}

        Refine the answer:
```

**How it works**:
1. Generate answer from first document
2. For each subsequent document, refine the answer
3. Return final refined answer

**Best for**: Building comprehensive answers, fact accumulation

### 5. Generation

Generate the final answer using LLM.

```yaml
steps:
  - use: ai_generation.generation
    config:
      subtechnique: standard
      provider: primary
      temperature: 0.7
      max_tokens: 2000
      system_prompt: |
        You are a helpful assistant that answers questions based on the provided context.
        Always cite your sources.
        If the context doesn't contain the answer, say so.
```

### 6. Validation (Optional)

Validate the generated answer.

#### Fact Checking

```yaml
steps:
  - use: ai_generation.validation
    config:
      subtechnique: fact_check
      provider: primary
      strict_mode: true
```

#### Citation Validation

```yaml
steps:
  - use: ai_generation.validation
    config:
      subtechnique: citation
      require_citations: true
      citation_format: "[1]"
```

#### Hallucination Detection

```yaml
steps:
  - use: ai_generation.validation
    config:
      subtechnique: hallucination
      threshold: 0.8                   # Confidence threshold
```

## Complete RAG Pipeline Examples

### Basic RAG Pipeline

```yaml
pipelines:
  basic_qa:
    shop: rag
    steps:
      - use: rag.retrieval
        config:
          subtechnique: similarity
          top_k: 5

      - use: rag.augmentation
        config:
          subtechnique: context_stuffing

      - use: ai_generation.generation
        config:
          provider: primary
```

### Advanced RAG Pipeline

```yaml
pipelines:
  advanced_qa:
    shop: rag
    steps:
      # 1. Query Processing
      - use: rag.query_processing
        config:
          subtechnique: expansion
          num_queries: 3

      # 2. Retrieval with MMR
      - use: rag.retrieval
        config:
          subtechnique: mmr
          top_k: 10
          fetch_k: 20
          lambda_param: 0.7

      # 3. Reranking
      - use: rag.reranking
        config:
          subtechnique: cross_encoder
          top_k: 5

      # 4. Augmentation
      - use: rag.augmentation
        config:
          subtechnique: context_stuffing
          max_context_length: 4000

      # 5. Generation
      - use: ai_generation.generation
        config:
          provider: primary
          temperature: 0.7

      # 6. Validation
      - use: ai_generation.validation
        config:
          subtechnique: fact_check
```

### Multi-Query RAG with Fusion

```yaml
pipelines:
  fusion_qa:
    shop: rag
    steps:
      # Generate multiple query variations
      - use: rag.query_processing
        config:
          subtechnique: expansion
          num_queries: 5

      # Search with each query
      - use: rag.search
        config:
          subtechnique: hybrid
          top_k: 20
          parallel: true                # Run queries in parallel

      # Fuse results using reciprocal rank fusion
      - use: rag.ranking
        config:
          subtechnique: reciprocal_rank_fusion
          k: 60

      # Rerank top results
      - use: rag.reranking
        config:
          subtechnique: cross_encoder
          top_k: 5

      # Generate answer
      - use: rag.augmentation
        config:
          subtechnique: context_stuffing

      - use: ai_generation.generation
        config:
          provider: primary
```

## RAG Optimization Strategies

### 1. Chunk Size Optimization

```yaml
# Small chunks (256-512 tokens)
# Pros: Precise retrieval, lower noise
# Cons: May miss context
chunk_size: 512

# Large chunks (1024-2048 tokens)
# Pros: More context, better for complex queries
# Cons: More noise, higher costs
chunk_size: 1024
```

**Recommendation**: Start with 512, adjust based on evaluation.

### 2. Overlap Optimization

```yaml
# No overlap
chunk_overlap: 0          # Faster indexing, risk missing context

# Moderate overlap (10-20%)
chunk_overlap: 50         # Recommended: balances context and efficiency

# High overlap (50%+)
chunk_overlap: 256        # Maximum context, higher storage costs
```

### 3. Retrieval Optimization

```yaml
# Fast, less accurate
top_k: 3
similarity_threshold: 0.8

# Balanced
top_k: 5
similarity_threshold: 0.7

# Comprehensive, slower
top_k: 20
similarity_threshold: 0.5
```

### 4. Reranking Strategy

```yaml
# Lightweight reranking
retrieval:
  top_k: 10
reranking:
  top_k: 5                 # Rerank top 10 to 5

# Heavy reranking
retrieval:
  top_k: 50
reranking:
  top_k: 5                 # Rerank top 50 to 5
```

### 5. Cost Optimization

```yaml
# Minimize costs
providers:
  embedding:
    local:                 # Free local embeddings
      kind: sentence-transformer

  llm:
    simple:                # Cheaper model for simple queries
      kind: openai
      model: gpt-3.5-turbo

# Use caching
shops:
  infrastructure:
    config:
      caching:
        enabled: true
        ttl: 3600
```

## Evaluation Metrics

```yaml
shops:
  infrastructure:
    config:
      evaluation:
        metrics:
          # Retrieval metrics
          - context_precision     # Proportion of relevant docs retrieved
          - context_recall        # Proportion of relevant docs in corpus retrieved
          - mrr                   # Mean Reciprocal Rank
          - ndcg                  # Normalized Discounted Cumulative Gain

          # Generation metrics
          - answer_relevance      # Answer relevant to query
          - faithfulness          # Answer faithful to context
          - answer_correctness    # Answer factually correct
```

## Common RAG Patterns

### Pattern 1: Document Q&A

```yaml
pipelines:
  doc_qa:
    steps:
      - use: rag.retrieval
        config:
          subtechnique: hybrid
          top_k: 5
      - use: rag.reranking
      - use: rag.augmentation
      - use: ai_generation.generation
```

### Pattern 2: Conversational RAG

```yaml
pipelines:
  conversational_rag:
    steps:
      - use: workflow_orchestration.context_management
        config:
          max_history: 10

      - use: rag.query_processing
        config:
          subtechnique: rewriting
          context: "${conversation_history}"

      - use: rag.retrieval
      - use: rag.augmentation
      - use: ai_generation.generation
```

### Pattern 3: Multi-Source RAG

```yaml
pipelines:
  multi_source:
    steps:
      # Search source 1
      - use: rag.search
        config:
          collection: docs
          top_k: 5

      # Search source 2
      - use: rag.search
        config:
          collection: code
          top_k: 5

      # Combine and rank
      - use: rag.ranking
        config:
          subtechnique: reciprocal_rank_fusion

      - use: rag.augmentation
      - use: ai_generation.generation
```

## Troubleshooting

### Poor Retrieval Quality

**Problem**: Retrieved documents not relevant.

**Solutions**:
1. Adjust chunk size: `chunk_size: 512` → `chunk_size: 256`
2. Lower similarity threshold: `similarity_threshold: 0.7` → `0.5`
3. Use hybrid search instead of pure vector
4. Try query expansion
5. Add reranking step

### High Latency

**Problem**: Pipeline too slow.

**Solutions**:
1. Reduce `top_k`: `top_k: 20` → `top_k: 5`
2. Remove reranking for simple queries
3. Enable caching
4. Use batch processing
5. Optimize vector index (HNSW instead of IVFFlat)

### High Costs

**Problem**: LLM costs too high.

**Solutions**:
1. Use cheaper embedding model (local instead of OpenAI)
2. Use cheaper LLM (gpt-3.5-turbo instead of gpt-4)
3. Reduce `max_tokens`: `max_tokens: 2000` → `1000`
4. Enable semantic caching
5. Use smaller `top_k`

## Further Reading

- **[Technique Catalog](catalog.md)** - Complete technique reference
- **[Shops and Techniques](../workspaces/shops-and-techniques.md)** - Configuration guide
- **[Examples](../examples/rag-examples.md)** - Working examples
- **[Evaluation Guide](../operations/evaluation.md)** - Measuring RAG quality

---

**Previous**: [Technique Catalog](catalog.md) | **Next**: [AI Generation Techniques](ai-generation.md)

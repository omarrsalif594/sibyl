# Techniques Catalog

Complete reference of all available techniques in Sibyl, organized by shop.

## Overview

Sibyl provides 40+ techniques across 4 shops. This catalog helps you:
- Discover available techniques
- Understand what each technique does
- Choose the right technique for your use case
- Configure techniques properly

## Quick Reference

| Shop | Techniques | Purpose |
|------|-----------|---------|
| **RAG** | 8 techniques | Document processing and retrieval |
| **AI Generation** | 3 techniques | Content generation and validation |
| **Workflow** | 4 techniques | Orchestration and execution |
| **Infrastructure** | 7 techniques | Cross-cutting concerns |

---

## RAG Shop

Document processing and retrieval-augmented generation.

### 1. Chunking

**Purpose**: Split documents into smaller, manageable pieces

**Subtechniques**:

#### `fixed-size`
Split by character or token count with overlap.

```yaml
use: rag.chunking
config:
  subtechnique: fixed-size
  chunk_size: 512              # Characters or tokens
  chunk_overlap: 50            # Overlap between chunks
  separator: "\n\n"            # Split on paragraphs
```

**Best for**: General documents, consistent chunk sizes

#### `semantic`
Split based on semantic boundaries using embeddings.

```yaml
use: rag.chunking
config:
  subtechnique: semantic
  chunk_size: 512
  threshold: 0.5               # Similarity threshold
```

**Best for**: Maintaining semantic coherence, academic papers

#### `markdown`
Split markdown by structure (headers, sections).

```yaml
use: rag.chunking
config:
  subtechnique: markdown
  header_split: true           # Split on headers
  respect_code_blocks: true    # Keep code together
```

**Best for**: Markdown documentation, READMEs, technical docs

#### `sql`
Split SQL code by statements.

```yaml
use: rag.chunking
config:
  subtechnique: sql
  statement_per_chunk: true
```

**Best for**: SQL files, database scripts

---

### 2. Embedding

**Purpose**: Convert text to numerical vectors

**Subtechniques**:

#### `batch`
Process multiple texts in batches.

```yaml
use: rag.embedding
config:
  subtechnique: batch
  provider: default            # Embedding provider
  batch_size: 32
```

**Best for**: Large document sets, efficiency

#### `streaming`
Process texts one at a time.

```yaml
use: rag.embedding
config:
  subtechnique: streaming
  provider: default
```

**Best for**: Real-time processing, low memory

---

### 3. Search

**Purpose**: Find relevant documents

**Subtechniques**:

#### `vector-search`
Semantic search using vector similarity.

```yaml
use: rag.search
config:
  subtechnique: vector-search
  top_k: 10
  distance_metric: cosine
```

**Best for**: Semantic similarity, finding conceptually similar content

#### `keyword-search`
Lexical search using BM25.

```yaml
use: rag.search
config:
  subtechnique: keyword-search
  top_k: 10
  analyzer: standard
```

**Best for**: Exact term matching, specific keywords

#### `hybrid-search`
Combine vector and keyword search.

```yaml
use: rag.search
config:
  subtechnique: hybrid-search
  vector_weight: 0.7           # 70% vector
  keyword_weight: 0.3          # 30% keyword
  top_k: 10
```

**Best for**: Best of both worlds, comprehensive search

---

### 4. Retrieval

**Purpose**: Retrieve relevant documents from vector store

**Subtechniques**:

#### `semantic-search`
Standard vector similarity retrieval.

```yaml
use: rag.retrieval
config:
  subtechnique: semantic-search
  vector_store: main
  top_k: 5
  min_score: 0.7
```

**Best for**: General RAG pipelines

#### `mmr`
Maximal Marginal Relevance (diversity).

```yaml
use: rag.retrieval
config:
  subtechnique: mmr
  top_k: 10
  lambda: 0.5                  # Diversity vs relevance
```

**Best for**: Diverse results, reducing redundancy

---

### 5. Reranking

**Purpose**: Re-order retrieved documents for better relevance

**Subtechniques**:

#### `cross-encoder`
Deep reranking with cross-encoder models.

```yaml
use: rag.reranking
config:
  subtechnique: cross-encoder
  model: cross-encoder/ms-marco-MiniLM-L-6-v2
  top_k: 3
```

**Best for**: Highest quality, when latency allows

#### `llm-rerank`
Use LLM to score relevance.

```yaml
use: rag.reranking
config:
  subtechnique: llm-rerank
  provider: primary
  top_k: 3
```

**Best for**: Complex relevance criteria, expensive but accurate

#### `diversity-rerank`
Maximize diversity in results.

```yaml
use: rag.reranking
config:
  subtechnique: diversity-rerank
  diversity_weight: 0.3
  top_k: 3
```

**Best for**: Exploratory search, broad coverage

#### `bm25-rerank`
Keyword-based reranking.

```yaml
use: rag.reranking
config:
  subtechnique: bm25-rerank
  top_k: 3
```

**Best for**: Fast, lexical relevance

#### `fusion`
Combine multiple ranking strategies.

```yaml
use: rag.reranking
config:
  subtechnique: fusion
  strategies:
    - cross-encoder
    - bm25
  weights: [0.7, 0.3]
```

**Best for**: Best overall performance

---

### 6. Query Processing

**Purpose**: Transform and enhance user queries

**Subtechniques**:

#### `query-expansion`
Add related terms to query.

```yaml
use: rag.query_processing
config:
  subtechnique: query-expansion
  num_expansions: 5
  provider: primary
```

**Best for**: Improving recall, broader search

#### `query-rewriting`
Reformulate query for better search.

```yaml
use: rag.query_processing
config:
  subtechnique: query-rewriting
  provider: primary
```

**Best for**: Ambiguous queries, improving precision

#### `multi-query`
Generate multiple query variations.

```yaml
use: rag.query_processing
config:
  subtechnique: multi-query
  num_queries: 3
  provider: primary
```

**Best for**: Comprehensive search, different perspectives

#### `hyde`
Hypothetical Document Embeddings - generate hypothetical answer, search for it.

```yaml
use: rag.query_processing
config:
  subtechnique: hyde
  provider: primary
```

**Best for**: When queries are questions, finding answer-like documents

#### `query-decomposition`
Break complex queries into sub-queries.

```yaml
use: rag.query_processing
config:
  subtechnique: query-decomposition
  max_sub_queries: 5
  provider: primary
```

**Best for**: Complex, multi-part questions

---

### 7. Augmentation

**Purpose**: Enhance retrieved documents with metadata and context

**Subtechniques**:

#### `metadata-injection`
Add document metadata to context.

```yaml
use: rag.augmentation
config:
  subtechnique: metadata-injection
  fields: [title, author, date, source]
```

**Best for**: Providing context, attribution

#### `citation-injection`
Add citation markers.

```yaml
use: rag.augmentation
config:
  subtechnique: citation-injection
  format: "[{index}]"
```

**Best for**: Academic writing, source tracking

#### `cross-reference`
Add links to related documents.

```yaml
use: rag.augmentation
config:
  subtechnique: cross-reference
  max_references: 3
```

**Best for**: Exploratory research, knowledge graphs

#### `temporal-context`
Add time-based context.

```yaml
use: rag.augmentation
config:
  subtechnique: temporal-context
  include_dates: true
```

**Best for**: News, historical documents

#### `entity-linking`
Link entities to knowledge bases.

```yaml
use: rag.augmentation
config:
  subtechnique: entity-linking
  knowledge_base: wikidata
```

**Best for**: Entity-centric applications

---

### 8. Ranking

**Purpose**: Score and order retrieved documents

**Subtechniques**:

#### `relevance-scoring`
Score documents by relevance.

```yaml
use: rag.ranking
config:
  subtechnique: relevance-scoring
  algorithm: bm25
```

---

## AI Generation Shop

Content generation and quality control.

### 1. Generation

**Purpose**: Generate text with LLMs

**Subtechniques**:

#### `basic-generation`
Standard LLM completion.

```yaml
use: ai_generation.generation
config:
  subtechnique: basic-generation
  provider: primary
  temperature: 0.7
  max_tokens: 2000
```

**Best for**: Simple generation tasks

#### `chain-of-thought`
Step-by-step reasoning before answer.

```yaml
use: ai_generation.generation
config:
  subtechnique: chain-of-thought
  provider: primary
```

**Best for**: Complex reasoning, explanations

#### `react`
Reasoning and Acting - iterative reasoning with actions.

```yaml
use: ai_generation.generation
config:
  subtechnique: react
  provider: primary
  max_iterations: 5
```

**Best for**: Multi-step tasks, tool use

#### `tree-of-thought`
Explore multiple reasoning paths.

```yaml
use: ai_generation.generation
config:
  subtechnique: tree-of-thought
  provider: primary
  branches: 3
  depth: 2
```

**Best for**: Complex problems, need to explore options

#### `self-consistency`
Generate multiple answers, pick most consistent.

```yaml
use: ai_generation.generation
config:
  subtechnique: self-consistency
  provider: primary
  num_samples: 5
```

**Best for**: Factual accuracy, reducing hallucinations

---

### 2. Consensus

**Purpose**: Combine multiple LLM responses

**Subtechniques**:

#### `quorum-voting`
Majority vote on answers.

```yaml
use: ai_generation.consensus
config:
  subtechnique: quorum-voting
  num_responses: 3
  threshold: 0.6               # 60% agreement
```

**Best for**: Binary decisions, classification

#### `weighted-voting`
Weight votes by confidence.

```yaml
use: ai_generation.consensus
config:
  subtechnique: weighted-voting
  num_responses: 3
  confidence_weight: true
```

**Best for**: When some models more reliable

#### `hybrid-consensus`
Combine voting with quality scoring.

```yaml
use: ai_generation.consensus
config:
  subtechnique: hybrid-consensus
  num_responses: 5
  quality_threshold: 0.7
```

**Best for**: Best overall quality

---

### 3. Validation

**Purpose**: Validate and improve generated content

**Subtechniques**:

#### `quality-scoring`
Score output quality.

```yaml
use: ai_generation.validation
config:
  subtechnique: quality-scoring
  min_score: 0.7
  max_retries: 3
```

**Best for**: Quality control, retry on poor outputs

#### `fact-checking`
Verify factual accuracy.

```yaml
use: ai_generation.validation
config:
  subtechnique: fact-checking
  source_check: true
```

**Best for**: Factual content, reducing hallucinations

#### `format-validation`
Validate output format.

```yaml
use: ai_generation.validation
config:
  subtechnique: format-validation
  schema: json_schema
```

**Best for**: Structured outputs, JSON/XML

---

## Workflow Shop

Orchestration and execution control.

### 1. Session Management

**Purpose**: Manage conversation sessions

**Subtechniques**:

#### `token-rotation`
Rotate when token limit approached.

```yaml
use: workflow.session_management
config:
  subtechnique: token-rotation
  max_tokens: 4000
  rotation_threshold: 0.8      # Rotate at 80%
```

#### `context-preservation`
Preserve important context across rotations.

```yaml
use: workflow.session_management
config:
  subtechnique: context-preservation
  preserve_entities: true
```

#### `summarization`
Summarize history when rotating.

```yaml
use: workflow.session_management
config:
  subtechnique: summarization
  provider: primary
```

---

### 2. Context Management

**Purpose**: Manage context windows

**Subtechniques**:

#### `rotation-strategy`
Rotate context when full.

```yaml
use: workflow.context_management
config:
  subtechnique: rotation-strategy
  max_context: 8000
```

#### `summarization`
Summarize old context.

```yaml
use: workflow.context_management
config:
  subtechnique: summarization
  provider: primary
```

#### `compression`
Compress context to fit.

```yaml
use: workflow.context_management
config:
  subtechnique: compression
  algorithm: extractive
```

#### `prioritization`
Keep most important context.

```yaml
use: workflow.context_management
config:
  subtechnique: prioritization
  importance_metric: recency
```

---

### 3. Graph

**Purpose**: Graph-based workflow execution

**Subtechniques**:

#### `graph-backend`
NetworkX-based execution graph.

```yaml
use: workflow.graph
config:
  subtechnique: graph-backend
```

#### `analysis-algorithms`
Graph analysis (shortest path, etc.).

```yaml
use: workflow.graph
config:
  subtechnique: analysis-algorithms
```

#### `visualization`
Visualize execution graph.

```yaml
use: workflow.graph
config:
  subtechnique: visualization
  format: png
```

---

### 4. Orchestration

**Purpose**: Coordinate pipeline execution

**Subtechniques**:

#### `sequential`
Execute steps one after another.

```yaml
use: workflow.orchestration
config:
  subtechnique: sequential
```

#### `parallel`
Execute steps in parallel.

```yaml
use: workflow.orchestration
config:
  subtechnique: parallel
  max_parallelism: 4
```

#### `conditional`
Conditional execution based on results.

```yaml
use: workflow.orchestration
config:
  subtechnique: conditional
  conditions:
    - if: "score > 0.8"
      then: high_quality_path
```

---

## Infrastructure Shop

Cross-cutting concerns.

### 1. Caching

**Purpose**: Cache results to improve performance

**Subtechniques**:

#### `embedding-cache`
Cache text embeddings.

```yaml
use: infrastructure.caching
config:
  subtechnique: embedding-cache
  backend: redis
  ttl: 3600
```

#### `retrieval-cache`
Cache retrieval results.

```yaml
use: infrastructure.caching
config:
  subtechnique: retrieval-cache
  backend: memory
```

#### `semantic-cache`
Cache by semantic similarity.

```yaml
use: infrastructure.caching
config:
  subtechnique: semantic-cache
  similarity_threshold: 0.95
```

#### `query-cache`
Cache exact queries.

```yaml
use: infrastructure.caching
config:
  subtechnique: query-cache
  backend: redis
  ttl: 1800
```

---

### 2. Security

**Purpose**: Security and safety controls

**Subtechniques**:

#### `content-filtering`
Filter inappropriate content.

```yaml
use: infrastructure.security
config:
  subtechnique: content-filtering
  blocked_patterns: [...]
```

#### `pii-redaction`
Remove personally identifiable information.

```yaml
use: infrastructure.security
config:
  subtechnique: pii-redaction
  patterns: [ssn, email, phone]
```

#### `access-control`
Role-based access control.

```yaml
use: infrastructure.security
config:
  subtechnique: access-control
  roles: [admin, user]
```

#### `prompt-injection-detection`
Detect malicious prompts.

```yaml
use: infrastructure.security
config:
  subtechnique: prompt-injection-detection
  sensitivity: high
```

#### `audit-logging`
Log all operations for audit.

```yaml
use: infrastructure.security
config:
  subtechnique: audit-logging
  log_level: INFO
```

---

### 3. Evaluation

**Purpose**: Evaluate output quality

**Subtechniques**:

#### `faithfulness`
Check if answer supported by sources.

```yaml
use: infrastructure.evaluation
config:
  subtechnique: faithfulness
```

#### `relevance`
Check if answer relevant to query.

```yaml
use: infrastructure.evaluation
config:
  subtechnique: relevance
```

#### `groundedness`
Check if answer grounded in retrieved docs.

```yaml
use: infrastructure.evaluation
config:
  subtechnique: groundedness
```

#### `completeness`
Check if answer complete.

```yaml
use: infrastructure.evaluation
config:
  subtechnique: completeness
```

#### `coherence`
Check if answer coherent.

```yaml
use: infrastructure.evaluation
config:
  subtechnique: coherence
```

---

### 4-7. Other Infrastructure Techniques

- **Checkpointing**: Save and resume state
- **Learning**: Pattern learning and feedback
- **Rate Limiting**: Control API usage
- **Resilience**: Circuit breakers, retries
- **Scoring**: Quality scoring
- **Workflow Optimization**: Adaptive retrieval, early stopping, cost optimization

---

## Technique Selection Guide

### For Document Q&A

```yaml
pipelines:
  qa_pipeline:
    steps:
      - use: rag.chunking
        config: {subtechnique: semantic}
      - use: rag.embedding
      - use: rag.retrieval
        config: {top_k: 10}
      - use: rag.reranking
        config: {subtechnique: cross-encoder, top_k: 3}
      - use: ai_generation.generation
        config: {subtechnique: chain-of-thought}
```

### For Code Analysis

```yaml
pipelines:
  code_analysis:
    steps:
      - use: rag.chunking
        config: {subtechnique: semantic}  # Or custom code chunker
      - use: rag.query_processing
        config: {subtechnique: query-decomposition}
      - use: rag.retrieval
      - use: ai_generation.generation
        config: {subtechnique: react}
```

### For Factual Accuracy

```yaml
pipelines:
  factual_qa:
    steps:
      - use: rag.retrieval
      - use: rag.reranking
        config: {subtechnique: fusion}
      - use: ai_generation.generation
        config: {subtechnique: self-consistency}
      - use: ai_generation.validation
        config: {subtechnique: fact-checking}
      - use: infrastructure.evaluation
        config: {subtechnique: faithfulness}
```

## Further Reading

- **[RAG Pipeline Techniques](rag-pipeline.md)** - Deep dive into RAG
- **[AI Generation Techniques](ai-generation.md)** - Generation strategies
- **[Custom Techniques](custom-techniques.md)** - Build your own
- **[Shops & Techniques Configuration](../workspaces/shops-and-techniques.md)** - Configure techniques

---

**Previous**: [Workspaces](../workspaces/overview.md) | **Next**: [RAG Pipeline](rag-pipeline.md)

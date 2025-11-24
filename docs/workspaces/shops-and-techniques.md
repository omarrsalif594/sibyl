# Shops and Techniques Configuration

Complete guide to configuring shops and techniques in Sibyl workspaces.

## Overview

**Shops** are collections of related techniques that provide specific AI capabilities. **Techniques** are modular AI processing components that can be composed into pipelines.

Sibyl includes 4 built-in shops with 40+ techniques:

1. **RAG Shop** - Retrieval-Augmented Generation
2. **AI Generation Shop** - Text generation and synthesis
3. **Workflow Orchestration Shop** - Complex AI workflows
4. **Infrastructure Shop** - Supporting capabilities

## Shop Configuration

### Enabling Shops

```yaml
# config/workspaces/my_workspace.yaml
shops:
  rag:
    enabled: true
    config:
      default_chunk_size: 512
      default_overlap: 50

  ai_generation:
    enabled: true
    config:
      default_provider: primary
      max_retries: 3

  workflow_orchestration:
    enabled: true
    config:
      max_iterations: 10

  infrastructure:
    enabled: true
    config:
      cache_enabled: true
      cache_ttl: 3600
```

### Shop-Level Configuration

Each shop accepts global configuration that applies to all its techniques:

```yaml
shops:
  rag:
    enabled: true
    config:
      # Default chunking settings
      chunk_size: 512
      chunk_overlap: 50

      # Default embedding settings
      embedding_provider: default

      # Default retrieval settings
      top_k: 5
      similarity_threshold: 0.7

      # Reranking settings
      rerank_enabled: true
      rerank_top_k: 3
```

## RAG Shop Configuration

### Complete RAG Shop Setup

```yaml
shops:
  rag:
    enabled: true
    config:
      # Chunking Configuration
      chunking:
        default_strategy: recursive
        chunk_size: 512
        chunk_overlap: 50
        separators: ["\n\n", "\n", ". ", " ", ""]

      # Embedding Configuration
      embedding:
        provider: local
        batch_size: 32
        normalize: true

      # Vector Store Configuration
      vector_store:
        provider: main
        collection_name: documents
        distance_metric: cosine

      # Retrieval Configuration
      retrieval:
        top_k: 5
        similarity_threshold: 0.7
        fetch_k_multiplier: 2

      # Reranking Configuration
      reranking:
        enabled: true
        top_k: 3
        model: cross-encoder/ms-marco-MiniLM-L-6-v2

      # Query Processing
      query_processing:
        expansion_enabled: true
        num_queries: 3
        decomposition_enabled: false
```

### RAG Techniques Reference

#### 1. Chunking

```yaml
# In pipeline
steps:
  - use: rag.chunking
    config:
      subtechnique: recursive    # recursive, semantic, markdown
      chunk_size: 512
      chunk_overlap: 50
      metadata_mode: include     # include, exclude, separate
```

**Available Subtechniques**:
- `recursive` - Split by separators recursively
- `semantic` - Split by semantic meaning
- `markdown` - Preserve markdown structure
- `code` - Code-aware splitting
- `fixed` - Fixed-size chunks

#### 2. Embedding

```yaml
steps:
  - use: rag.embedding
    config:
      provider: local            # Which embedding provider
      batch_size: 32
      normalize: true
      show_progress: true
```

#### 3. Search

```yaml
steps:
  - use: rag.search
    config:
      subtechnique: vector       # vector, hybrid, keyword
      top_k: 10
      filters:
        document_type: ["pdf", "markdown"]
        date_after: "2024-01-01"
```

**Available Subtechniques**:
- `vector` - Pure vector similarity search
- `hybrid` - Vector + keyword combination
- `keyword` - Traditional keyword search
- `multi_vector` - Multiple vector spaces

#### 4. Retrieval

```yaml
steps:
  - use: rag.retrieval
    config:
      subtechnique: similarity   # similarity, mmr, diversity
      top_k: 5
      similarity_threshold: 0.7
      fetch_k: 20                # Fetch more, filter later
```

**Available Subtechniques**:
- `similarity` - Pure similarity-based
- `mmr` - Maximal Marginal Relevance (diversity)
- `diversity` - Maximize result diversity
- `contextual` - Include surrounding context

#### 5. Reranking

```yaml
steps:
  - use: rag.reranking
    config:
      subtechnique: cross_encoder  # cross_encoder, llm, colbert
      top_k: 3
      model: cross-encoder/ms-marco-MiniLM-L-6-v2
```

**Available Subtechniques**:
- `cross_encoder` - Cross-encoder reranking
- `llm` - LLM-based reranking
- `colbert` - ColBERT reranking
- `bm25` - BM25 reranking

#### 6. Query Processing

```yaml
steps:
  - use: rag.query_processing
    config:
      subtechnique: expansion    # expansion, decomposition, rewriting
      num_queries: 3
      provider: primary
```

**Available Subtechniques**:
- `expansion` - Generate multiple query variations
- `decomposition` - Break complex queries into sub-queries
- `rewriting` - Rewrite query for better retrieval
- `routing` - Route query to appropriate data source

#### 7. Augmentation

```yaml
steps:
  - use: rag.augmentation
    config:
      subtechnique: context_stuffing  # context_stuffing, map_reduce, refine
      max_context_length: 4000
      template: |
        Context: {context}
        Question: {query}
        Answer:
```

**Available Subtechniques**:
- `context_stuffing` - Include all context in prompt
- `map_reduce` - Process chunks separately, then combine
- `refine` - Iteratively refine answer
- `custom_template` - Use custom prompt template

#### 8. Ranking

```yaml
steps:
  - use: rag.ranking
    config:
      subtechnique: reciprocal_rank_fusion  # reciprocal_rank_fusion, weighted, learned
      weights:
        vector_score: 0.7
        keyword_score: 0.3
```

## AI Generation Shop Configuration

### Complete AI Generation Setup

```yaml
shops:
  ai_generation:
    enabled: true
    config:
      # Default LLM settings
      generation:
        provider: primary
        temperature: 0.7
        max_tokens: 2000
        top_p: 1.0

      # Consensus settings
      consensus:
        num_generations: 3
        agreement_threshold: 0.8

      # Validation settings
      validation:
        fact_check_enabled: true
        citation_required: true
```

### AI Generation Techniques

#### 1. Generation

```yaml
steps:
  - use: ai_generation.generation
    config:
      subtechnique: standard     # standard, streaming, structured
      provider: primary
      temperature: 0.7
      max_tokens: 2000
      stop_sequences: ["\n\n"]
```

**Available Subtechniques**:
- `standard` - Standard completion
- `streaming` - Streaming response
- `structured` - JSON/structured output
- `chat` - Chat-based generation
- `instruct` - Instruction-following

#### 2. Consensus

```yaml
steps:
  - use: ai_generation.consensus
    config:
      subtechnique: majority_vote  # majority_vote, weighted, llm_judge
      num_generations: 3
      providers: [primary, fallback]
      agreement_threshold: 0.8
```

**Available Subtechniques**:
- `majority_vote` - Simple majority voting
- `weighted` - Weighted voting by confidence
- `llm_judge` - LLM judges best response
- `ensemble` - Combine multiple responses

#### 3. Validation

```yaml
steps:
  - use: ai_generation.validation
    config:
      subtechnique: fact_check   # fact_check, citation, hallucination
      provider: primary
      strict_mode: true
```

**Available Subtechniques**:
- `fact_check` - Verify factual accuracy
- `citation` - Ensure proper citations
- `hallucination` - Detect hallucinations
- `consistency` - Check internal consistency

## Workflow Orchestration Shop Configuration

### Complete Workflow Setup

```yaml
shops:
  workflow_orchestration:
    enabled: true
    config:
      # Session management
      session:
        timeout: 3600
        max_messages: 100

      # Context management
      context:
        max_tokens: 8000
        compression_enabled: true

      # Graph orchestration
      graph:
        max_iterations: 10
        cycle_detection: true

      # Multi-step orchestration
      orchestration:
        parallel_enabled: true
        max_parallel: 5
```

### Workflow Techniques

#### 1. Session Management

```yaml
steps:
  - use: workflow_orchestration.session_management
    config:
      subtechnique: memory       # memory, stateless, persistent
      timeout: 3600
      max_messages: 100
      storage: redis
```

#### 2. Context Management

```yaml
steps:
  - use: workflow_orchestration.context_management
    config:
      subtechnique: window       # window, compression, summary
      max_tokens: 8000
      window_size: 10
```

#### 3. Graph Orchestration

```yaml
steps:
  - use: workflow_orchestration.graph
    config:
      subtechnique: dag          # dag, cyclic, conditional
      max_iterations: 10
      graph_definition:
        nodes:
          - id: retrieve
            technique: rag.retrieval
          - id: generate
            technique: ai_generation.generation
        edges:
          - from: retrieve
            to: generate
```

#### 4. Orchestration

```yaml
steps:
  - use: workflow_orchestration.orchestration
    config:
      subtechnique: sequential   # sequential, parallel, conditional
      steps:
        - name: step1
          technique: rag.retrieval
        - name: step2
          technique: ai_generation.generation
          depends_on: [step1]
```

## Infrastructure Shop Configuration

### Complete Infrastructure Setup

```yaml
shops:
  infrastructure:
    enabled: true
    config:
      # Caching
      caching:
        enabled: true
        backend: redis
        ttl: 3600

      # Security
      security:
        pii_redaction: true
        prompt_injection_detection: true

      # Evaluation
      evaluation:
        metrics: [accuracy, relevance, coherence]
        human_in_loop: false

      # Checkpointing
      checkpointing:
        enabled: true
        frequency: 10

      # Rate limiting
      rate_limiting:
        enabled: true
        requests_per_minute: 60

      # Resilience
      resilience:
        retries: 3
        circuit_breaker: true
```

### Infrastructure Techniques

#### 1. Caching

```yaml
steps:
  - use: infrastructure.caching
    config:
      subtechnique: semantic     # semantic, exact, vector
      backend: redis
      ttl: 3600
      cache_key_prefix: "sibyl:"
```

#### 2. Security

```yaml
steps:
  - use: infrastructure.security
    config:
      subtechnique: pii_redaction  # pii_redaction, injection_detection
      pii_patterns: [email, phone, ssn]
      replacement: "[REDACTED]"
```

#### 3. Evaluation

```yaml
steps:
  - use: infrastructure.evaluation
    config:
      subtechnique: rag_metrics  # rag_metrics, generation_metrics
      metrics:
        - answer_relevance
        - faithfulness
        - context_precision
        - context_recall
```

#### 4. Rate Limiting

```yaml
steps:
  - use: infrastructure.rate_limiting
    config:
      subtechnique: token_bucket  # token_bucket, sliding_window
      requests_per_minute: 60
      burst: 10
```

## Complete Pipeline Examples

### Example 1: Basic RAG Pipeline

```yaml
pipelines:
  qa_over_docs:
    shop: rag
    description: "Answer questions from documents"
    steps:
      # Query processing
      - use: rag.query_processing
        config:
          subtechnique: expansion
          num_queries: 3

      # Retrieval
      - use: rag.retrieval
        config:
          subtechnique: mmr
          top_k: 10

      # Reranking
      - use: rag.reranking
        config:
          subtechnique: cross_encoder
          top_k: 3

      # Augmentation
      - use: rag.augmentation
        config:
          subtechnique: context_stuffing
          max_context_length: 4000

      # Generation
      - use: ai_generation.generation
        config:
          subtechnique: standard
          provider: primary
          temperature: 0.7

      # Validation
      - use: ai_generation.validation
        config:
          subtechnique: fact_check
```

### Example 2: Advanced RAG with Infrastructure

```yaml
pipelines:
  advanced_qa:
    shop: rag
    description: "Advanced Q&A with caching and security"
    steps:
      # Security check
      - use: infrastructure.security
        config:
          subtechnique: injection_detection

      # Check cache
      - use: infrastructure.caching
        config:
          subtechnique: semantic
          ttl: 3600

      # Query processing
      - use: rag.query_processing
        config:
          subtechnique: decomposition

      # Retrieval with rate limiting
      - use: infrastructure.rate_limiting
        config:
          requests_per_minute: 60

      - use: rag.retrieval
        config:
          subtechnique: hybrid
          top_k: 10

      # Reranking
      - use: rag.reranking
        config:
          subtechnique: llm
          top_k: 3

      # Generation with consensus
      - use: ai_generation.consensus
        config:
          subtechnique: majority_vote
          num_generations: 3

      # Evaluation
      - use: infrastructure.evaluation
        config:
          subtechnique: rag_metrics
          metrics: [faithfulness, answer_relevance]
```

### Example 3: Multi-Step Workflow

```yaml
pipelines:
  research_workflow:
    shop: workflow_orchestration
    description: "Complex research workflow"
    steps:
      # Session management
      - use: workflow_orchestration.session_management
        config:
          subtechnique: memory
          timeout: 7200

      # Graph orchestration
      - use: workflow_orchestration.graph
        config:
          subtechnique: dag
          graph_definition:
            nodes:
              - id: query_expansion
                technique: rag.query_processing
                config:
                  subtechnique: expansion
                  num_queries: 5

              - id: parallel_search
                technique: rag.search
                config:
                  subtechnique: hybrid
                  top_k: 20

              - id: consolidate
                technique: rag.ranking
                config:
                  subtechnique: reciprocal_rank_fusion

              - id: generate_report
                technique: ai_generation.generation
                config:
                  subtechnique: structured
                  max_tokens: 4000

              - id: validate
                technique: ai_generation.validation
                config:
                  subtechnique: fact_check

            edges:
              - from: query_expansion
                to: parallel_search
              - from: parallel_search
                to: consolidate
              - from: consolidate
                to: generate_report
              - from: generate_report
                to: validate
```

## Technique Override Patterns

### Per-Pipeline Overrides

```yaml
shops:
  rag:
    enabled: true
    config:
      # Global defaults
      chunk_size: 512
      top_k: 5

pipelines:
  quick_search:
    steps:
      - use: rag.retrieval
        config:
          top_k: 3              # Override global setting

  deep_search:
    steps:
      - use: rag.retrieval
        config:
          top_k: 20             # Different override
```

### Conditional Configuration

```yaml
pipelines:
  adaptive_search:
    steps:
      - use: rag.retrieval
        config:
          subtechnique: |
            {%- if query_length > 100 -%}
              mmr
            {%- else -%}
              similarity
            {%- endif -%}
          top_k: |
            {%- if query_complexity == "simple" -%}
              3
            {%- else -%}
              10
            {%- endif -%}
```

## Best Practices

### 1. Start Simple

```yaml
# Good - start with basics
shops:
  rag:
    enabled: true

pipelines:
  simple_qa:
    steps:
      - use: rag.retrieval
      - use: ai_generation.generation
```

### 2. Add Complexity Gradually

```yaml
# Then add features as needed
pipelines:
  enhanced_qa:
    steps:
      - use: rag.query_processing      # Add query enhancement
      - use: rag.retrieval
      - use: rag.reranking              # Add reranking
      - use: ai_generation.generation
```

### 3. Use Appropriate Defaults

```yaml
# Set sensible shop-level defaults
shops:
  rag:
    config:
      chunk_size: 512          # Good for most documents
      top_k: 5                 # Balance quality/cost
      similarity_threshold: 0.7  # Filter low-quality results
```

### 4. Enable Observability

```yaml
# Always enable for production
shops:
  infrastructure:
    enabled: true
    config:
      evaluation:
        metrics: [accuracy, relevance]
      checkpointing:
        enabled: true
```

### 5. Implement Security

```yaml
# Enable security features
shops:
  infrastructure:
    config:
      security:
        pii_redaction: true
        prompt_injection_detection: true
```

## Troubleshooting

### Technique Not Found

```bash
# Error: Technique 'rag.unknown' not found

# Solution: Check technique name
sibyl pipeline validate --workspace config/workspaces/my_workspace.yaml
```

### Shop Not Enabled

```yaml
# Error: Shop 'rag' is not enabled

# Solution: Enable shop
shops:
  rag:
    enabled: true  # Add this
```

### Configuration Override Not Working

```yaml
# Problem: Shop-level config not being used

# Solution: Ensure technique uses shop config
steps:
  - use: rag.retrieval
    config:
      top_k: ${rag.top_k}  # Reference shop config
```

## Further Reading

- **[Technique Catalog](../techniques/catalog.md)** - Complete technique reference
- **[Provider Configuration](providers.md)** - Configure providers
- **[Configuration Guide](configuration.md)** - Complete workspace configuration
- **[Pipeline Patterns](../examples/pipeline-patterns.md)** - Common pipeline patterns

---

**Previous**: [Provider Configuration](providers.md) | **Next**: [MCP Tools Configuration](mcp-tools.md)

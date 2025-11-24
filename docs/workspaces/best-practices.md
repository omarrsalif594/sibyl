# Workspace Best Practices

Proven patterns and best practices for designing effective Sibyl workspaces.

## Workspace Organization

### Naming Conventions

```yaml
# Good - descriptive, environment-specific names
config/workspaces/
├── prod_docs_search.yaml          # Production document search
├── staging_code_analysis.yaml     # Staging code analysis
├── dev_local_docs.yaml            # Development local docs
└── test_rag_eval.yaml             # Testing RAG evaluation

# Bad - vague names
├── workspace1.yaml
├── my_workspace.yaml
├── test.yaml
```

**Pattern**: `{environment}_{purpose}_{provider}.yaml`

Examples:
- `prod_customer_support_pgvector.yaml`
- `dev_docs_duckdb.yaml`
- `staging_code_analysis_qdrant.yaml`

### Environment Separation

```yaml
# Development
config/workspaces/dev_docs.yaml:
  name: dev_docs
  providers:
    llm:
      primary:
        kind: ollama              # Free local LLM
    vector_store:
      main:
        kind: duckdb              # Embedded database

# Staging
config/workspaces/staging_docs.yaml:
  name: staging_docs
  providers:
    llm:
      primary:
        kind: openai
        model: gpt-3.5-turbo      # Cheaper model
    vector_store:
      main:
        kind: pgvector            # Production-like

# Production
config/workspaces/prod_docs.yaml:
  name: prod_docs
  providers:
    llm:
      primary:
        kind: openai
        model: gpt-4              # Best model
      fallback:
        kind: anthropic           # Fallback provider
    vector_store:
      main:
        kind: pgvector
        pool_size: 50             # Scaled
```

### Template Inheritance

```yaml
# config/workspaces/_base.yaml (template)
_template: true                   # Mark as template

providers:
  embedding:
    default:
      kind: sentence-transformer
      model: all-MiniLM-L6-v2

shops:
  rag:
    enabled: true
  ai_generation:
    enabled: true

observability:
  logging:
    level: INFO

---
# config/workspaces/prod_docs.yaml
extends: _base.yaml               # Inherit from base

name: prod_docs

providers:
  llm:                            # Add LLM provider
    primary:
      kind: openai
      model: gpt-4

  vector_store:                   # Add vector store
    main:
      kind: pgvector
      dsn: "${DATABASE_URL}"

pipelines:                        # Add pipelines
  search:
    shop: rag
    steps:
      - use: rag.retrieval
      - use: ai_generation.generation
```

## Provider Configuration Best Practices

### API Keys and Secrets

```yaml
# Good - use environment variables
providers:
  llm:
    primary:
      kind: openai
      api_key: "${OPENAI_API_KEY}"    # From environment

# Bad - never hardcode
providers:
  llm:
    primary:
      kind: openai
      api_key: "sk-..."                # NEVER!
```

**.env file**:
```bash
# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Vector Stores
DATABASE_URL=postgresql://...
QDRANT_URL=http://localhost:6333

# Configuration
WORKSPACE_ENV=production
LOG_LEVEL=INFO
```

### Multi-Provider Strategy

```yaml
providers:
  llm:
    # Primary provider
    primary:
      kind: openai
      model: gpt-4
      timeout: 60

    # Fallback for errors
    fallback:
      kind: anthropic
      model: claude-3-opus-20240229
      timeout: 120

    # Emergency offline provider
    emergency:
      kind: ollama
      model: llama2
      base_url: "http://localhost:11434"

  # Use primary by default, auto-fallback on failure
  fallback_chain: [primary, fallback, emergency]
```

### Connection Pooling

```yaml
providers:
  vector_store:
    main:
      kind: pgvector
      dsn: "${DATABASE_URL}"

      # Development
      pool_size: 5
      max_overflow: 2

      # Production
      # pool_size: 50
      # max_overflow: 10
      # pool_timeout: 30
      # pool_recycle: 3600
```

## Pipeline Design Patterns

### Single Responsibility

```yaml
# Good - focused pipelines
pipelines:
  index_documents:                # Only indexing
    shop: rag
    steps:
      - use: rag.chunking
      - use: rag.embedding
      - use: data.store_vectors

  search_documents:               # Only searching
    shop: rag
    steps:
      - use: rag.retrieval
      - use: ai_generation.generation

# Bad - does too much
pipelines:
  everything:
    steps:
      - use: rag.chunking
      - use: rag.embedding
      - use: data.store_vectors
      - use: rag.retrieval
      - use: ai_generation.generation
      - use: data.export
      - use: notifications.send
```

### Composable Pipelines

```yaml
pipelines:
  # Base pipelines
  retrieve:
    shop: rag
    steps:
      - use: rag.retrieval
        config:
          top_k: ${top_k}

  generate:
    shop: ai_generation
    steps:
      - use: ai_generation.generation
        config:
          provider: ${provider}

  # Composed pipeline
  qa:
    shop: rag
    steps:
      - use: rag.query_processing
      - pipeline: retrieve          # Reuse pipeline
        params:
          top_k: 5
      - pipeline: generate           # Reuse pipeline
        params:
          provider: primary
```

### Error Handling

```yaml
pipelines:
  robust_search:
    shop: rag
    steps:
      # Input validation
      - use: infrastructure.validation
        config:
          schema:
            query: { type: string, minLength: 1 }

      # Main logic with retries
      - use: rag.retrieval
        config:
          timeout: 30
          max_retries: 3
          retry_delay: 1.0

      # Fallback on error
      - use: rag.retrieval
        config:
          subtechnique: keyword      # Simpler fallback
        on_error: true               # Only run if previous failed

      # Always run cleanup
      - use: infrastructure.cleanup
        always: true                 # Run even on error
```

### Progressive Enhancement

```yaml
pipelines:
  # Basic version
  quick_search:
    shop: rag
    steps:
      - use: rag.retrieval
      - use: ai_generation.generation

  # Enhanced version
  enhanced_search:
    shop: rag
    steps:
      - use: rag.query_processing   # Add query enhancement
      - use: rag.retrieval
      - use: rag.reranking           # Add reranking
      - use: ai_generation.generation

  # Premium version
  premium_search:
    shop: rag
    steps:
      - use: infrastructure.caching  # Add caching
      - use: rag.query_processing
        config:
          subtechnique: decomposition  # Advanced processing
      - use: rag.retrieval
        config:
          top_k: 20
      - use: rag.reranking
        config:
          subtechnique: llm          # Better reranking
      - use: ai_generation.consensus # Multi-model consensus
      - use: infrastructure.evaluation
```

## Budget and Cost Management

### Budget Configuration

```yaml
budget:
  # Hard limits
  max_cost_usd: 100.0              # Stop at $100
  alert_threshold: 0.8             # Alert at 80%

  # Rate limits
  max_requests_per_hour: 1000
  max_tokens_per_day: 1000000

  # Cost tracking
  tracking:
    enabled: true
    granularity: pipeline          # Track per pipeline
    export_path: ./costs/

  # Notifications
  alerts:
    email: admin@example.com
    slack_webhook: "${SLACK_WEBHOOK}"
```

### Cost-Effective Provider Selection

```yaml
providers:
  llm:
    # Expensive for complex queries
    complex:
      kind: openai
      model: gpt-4                 # ~$0.03 per 1k tokens

    # Affordable for simple queries
    simple:
      kind: openai
      model: gpt-3.5-turbo         # ~$0.002 per 1k tokens

    # Free for development
    dev:
      kind: ollama
      model: llama2                # $0

  embedding:
    # Paid, highest quality
    openai:
      kind: openai
      model: text-embedding-3-large  # ~$0.0001 per 1k

    # Free, good quality
    local:
      kind: sentence-transformer
      model: all-mpnet-base-v2     # $0

pipelines:
  # Use cheaper model for simple queries
  simple_qa:
    steps:
      - use: ai_generation.generation
        config:
          provider: simple

  # Use expensive model only when needed
  complex_analysis:
    steps:
      - use: ai_generation.generation
        config:
          provider: complex
```

### Caching Strategy

```yaml
shops:
  infrastructure:
    config:
      caching:
        enabled: true
        backend: redis
        ttl: 3600                  # 1 hour

pipelines:
  search:
    steps:
      # Cache expensive operations
      - use: infrastructure.caching
        config:
          cache_key: "search:${query}"
          ttl: 3600

      - use: rag.retrieval        # Cached if hit

      - use: infrastructure.caching
        config:
          cache_key: "generation:${context}:${query}"
          ttl: 1800

      - use: ai_generation.generation  # Cached if hit
```

## Performance Optimization

### Batch Processing

```yaml
pipelines:
  batch_index:
    shop: rag
    steps:
      - use: rag.chunking
        config:
          batch_size: 100          # Process 100 docs at once

      - use: rag.embedding
        config:
          batch_size: 32           # Batch embeddings
          max_concurrent: 5        # Parallel batches

      - use: data.store_vectors
        config:
          batch_size: 1000         # Batch inserts
```

### Connection Pooling

```yaml
providers:
  vector_store:
    main:
      kind: pgvector
      pool_size: 20                # Concurrent connections
      max_overflow: 10             # Extra connections
      pool_timeout: 30             # Wait timeout
      pool_recycle: 3600           # Recycle connections
```

### Async Operations

```yaml
pipelines:
  parallel_search:
    shop: rag
    steps:
      # Run multiple searches in parallel
      - use: rag.search
        config:
          queries: [
            "machine learning",
            "neural networks",
            "deep learning"
          ]
          parallel: true           # Run in parallel
          max_concurrent: 3

      # Aggregate results
      - use: rag.ranking
        config:
          subtechnique: reciprocal_rank_fusion
```

### Index Optimization

```yaml
providers:
  vector_store:
    main:
      kind: pgvector
      dsn: "${DATABASE_URL}"

      # Index configuration
      index_type: hnsw             # Fast approximate search
      # index_type: ivfflat        # Balanced

      # HNSW parameters
      hnsw_ef_construction: 200    # Build quality
      hnsw_ef_search: 100          # Search quality
      hnsw_m: 16                   # Connections

      # IVFFlat parameters
      # lists: 100                 # Number of clusters
      # probes: 10                 # Search probes
```

## Security Best Practices

### PII Protection

```yaml
shops:
  infrastructure:
    config:
      security:
        pii_redaction: true
        pii_patterns:
          - email
          - phone
          - ssn
          - credit_card
        replacement: "[REDACTED]"

pipelines:
  secure_search:
    steps:
      # Redact PII from query
      - use: infrastructure.security
        config:
          subtechnique: pii_redaction

      - use: rag.retrieval

      # Redact PII from response
      - use: infrastructure.security
        config:
          subtechnique: pii_redaction
```

### Prompt Injection Protection

```yaml
shops:
  infrastructure:
    config:
      security:
        prompt_injection_detection: true
        injection_threshold: 0.8

pipelines:
  secure_qa:
    steps:
      # Detect injection attempts
      - use: infrastructure.security
        config:
          subtechnique: injection_detection

      # Only proceed if safe
      - use: rag.retrieval
        condition: ${security.is_safe}
```

### Access Control

```yaml
mcp:
  transport: http
  authentication:
    type: api_key
    header: X-API-Key
    keys:
      - "${API_KEY_ADMIN}"       # Full access
      - "${API_KEY_READONLY}"    # Read-only

  # Role-based access
  authorization:
    roles:
      admin:
        api_keys: ["${API_KEY_ADMIN}"]
        tools: ["*"]             # All tools

      readonly:
        api_keys: ["${API_KEY_READONLY}"]
        tools: ["search_*"]      # Only search tools
```

## Observability Best Practices

### Comprehensive Logging

```yaml
observability:
  logging:
    level: INFO                    # DEBUG in dev, INFO in prod
    format: json                   # Structured logging

    # Component-specific levels
    components:
      rag: DEBUG                   # Debug RAG pipeline
      llm: INFO                    # Info for LLM calls
      database: WARNING            # Only warnings for DB

    # File output
    file:
      enabled: true
      path: /var/log/sibyl/app.log
      rotation:
        max_bytes: 10485760        # 10MB
        backup_count: 10

    # Structured metadata
    metadata:
      environment: production
      version: "1.0.0"
      workspace: "${WORKSPACE_NAME}"
```

### Metrics Collection

```yaml
observability:
  metrics:
    enabled: true
    port: 9090
    path: /metrics

    # Custom metrics
    custom:
      - name: query_length
        type: histogram
        buckets: [10, 50, 100, 500, 1000]

      - name: retrieval_latency
        type: histogram
        buckets: [0.1, 0.5, 1.0, 2.0, 5.0]

      - name: generation_cost
        type: counter
        labels: [model, pipeline]
```

### Distributed Tracing

```yaml
observability:
  tracing:
    enabled: true
    exporter: jaeger
    endpoint: "http://jaeger:14268/api/traces"

    # Sampling
    sampling:
      type: probabilistic
      rate: 0.1                    # Sample 10%

    # Trace all pipelines
    pipelines: true

    # Custom spans
    custom_spans:
      - name: retrieval
        technique: rag.retrieval
      - name: generation
        technique: ai_generation.generation
```

## Testing and Validation

### Workspace Validation

```bash
# Always validate before deployment
sibyl workspace validate config/workspaces/prod_docs.yaml

# Check specific aspects
sibyl workspace validate --check providers config/workspaces/prod_docs.yaml
sibyl workspace validate --check pipelines config/workspaces/prod_docs.yaml
```

### Pipeline Testing

```yaml
# test/workspaces/test_pipelines.yaml
pipelines:
  test_search:
    shop: rag
    steps:
      - use: rag.retrieval
      - use: ai_generation.generation

    # Test configuration
    tests:
      - name: basic_search
        input:
          query: "test query"
        expect:
          output.answer: { type: string, minLength: 1 }

      - name: empty_query
        input:
          query: ""
        expect_error: "Query cannot be empty"
```

```bash
# Run tests
sibyl pipeline test --workspace config/workspaces/test_pipelines.yaml
```

### Integration Testing

```yaml
# test/integration/search_test.yaml
tests:
  - name: end_to_end_search
    steps:
      # Index documents
      - pipeline: index_documents
        params:
          source_path: ./test/data/docs

      # Search documents
      - pipeline: search_documents
        params:
          query: "machine learning"

      # Verify results
      - assert:
          - output.answer is not None
          - len(output.sources) >= 3
          - output.sources[0].score >= 0.7
```

## Common Anti-Patterns to Avoid

### ❌ Hardcoded Values

```yaml
# Bad
providers:
  llm:
    primary:
      api_key: "sk-..."            # Hardcoded secret

# Good
providers:
  llm:
    primary:
      api_key: "${OPENAI_API_KEY}" # Environment variable
```

### ❌ Over-Complex Pipelines

```yaml
# Bad - monolithic pipeline
pipelines:
  do_everything:
    steps:
      - use: step1
      - use: step2
      - use: step3
      - use: step4
      - use: step5
      # ... 20 more steps

# Good - composable pipelines
pipelines:
  index:
    steps: [...]

  search:
    steps: [...]

  generate:
    steps: [...]
```

### ❌ No Error Handling

```yaml
# Bad
pipelines:
  fragile:
    steps:
      - use: rag.retrieval        # What if this fails?
      - use: ai_generation.generation

# Good
pipelines:
  robust:
    steps:
      - use: rag.retrieval
        config:
          timeout: 30
          max_retries: 3

        on_error:
          - use: notifications.alert
          - pipeline: fallback_pipeline
```

### ❌ Missing Observability

```yaml
# Bad - no visibility
pipelines:
  mystery:
    steps:
      - use: rag.retrieval
      - use: ai_generation.generation

# Good - observable
pipelines:
  transparent:
    steps:
      - use: infrastructure.logging
        config:
          message: "Starting search for: ${query}"

      - use: rag.retrieval

      - use: infrastructure.metrics
        config:
          metric: retrieval_count
          value: ${retrieval.count}

      - use: ai_generation.generation
```

### ❌ No Budget Limits

```yaml
# Bad - unlimited costs
budget:
  max_cost_usd: null              # No limit!

# Good - controlled costs
budget:
  max_cost_usd: 1000.0
  alert_threshold: 0.8
  max_requests_per_hour: 1000
```

## Checklist for Production Workspaces

- [ ] All secrets in environment variables
- [ ] Multi-provider fallback configured
- [ ] Connection pooling enabled
- [ ] Budget limits set
- [ ] Logging configured
- [ ] Metrics enabled
- [ ] Error handling in all pipelines
- [ ] PII protection enabled
- [ ] Rate limiting configured
- [ ] Health checks enabled
- [ ] Workspace validated
- [ ] Pipelines tested
- [ ] Documentation updated

## Further Reading

- **[Configuration Guide](configuration.md)** - Complete configuration reference
- **[Provider Configuration](providers.md)** - Provider setup
- **[Shops and Techniques](shops-and-techniques.md)** - Technique configuration
- **[MCP Tools](mcp-tools.md)** - Tool exposure
- **[Security Guide](../operations/security.md)** - Security best practices

---

**Previous**: [MCP Tools Configuration](mcp-tools.md) | **Next**: [RAG Pipeline Guide](../techniques/rag-pipeline.md)

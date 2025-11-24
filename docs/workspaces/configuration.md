# Workspace Configuration Guide

Complete reference for configuring Sibyl workspaces.

## Configuration Schema

### Complete Workspace Template

```yaml
# ==============================================================================
# METADATA
# ==============================================================================
name: workspace_name              # Required: Unique workspace identifier
description: "Workspace description"  # Optional: Human-readable description
version: "1.0.0"                  # Optional: Semantic version
author: "Your Name"               # Optional: Workspace author
tags: ["tag1", "tag2"]           # Optional: Tags for organization

# ==============================================================================
# PROVIDERS
# ==============================================================================
providers:
  # LLM Providers
  llm:
    primary:                      # Provider name (arbitrary)
      kind: openai                # Required: Provider type
      model: gpt-4                # Required: Model name
      api_key: "${OPENAI_API_KEY}"  # Optional: API key (use env vars!)
      temperature: 0.7            # Optional: Sampling temperature (0.0-2.0)
      max_tokens: 2000            # Optional: Maximum tokens per request
      top_p: 1.0                  # Optional: Nucleus sampling
      frequency_penalty: 0.0      # Optional: Frequency penalty
      presence_penalty: 0.0       # Optional: Presence penalty

    fallback:                     # Optional: Fallback provider
      kind: anthropic
      model: claude-3-opus-20240229
      api_key: "${ANTHROPIC_API_KEY}"

  # Embedding Providers
  embedding:
    default:
      kind: sentence-transformer  # local, openai, fastembed
      model: all-MiniLM-L6-v2    # Model identifier
      device: cpu                 # cpu, cuda, mps
      batch_size: 32              # Batch size for encoding
      normalize: true             # Normalize embeddings

    openai_embeddings:
      kind: openai
      model: text-embedding-3-small
      api_key: "${OPENAI_API_KEY}"
      dimensions: 1536            # Optional: Embedding dimensions

  # Vector Store Providers
  vector_store:
    main_index:
      kind: duckdb                # duckdb, pgvector, qdrant, faiss
      dsn: "duckdb://./data/vectors.duckdb"
      collection_name: embeddings
      distance_metric: cosine     # cosine, euclidean, dot_product
      dimension: 384              # Must match embedding dimension

    pgvector_store:
      kind: pgvector
      dsn: "postgresql://user:pass@localhost:5432/db"
      collection_name: documents
      distance_metric: cosine
      pool_size: 20               # Connection pool size
      max_overflow: 10            # Max overflow connections
      pool_timeout: 30            # Pool timeout in seconds

    qdrant_store:
      kind: qdrant
      url: "http://localhost:6333"
      api_key: "${QDRANT_API_KEY}"  # Optional
      collection_name: vectors
      distance_metric: cosine
      on_disk: true               # Store on disk vs memory

  # Document Source Providers
  document_sources:
    local_markdown:
      type: filesystem_markdown
      config:
        root: ./docs              # Root directory
        pattern: "**/*.md"        # Glob pattern
        recursive: true           # Recurse into subdirectories
        ignore_patterns:          # Patterns to ignore
          - "node_modules/**"
          - ".git/**"
        max_file_size: 10485760   # Max file size (10MB)

  # SQL Data Providers
  sql:
    metadata_db:
      type: sqlite
      config:
        path: ./data/metadata.db
        timeout: 30.0

    postgres_db:
      type: postgresql
      config:
        dsn: "${POSTGRES_DSN}"
        pool_size: 10

# ==============================================================================
# SHOPS
# ==============================================================================
shops:
  # RAG Shop Configuration
  rag:
    enabled: true                 # Enable this shop
    config:                       # Shop-level defaults
      chunk_size: 512
      chunk_overlap: 50
      top_k: 5

    techniques:                   # Technique-specific config
      chunking:
        default_subtechnique: semantic
        config:
          chunk_size: 512
          chunk_overlap: 50
          min_chunk_size: 100
          max_chunk_size: 1000

      embedding:
        default_subtechnique: batch
        config:
          batch_size: 32
          provider: default       # Reference to embedding provider

      retrieval:
        default_subtechnique: hybrid
        config:
          vector_weight: 0.7
          keyword_weight: 0.3
          top_k: 10

      reranking:
        default_subtechnique: cross-encoder
        config:
          model: cross-encoder/ms-marco-MiniLM-L-6-v2
          top_k: 3

      query_processing:
        default_subtechnique: multi-query
        config:
          num_queries: 3

      augmentation:
        default_subtechnique: citation
        config:
          include_metadata: true
          include_citations: true

  # AI Generation Shop Configuration
  ai_generation:
    enabled: true
    techniques:
      generation:
        default_subtechnique: chain-of-thought
        config:
          provider: primary
          temperature: 0.7
          max_tokens: 2000

      consensus:
        default_subtechnique: quorum-voting
        config:
          num_responses: 3
          threshold: 0.6

      validation:
        default_subtechnique: quality-scoring
        config:
          min_quality_score: 0.7
          max_retries: 3

  # Workflow Shop Configuration
  workflow:
    enabled: true
    techniques:
      session_management:
        default_subtechnique: token-rotation
        config:
          max_tokens: 4000
          rotation_threshold: 0.8

      context_management:
        default_subtechnique: summarization
        config:
          max_context_tokens: 8000

      orchestration:
        default_subtechnique: sequential
        config:
          parallelism: 4

  # Infrastructure Shop Configuration
  infrastructure:
    enabled: true
    techniques:
      caching:
        default_subtechnique: semantic-cache
        config:
          cache_backend: redis
          ttl: 3600
          similarity_threshold: 0.95

      security:
        default_subtechnique: pii-redaction
        config:
          redact_pii: true
          detect_prompt_injection: true
          content_filter: true

      evaluation:
        default_subtechnique: faithfulness
        config:
          compute_metrics: true

# ==============================================================================
# PIPELINES
# ==============================================================================
pipelines:
  # Document Indexing Pipeline
  build_docs_index_from_markdown:
    shop: rag
    description: "Index markdown documents into vector store"
    timeout_s: 600                # Pipeline timeout
    budget:                       # Pipeline-specific budget
      max_cost_usd: 5.0
      max_tokens: 1000000
    steps:
      - use: data.load_documents
        config:
          source: local_markdown  # Reference to document source
        timeout_s: 60             # Step timeout

      - use: rag.chunking
        config:
          subtechnique: semantic
          chunk_size: 512
          chunk_overlap: 50

      - use: rag.embedding
        config:
          provider: default
          batch_size: 32

      - use: data.store_vectors
        config:
          vector_store: main_index

  # Question Answering Pipeline
  qa_over_docs:
    shop: rag
    description: "Answer questions over indexed documents"
    timeout_s: 120
    budget:
      max_cost_usd: 1.0
    steps:
      - use: rag.query_processing
        config:
          subtechnique: multi-query
          num_queries: 3

      - use: rag.retrieval
        config:
          vector_store: main_index
          top_k: 10

      - use: rag.reranking
        config:
          subtechnique: cross-encoder
          top_k: 3

      - use: rag.augmentation
        config:
          subtechnique: citation
          include_metadata: true

      - use: ai_generation.generation
        config:
          subtechnique: chain-of-thought
          provider: primary
          temperature: 0.7

  # Multi-Step Workflow Pipeline
  research_workflow:
    shop: workflow
    description: "Complex research workflow"
    timeout_s: 300
    steps:
      - use: workflow.orchestration
        config:
          subtechnique: parallel
          tasks:
            - pipeline: qa_over_docs
              params: {query: "Question 1"}
            - pipeline: qa_over_docs
              params: {query: "Question 2"}

      - use: ai_generation.consensus
        config:
          subtechnique: quorum-voting
          threshold: 0.6

# ==============================================================================
# BUDGET
# ==============================================================================
budget:
  max_cost_usd: 100.0             # Maximum USD spend
  max_tokens: 10000000            # Maximum tokens
  max_requests: 1000              # Maximum API requests
  tracking_enabled: true          # Enable budget tracking
  alert_threshold: 0.8            # Alert at 80% of budget

# ==============================================================================
# MCP (Model Context Protocol)
# ==============================================================================
mcp:
  enabled: true                   # Enable MCP server
  transport: stdio                # stdio or http
  port: 8000                      # Port for HTTP transport
  host: "0.0.0.0"                # Host for HTTP transport

  tools:                          # Exposed MCP tools
    - name: search_documents
      description: "Search indexed documents and answer questions"
      pipeline: qa_over_docs
      parameters:
        query:
          type: string
          description: "Question to answer"
          required: true
        top_k:
          type: integer
          description: "Number of results to return"
          default: 3
          minimum: 1
          maximum: 20

    - name: index_documents
      description: "Index new documents"
      pipeline: build_docs_index_from_markdown
      parameters:
        source_path:
          type: string
          description: "Path to documents"
          required: true

# ==============================================================================
# OBSERVABILITY
# ==============================================================================
observability:
  logging:
    level: INFO                   # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: json                  # json or text
    file: logs/workspace.log      # Log file path
    max_size: 104857600          # Max log file size (100MB)
    backup_count: 5               # Number of backup files
    console: true                 # Also log to console

  metrics:
    enabled: true
    backend: prometheus           # prometheus, statsd
    port: 9090
    path: /metrics
    push_gateway: null            # Optional push gateway URL

  tracing:
    enabled: true
    backend: opentelemetry        # opentelemetry, jaeger
    endpoint: "http://localhost:4318"
    service_name: sibyl
    sample_rate: 1.0              # 1.0 = 100% of traces

  health_checks:
    enabled: true
    port: 8001
    path: /health

# ==============================================================================
# SECURITY
# ==============================================================================
security:
  pii_redaction:
    enabled: true
    patterns:                     # Custom PII patterns
      - pattern: '\b\d{3}-\d{2}-\d{4}\b'  # SSN
        replacement: "[SSN]"
      - pattern: '\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'  # Email
        replacement: "[EMAIL]"

  content_filtering:
    enabled: true
    blocked_patterns: []          # Blocked content patterns

  prompt_injection:
    enabled: true
    detection_model: default

  access_control:
    enabled: false                # Enable RBAC
    roles:
      admin:
        pipelines: ["*"]
      user:
        pipelines: ["qa_over_docs"]

# ==============================================================================
# PERFORMANCE
# ==============================================================================
performance:
  caching:
    enabled: true
    backend: memory               # memory, redis, disk
    ttl: 3600                     # Cache TTL in seconds
    max_size: 1000                # Max cache entries

  connection_pooling:
    enabled: true
    pool_size: 10
    max_overflow: 5
    pool_timeout: 30

  batch_processing:
    enabled: true
    batch_size: 32
    max_batch_wait: 1.0           # Max wait time for batch

  async_execution:
    enabled: true
    max_concurrent_tasks: 10

# ==============================================================================
# EXTENSIONS
# ==============================================================================
extensions:
  plugins:                        # Custom plugins
    - name: custom_router
      path: plugins/custom_router
      config:
        routing_strategy: round-robin

  hooks:                          # Event hooks
    on_pipeline_start:
      - handler: log_pipeline_start
    on_pipeline_complete:
      - handler: log_pipeline_complete
    on_error:
      - handler: notify_error

# ==============================================================================
# EXPERIMENTAL FEATURES
# ==============================================================================
experimental:
  adaptive_retrieval: false       # Adaptive retrieval strategies
  auto_tuning: false              # Auto-tune parameters
  distributed_execution: false    # Distributed pipeline execution
```

## Configuration Sections

### 1. Metadata

Basic workspace information:

```yaml
name: my_workspace           # Unique identifier
description: "Description"   # What this workspace does
version: "1.0.0"            # Semantic version
author: "Your Name"
tags: ["production", "rag"]
```

### 2. Providers

Configure external services. See [Provider Configuration](providers.md) for details.

### 3. Shops

Enable and configure technique collections. See [Shops & Techniques](shops-and-techniques.md) for details.

### 4. Pipelines

Define execution workflows:

```yaml
pipelines:
  my_pipeline:
    shop: rag                 # Which shop
    description: "..."        # Description
    timeout_s: 300            # Timeout
    budget: {...}             # Budget
    steps:                    # Steps to execute
      - use: shop.technique
        config: {...}
```

### 5. Budget

Control resource usage:

```yaml
budget:
  max_cost_usd: 100.0        # USD limit
  max_tokens: 1000000        # Token limit
  max_requests: 1000         # Request limit
```

### 6. MCP

Expose tools through Model Context Protocol. See [MCP Tools](mcp-tools.md) for details.

### 7. Observability

Monitoring and logging:

```yaml
observability:
  logging:
    level: INFO
    format: json
  metrics:
    enabled: true
    port: 9090
  tracing:
    enabled: true
```

### 8. Security

Security settings:

```yaml
security:
  pii_redaction: true
  content_filtering: true
  prompt_injection_detection: true
```

## Environment Variables

### Usage

Reference environment variables with `${VAR_NAME}`:

```yaml
providers:
  llm:
    primary:
      api_key: "${OPENAI_API_KEY}"

  vector_store:
    main:
      dsn: "${DATABASE_URL}"
```

### Default Values

Provide defaults with `${VAR_NAME:-default}`:

```yaml
providers:
  vector_store:
    main:
      pool_size: ${POOL_SIZE:-10}  # Default: 10
      timeout: ${TIMEOUT:-30}      # Default: 30
```

### .env File

Create a `.env` file:

```bash
# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Databases
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Configuration
POOL_SIZE=20
TIMEOUT=60
LOG_LEVEL=INFO
```

## Validation

### Validate Configuration

```bash
sibyl workspace validate config/workspaces/my_workspace.yaml
```

### Validation Checks

- ✓ YAML syntax
- ✓ Required fields present
- ✓ Provider configurations valid
- ✓ Shop and technique references exist
- ✓ Pipeline syntax correct
- ✓ Budget values valid
- ✓ MCP tool definitions valid
- ✓ Environment variables resolved

### Common Errors

**Missing required field**:
```
Error: providers.llm.primary.kind is required
```

**Invalid provider type**:
```
Error: Unknown provider kind 'invalid_provider'
Valid options: openai, anthropic, ollama, local
```

**Circular pipeline reference**:
```
Error: Circular dependency in pipeline 'pipeline_a'
```

**Invalid budget value**:
```
Error: budget.max_cost_usd must be positive
```

## Best Practices

### 1. Use Environment Variables for Secrets

```yaml
# Good
api_key: "${OPENAI_API_KEY}"

# Bad
api_key: "sk-..."  # Never hardcode!
```

### 2. Set Appropriate Timeouts

```yaml
# Short timeout for quick operations
qa_over_docs:
  timeout_s: 60

# Longer timeout for batch processing
index_documents:
  timeout_s: 600
```

### 3. Configure Budgets

```yaml
# Development
budget:
  max_cost_usd: 1.0

# Production
budget:
  max_cost_usd: 100.0
  alert_threshold: 0.8  # Alert at 80%
```

### 4. Enable Observability

```yaml
observability:
  logging:
    level: INFO  # Not DEBUG in production
  metrics:
    enabled: true
  tracing:
    enabled: true
    sample_rate: 0.1  # 10% in production
```

### 5. Document Your Configuration

```yaml
pipelines:
  complex_pipeline:
    # This pipeline handles financial document analysis
    # chunk_size: 1024 - larger chunks for financial docs
    # top_k: 15 - more results for comprehensive analysis
    description: "Financial document analysis pipeline"
    steps: [...]
```

### 6. Use Descriptive Names

```yaml
# Good
providers:
  vector_store:
    financial_docs_pgvector:
      kind: pgvector

# Bad
providers:
  vector_store:
    vs1:
      kind: pgvector
```

### 7. Version Your Workspaces

```yaml
name: prod_financial_system
version: "2.1.0"  # Bump on breaking changes
```

## Examples

### Minimal Workspace

```yaml
name: minimal
providers:
  llm:
    primary:
      kind: openai
      model: gpt-3.5-turbo
shops:
  rag:
    enabled: true
pipelines:
  simple_qa:
    shop: rag
    steps:
      - use: rag.retrieval
      - use: ai_generation.generation
```

### Production Workspace

See complete example at top of this page.

### Multi-Environment

```yaml
# config/workspaces/base.yaml
name: base
providers: &providers
  llm:
    primary:
      kind: openai
      model: gpt-4

# config/workspaces/dev.yaml
name: dev
providers:
  <<: *providers  # Inherit from base
  llm:
    primary:
      model: gpt-3.5-turbo  # Override
budget:
  max_cost_usd: 1.0
```

## Troubleshooting

### Configuration Not Loading

```bash
# Check YAML syntax
yamllint config/workspaces/my_workspace.yaml

# Validate
sibyl workspace validate config/workspaces/my_workspace.yaml
```

### Environment Variables Not Resolved

```bash
# Check .env file location
ls -la .env

# Test environment variable
echo $OPENAI_API_KEY

# Load .env explicitly
export $(cat .env | xargs)
```

### Provider Connection Failed

```yaml
# Add connection pooling and timeouts
providers:
  vector_store:
    main:
      kind: pgvector
      dsn: "${DATABASE_URL}"
      pool_size: 20
      timeout: 30
      retry_attempts: 3
```

## Further Reading

- **[Workspace Overview](overview.md)** - Understanding workspaces
- **[Provider Configuration](providers.md)** - Configure providers
- **[Shops & Techniques](shops-and-techniques.md)** - Configure techniques
- **[MCP Tools](mcp-tools.md)** - Expose MCP tools
- **[Best Practices](best-practices.md)** - Design patterns

---

**Previous**: [Workspace Overview](overview.md) | **Next**: [Provider Configuration](providers.md)

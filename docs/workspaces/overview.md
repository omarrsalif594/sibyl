# Workspace Overview

Workspaces are the foundation of Sibyl's configuration system. Understanding workspaces is essential for effectively using Sibyl.

## What is a Workspace?

A workspace is a YAML configuration file that defines a complete execution environment for Sibyl. It specifies:

- **Providers**: Which LLMs, embeddings, and vector stores to use
- **Shops**: Which technique collections to enable
- **Pipelines**: Sequences of operations to perform
- **Budget Limits**: Resource constraints
- **MCP Configuration**: Tools exposed through Model Context Protocol
- **Observability**: Logging and monitoring settings

Think of a workspace as a **profile** or **environment** - you might have:
- `dev_local.yaml` - Development with local models
- `staging_cloud.yaml` - Staging with cloud services
- `prod_pgvector.yaml` - Production with PostgreSQL

## Workspace Structure

### Basic Workspace

```yaml
# Workspace metadata
name: my_workspace
description: "Description of this workspace"
version: "1.0.0"

# Provider configuration
providers:
  llm:
    primary:
      kind: openai
      model: gpt-4

  embedding:
    default:
      kind: sentence-transformer
      model: all-MiniLM-L6-v2

  vector_store:
    main:
      kind: duckdb
      dsn: "duckdb://./data/vectors.duckdb"

# Shop configuration
shops:
  rag:
    enabled: true

# Pipeline definitions
pipelines:
  my_pipeline:
    shop: rag
    steps:
      - use: rag.chunking
      - use: rag.embedding
```

### Complete Workspace

```yaml
# Metadata
name: production_workspace
description: "Production RAG system with pgvector"
version: "1.0.0"
author: "Your Team"
tags: ["production", "rag", "qa"]

# Provider configuration
providers:
  llm:
    primary:
      kind: openai
      model: gpt-4
      temperature: 0.7
      max_tokens: 2000
    fallback:
      kind: anthropic
      model: claude-3-opus-20240229

  embedding:
    default:
      kind: openai
      model: text-embedding-3-small
      dimensions: 1536

  vector_store:
    docs:
      kind: pgvector
      dsn: "postgresql://user:pass@localhost:5432/vectors"
      collection_name: documents
      distance_metric: cosine

  document_sources:
    local_docs:
      type: filesystem_markdown
      config:
        root: ./docs
        pattern: "**/*.md"

# Shop configuration
shops:
  rag:
    enabled: true
    config:
      chunk_size: 512
      chunk_overlap: 50
    techniques:
      chunking:
        default_subtechnique: semantic
      reranking:
        default_subtechnique: cross-encoder
        config:
          model: cross-encoder/ms-marco-MiniLM-L-6-v2

  ai_generation:
    enabled: true
    techniques:
      generation:
        default_subtechnique: chain-of-thought

# Pipeline definitions
pipelines:
  index_documents:
    shop: rag
    description: "Index markdown documents into vector store"
    timeout_s: 600
    budget:
      max_cost_usd: 5.0
    steps:
      - use: data.load_documents
        config:
          source: local_docs

      - use: rag.chunking
        config:
          subtechnique: semantic
          chunk_size: 512

      - use: rag.embedding

      - use: data.store_vectors
        config:
          vector_store: docs

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

      - use: rag.retrieval
        config:
          top_k: 10
          vector_store: docs

      - use: rag.reranking
        config:
          top_k: 3

      - use: rag.augmentation
        config:
          subtechnique: citation

      - use: ai_generation.generation
        config:
          subtechnique: chain-of-thought
          provider: primary

# Global budget limits
budget:
  max_cost_usd: 100.0
  max_tokens: 10000000
  max_requests: 1000

# MCP server configuration
mcp:
  enabled: true
  transport: stdio
  tools:
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
          description: "Number of results"
          default: 3

# Observability configuration
observability:
  logging:
    level: INFO
    format: json
    file: logs/workspace.log

  metrics:
    enabled: true
    port: 9090

  tracing:
    enabled: true
    endpoint: http://localhost:4318

# Security configuration
security:
  pii_redaction: true
  content_filtering: true
  prompt_injection_detection: true
```

## Workspace Locations

### Default Locations

Sibyl looks for workspaces in these locations:

1. **Command-line specified**:
   ```bash
   sibyl --workspace /path/to/workspace.yaml
   ```

2. **Environment variable**:
   ```bash
   export SIBYL_WORKSPACE_FILE=/path/to/workspace.yaml
   ```

3. **Current directory**:
   ```
   ./workspace.yaml
   ./sibyl_workspace.yaml
   ```

4. **Config directory**:
   ```
   ./config/workspace.yaml
   ./config/workspaces/<name>.yaml
   ```

5. **Home directory**:
   ```
   ~/.sibyl/workspace.yaml
   ~/.config/sibyl/workspace.yaml
   ```

### Organizing Workspaces

Recommended structure:

```
project/
├── config/
│   └── workspaces/
│       ├── dev_local_duckdb.yaml      # Local development
│       ├── dev_local_ollama.yaml      # Fully local (no API keys)
│       ├── staging_cloud.yaml         # Staging environment
│       ├── prod_pgvector.yaml         # Production with pgvector
│       ├── prod_qdrant.yaml           # Production with Qdrant
│       └── test_minimal.yaml          # Minimal for testing
├── .env                               # API keys
└── README.md
```

## Workspace Types

### 1. Development Workspace

For local development and testing:

```yaml
name: dev_local
description: "Local development with DuckDB"

providers:
  llm:
    primary:
      kind: openai
      model: gpt-3.5-turbo  # Cheaper for dev

  embedding:
    default:
      kind: sentence-transformer  # Free, local
      model: all-MiniLM-L6-v2
      device: cpu

  vector_store:
    main:
      kind: duckdb  # Embedded, no setup
      dsn: "duckdb://./data/dev_vectors.duckdb"

budget:
  max_cost_usd: 1.0  # Low limit for dev

observability:
  logging:
    level: DEBUG  # Verbose logging
```

### 2. Production Workspace

For production deployments:

```yaml
name: prod_pgvector
description: "Production with PostgreSQL and pgvector"

providers:
  llm:
    primary:
      kind: openai
      model: gpt-4
    fallback:
      kind: anthropic
      model: claude-3-opus-20240229

  embedding:
    default:
      kind: openai
      model: text-embedding-3-small

  vector_store:
    main:
      kind: pgvector
      dsn: "${DATABASE_URL}"  # From environment
      pool_size: 20
      max_overflow: 10

budget:
  max_cost_usd: 1000.0

observability:
  logging:
    level: INFO  # Less verbose
  metrics:
    enabled: true
  tracing:
    enabled: true
```

### 3. Testing Workspace

For automated testing:

```yaml
name: test_minimal
description: "Minimal workspace for testing"

providers:
  llm:
    primary:
      kind: mock  # Mock provider for tests

  embedding:
    default:
      kind: mock

  vector_store:
    main:
      kind: duckdb
      dsn: ":memory:"  # In-memory for tests

budget:
  max_cost_usd: 0.0  # No real API calls

observability:
  logging:
    level: ERROR  # Quiet during tests
```

### 4. Local-Only Workspace

No external API calls:

```yaml
name: local_only
description: "Completely local, no API keys needed"

providers:
  llm:
    primary:
      kind: ollama
      base_url: http://localhost:11434
      model: llama2

  embedding:
    default:
      kind: sentence-transformer
      model: all-MiniLM-L6-v2

  vector_store:
    main:
      kind: duckdb
      dsn: "duckdb://./data/vectors.duckdb"

# No budget needed - all free!
```

## Workspace Lifecycle

### 1. Load

```python
from sibyl.workspace import load_workspace

workspace = load_workspace("config/workspaces/my_workspace.yaml")
```

### 2. Validate

```bash
sibyl workspace validate config/workspaces/my_workspace.yaml
```

### 3. Initialize Runtime

```python
from sibyl.runtime import WorkspaceRuntime

runtime = WorkspaceRuntime(workspace)
```

### 4. Execute Pipelines

```python
result = await runtime.run_pipeline("my_pipeline", **params)
```

### 5. Cleanup

```python
await runtime.cleanup()
```

## Configuration Cascading

Configurations cascade from general to specific:

```
1. Workspace defaults (lowest priority)
   ↓
2. Shop configuration
   ↓
3. Technique defaults
   ↓
4. Pipeline step configuration
   ↓
5. Runtime parameters (highest priority)
```

**Example**:

```yaml
# Workspace level - applies to all
shops:
  rag:
    config:
      chunk_size: 512  # Default

# Pipeline level - overrides workspace
pipelines:
  large_docs:
    steps:
      - use: rag.chunking
        config:
          chunk_size: 1024  # Override

# Runtime - overrides all
runtime.run_pipeline("large_docs", chunk_size=2048)  # Override
```

## Environment Variables

Workspaces support environment variable substitution:

```yaml
providers:
  llm:
    primary:
      kind: openai
      api_key: "${OPENAI_API_KEY}"  # From .env

  vector_store:
    main:
      kind: pgvector
      dsn: "${DATABASE_URL}"
      pool_size: ${POOL_SIZE:-10}  # Default value
```

Load from `.env` file:

```bash
# .env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
POOL_SIZE=20
```

## Workspace Validation

Validate workspace before use:

```bash
# Validate configuration
sibyl workspace validate config/workspaces/my_workspace.yaml

# Output
✓ Workspace metadata valid
✓ All providers configured correctly
✓ All shops exist and are valid
✓ All pipelines are well-formed
✓ Budget configuration valid
✓ MCP configuration valid

Workspace is valid and ready to use!
```

Common validation errors:

- Missing required fields
- Invalid provider configurations
- Unknown technique references
- Circular pipeline dependencies
- Invalid budget values

## Workspace Templates

Sibyl includes 26+ workspace templates:

### By Use Case

**Document Q&A**:
- `local_docs_duckdb.yaml` - Local documents with DuckDB
- `local_docs_pgvector.yaml` - Local documents with PostgreSQL

**Web Research**:
- `web_research_openai.yaml` - Web research with OpenAI
- `web_research_anthropic.yaml` - Web research with Claude

**Code Analysis**:
- `code_analysis.yaml` - Code analysis and documentation

**Multi-Language**:
- `multilingual_rag.yaml` - Multi-language document processing

### By Provider

**OpenAI**:
- `cloud_openai.yaml` - Full OpenAI stack

**Anthropic**:
- `cloud_anthropic.yaml` - Claude-based system

**Local**:
- `local_ollama.yaml` - Completely local with Ollama

**Hybrid**:
- `hybrid_local_cloud.yaml` - Local embeddings, cloud LLM

## Best Practices

### 1. Use Environment-Specific Workspaces

```
config/workspaces/
├── dev.yaml
├── staging.yaml
└── prod.yaml
```

### 2. Never Commit API Keys

```yaml
# Good - use environment variables
api_key: "${OPENAI_API_KEY}"

# Bad - hardcoded
api_key: "sk-..."  # Never do this!
```

### 3. Set Reasonable Budgets

```yaml
budget:
  max_cost_usd: 1.0  # Development
  max_cost_usd: 100.0  # Production
```

### 4. Version Your Workspaces

```yaml
name: my_workspace
version: "1.2.0"  # Semantic versioning
```

### 5. Document Your Configuration

```yaml
pipelines:
  complex_pipeline:
    description: "Detailed description of what this pipeline does"
    # Why these specific settings:
    # - chunk_size: 512 works best for our document types
    # - top_k: 10 provides good coverage without noise
    steps:
      - use: rag.chunking
        config:
          chunk_size: 512
```

### 6. Use Descriptive Names

```yaml
# Good
name: prod_financial_docs_pgvector

# Bad
name: workspace1
```

### 7. Enable Observability in Production

```yaml
observability:
  logging:
    level: INFO
  metrics:
    enabled: true
  tracing:
    enabled: true
```

## Common Patterns

### Multi-Provider Fallback

```yaml
providers:
  llm:
    primary:
      kind: openai
      model: gpt-4
    fallback:
      kind: anthropic
      model: claude-3-opus-20240229
    emergency:
      kind: ollama
      model: llama2
```

### Multiple Vector Stores

```yaml
providers:
  vector_store:
    main_docs:
      kind: pgvector
      dsn: "${DATABASE_URL}"
      collection_name: documents

    code_index:
      kind: qdrant
      url: "${QDRANT_URL}"
      collection_name: code

    cache:
      kind: duckdb
      dsn: "duckdb://./cache.duckdb"
```

### Pipeline Composition

```yaml
pipelines:
  # Base pipeline
  basic_rag:
    shop: rag
    steps:
      - use: rag.retrieval
      - use: ai_generation.generation

  # Enhanced pipeline
  advanced_rag:
    shop: rag
    steps:
      - use: rag.query_processing  # Added
      - use: rag.retrieval
      - use: rag.reranking         # Added
      - use: rag.augmentation      # Added
      - use: ai_generation.generation
```

## Troubleshooting

### Workspace Won't Load

```bash
# Check syntax
yamllint config/workspaces/my_workspace.yaml

# Validate
sibyl workspace validate config/workspaces/my_workspace.yaml
```

### Provider Connection Errors

```yaml
# Add connection pooling
providers:
  vector_store:
    main:
      kind: pgvector
      dsn: "${DATABASE_URL}"
      pool_size: 10
      timeout_s: 30
```

### Pipeline Timeout

```yaml
# Increase timeout
pipelines:
  slow_pipeline:
    timeout_s: 600  # 10 minutes
    steps:
      - use: rag.chunking
        timeout_s: 120  # Per-step timeout
```

## Next Steps

- **[Configuration Guide](configuration.md)** - Complete configuration reference
- **[Provider Configuration](providers.md)** - Configure providers in detail
- **[Shops & Techniques](shops-and-techniques.md)** - Configure techniques
- **[Best Practices](best-practices.md)** - Workspace design patterns

---

**Previous**: [Architecture](../architecture/overview.md) | **Next**: [Configuration Guide](configuration.md)

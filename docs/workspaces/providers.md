# Provider Configuration

Complete reference for configuring providers in Sibyl workspaces.

## Overview

Providers are concrete implementations that interface with external services. Sibyl supports five types of providers:

1. **LLM Providers** - Language models
2. **Embedding Providers** - Text embeddings
3. **Vector Store Providers** - Vector search
4. **Document Source Providers** - Document retrieval
5. **SQL Data Providers** - Database operations

## LLM Providers

### OpenAI

```yaml
providers:
  llm:
    primary:
      kind: openai
      model: gpt-4                    # gpt-3.5-turbo, gpt-4, gpt-4-turbo
      api_key: "${OPENAI_API_KEY}"   # From environment
      temperature: 0.7                # 0.0-2.0
      max_tokens: 2000                # Max completion length
      top_p: 1.0                      # Nucleus sampling
      frequency_penalty: 0.0          # -2.0 to 2.0
      presence_penalty: 0.0           # -2.0 to 2.0
      timeout: 60                     # Request timeout (seconds)
      max_retries: 3                  # Retry attempts
```

**Available Models:**
- `gpt-4` - Most capable, slower, expensive
- `gpt-4-turbo` - Fast GPT-4 with 128k context
- `gpt-3.5-turbo` - Fast, affordable, good for most tasks
- `gpt-3.5-turbo-16k` - Extended context window

### Anthropic

```yaml
providers:
  llm:
    claude:
      kind: anthropic
      model: claude-3-opus-20240229   # Model identifier
      api_key: "${ANTHROPIC_API_KEY}"
      max_tokens: 4096
      temperature: 1.0
      top_p: 1.0
      timeout: 120
```

**Available Models:**
- `claude-3-opus-20240229` - Most capable
- `claude-3-sonnet-20240229` - Balanced performance/cost
- `claude-3-haiku-20240307` - Fast and affordable
- `claude-2.1` - Previous generation

### Ollama (Local LLMs)

```yaml
providers:
  llm:
    local:
      kind: ollama
      base_url: "http://localhost:11434"  # Ollama server
      model: llama2                       # Model name
      temperature: 0.7
      num_ctx: 4096                      # Context window
      timeout: 300                       # Longer for local
```

**Popular Models:**
- `llama2` - Meta's Llama 2
- `mistral` - Mistral 7B
- `codellama` - Code-specialized
- `vicuna` - Instruction-following

**Setup:**
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull models
ollama pull llama2
ollama pull mistral

# Start server
ollama serve
```

### Multi-Provider with Fallback

```yaml
providers:
  llm:
    primary:
      kind: openai
      model: gpt-4
      api_key: "${OPENAI_API_KEY}"

    fallback:
      kind: anthropic
      model: claude-3-opus-20240229
      api_key: "${ANTHROPIC_API_KEY}"

    emergency:
      kind: ollama
      model: llama2
      base_url: "http://localhost:11434"
```

## Embedding Providers

### Sentence Transformers (Local)

```yaml
providers:
  embedding:
    local:
      kind: sentence-transformer
      model: all-MiniLM-L6-v2         # Model identifier
      device: cpu                      # cpu, cuda, mps
      batch_size: 32                   # Batch encoding
      normalize: true                  # Normalize vectors
      max_seq_length: 512             # Max sequence length
```

**Popular Models:**
- `all-MiniLM-L6-v2` - Fast, 384 dimensions, good general purpose
- `all-mpnet-base-v2` - Higher quality, 768 dimensions
- `multi-qa-MiniLM-L6-cos-v1` - Optimized for Q&A
- `paraphrase-multilingual-MiniLM-L12-v2` - Multilingual

**Model Selection:**
```yaml
# Fast, small (384 dim)
model: all-MiniLM-L6-v2

# Better quality (768 dim)
model: all-mpnet-base-v2

# Multilingual support
model: paraphrase-multilingual-MiniLM-L12-v2
```

### OpenAI Embeddings

```yaml
providers:
  embedding:
    openai:
      kind: openai
      model: text-embedding-3-small   # Model
      api_key: "${OPENAI_API_KEY}"
      dimensions: 1536                # Output dimensions
      batch_size: 100                 # Batch size
      timeout: 30
```

**Available Models:**
- `text-embedding-3-small` - 1536 dim, affordable
- `text-embedding-3-large` - 3072 dim, highest quality
- `text-embedding-ada-002` - 1536 dim

### FastEmbed

```yaml
providers:
  embedding:
    fast:
      kind: fastembed
      model: BAAI/bge-small-en-v1.5   # Model identifier
      batch_size: 32
      cache_dir: ./cache/embeddings
```

## Vector Store Providers

### DuckDB (Development)

```yaml
providers:
  vector_store:
    dev:
      kind: duckdb
      dsn: "duckdb://./data/vectors.duckdb"
      collection_name: embeddings
      distance_metric: cosine         # cosine, euclidean, dot_product
      dimension: 384                  # Must match embedding dimension
      create_index: true              # Create HNSW index
```

**Use Cases:**
- Local development
- Prototyping
- Small-scale applications (<1M vectors)

### PostgreSQL with pgvector (Production)

```yaml
providers:
  vector_store:
    prod:
      kind: pgvector
      dsn: "postgresql://user:pass@localhost:5432/db"
      collection_name: documents
      distance_metric: cosine
      dimension: 1536
      pool_size: 20                   # Connection pool
      max_overflow: 10                # Max overflow
      pool_timeout: 30                # Pool timeout (seconds)
      index_type: ivfflat             # ivfflat, hnsw
      lists: 100                      # IVFFlat lists
      probes: 10                      # IVFFlat probes
```

**Setup:**
```sql
-- Install pgvector extension
CREATE EXTENSION vector;

-- Create table
CREATE TABLE embeddings (
    id TEXT PRIMARY KEY,
    embedding vector(1536),
    metadata JSONB
);

-- Create index
CREATE INDEX ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Use Cases:**
- Production deployments
- Large-scale applications (>1M vectors)
- Need for ACID transactions

### Qdrant (Vector Search Engine)

```yaml
providers:
  vector_store:
    qdrant:
      kind: qdrant
      url: "http://localhost:6333"    # Qdrant server URL
      api_key: "${QDRANT_API_KEY}"   # Optional
      collection_name: vectors
      distance_metric: cosine
      dimension: 384
      on_disk: true                   # Store on disk
      hnsw_config:                    # HNSW parameters
        m: 16                         # Connections per layer
        ef_construct: 100             # Construction quality
```

**Setup:**
```bash
# Docker
docker run -p 6333:6333 qdrant/qdrant

# Or install locally
# See: https://qdrant.tech/documentation/install/
```

**Use Cases:**
- High-performance vector search
- Advanced filtering
- Distributed deployments

### FAISS

```yaml
providers:
  vector_store:
    faiss:
      kind: faiss
      index_path: ./data/faiss.index
      dimension: 384
      index_type: IVF256,Flat        # Index configuration
      metric: cosine                  # cosine, euclidean, inner_product
      nprobe: 10                      # Search probes
```

**Use Cases:**
- Research and experimentation
- Custom index types
- CPU/GPU optimization

## Document Source Providers

### Filesystem Markdown

```yaml
providers:
  document_sources:
    local_docs:
      type: filesystem_markdown
      config:
        root: ./docs                  # Root directory
        pattern: "**/*.md"            # Glob pattern
        recursive: true               # Recurse subdirs
        ignore_patterns:              # Ignore patterns
          - "node_modules/**"
          - ".git/**"
          - "**/.DS_Store"
        max_file_size: 10485760      # 10MB max
        encoding: utf-8               # File encoding
        extract_title: true           # Extract from # headers
```

### Database Documents

```yaml
providers:
  document_sources:
    db_docs:
      type: database
      config:
        connection: "${DATABASE_URL}"
        table: documents
        id_column: id
        content_column: content
        metadata_columns:
          - title
          - author
          - created_at
```

## SQL Data Providers

### SQLite

```yaml
providers:
  sql:
    local_db:
      type: sqlite
      config:
        path: ./data/metadata.db
        timeout: 30.0                 # Busy timeout
        check_same_thread: false      # Thread safety
```

### PostgreSQL

```yaml
providers:
  sql:
    postgres:
      type: postgresql
      config:
        dsn: "${POSTGRES_DSN}"
        pool_size: 10
        max_overflow: 5
        pool_timeout: 30
        echo: false                   # SQL logging
```

## Provider Selection Guidelines

### LLM Provider Selection

**Choose OpenAI if:**
- Need latest GPT-4 capabilities
- Want reliable, fast responses
- Budget allows (~$0.01-0.03 per 1k tokens)

**Choose Anthropic if:**
- Need long context (200k tokens)
- Want strong safety features
- Prefer Claude's style

**Choose Ollama if:**
- Want zero API costs
- Need data privacy
- Have sufficient local compute
- Can accept slower responses

### Embedding Provider Selection

**Choose Sentence Transformers if:**
- Want zero API costs
- Need offline capability
- OK with slightly lower quality
- Have CPU/GPU resources

**Choose OpenAI if:**
- Want highest quality
- Budget allows (~$0.0001 per 1k tokens)
- Need consistency with OpenAI LLM

**Choose FastEmbed if:**
- Want fast local embeddings
- Need specific model support
- Want easy deployment

### Vector Store Selection

**Choose DuckDB if:**
- Development/prototyping
- < 1M vectors
- Single-machine deployment
- No setup required

**Choose pgvector if:**
- Production deployment
- > 1M vectors
- Need ACID transactions
- Already using PostgreSQL

**Choose Qdrant if:**
- > 10M vectors
- Need advanced filtering
- Want distributed deployment
- High performance required

**Choose FAISS if:**
- Research/experimentation
- Custom index requirements
- GPU acceleration needed

## Environment Variables

### Best Practices

```yaml
# Good - use environment variables
providers:
  llm:
    primary:
      api_key: "${OPENAI_API_KEY}"

# Bad - never hardcode
providers:
  llm:
    primary:
      api_key: "sk-..."  # NEVER!
```

### .env File

```bash
# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Vector Stores
DATABASE_URL=postgresql://...
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...

# Optional
POOL_SIZE=20
TIMEOUT=60
```

### Loading Environment Variables

```bash
# Load from .env
export $(cat .env | xargs)

# Or use python-dotenv
# Automatically loaded by Sibyl
```

## Provider Pooling and Performance

### Connection Pooling

```yaml
providers:
  vector_store:
    prod:
      kind: pgvector
      dsn: "${DATABASE_URL}"
      pool_size: 20               # Concurrent connections
      max_overflow: 10            # Extra connections
      pool_timeout: 30            # Wait timeout
      pool_recycle: 3600          # Recycle after 1 hour
```

### Batch Processing

```yaml
providers:
  embedding:
    openai:
      kind: openai
      batch_size: 100             # Process 100 at a time
      max_concurrent: 5           # Max parallel batches
```

### Timeouts and Retries

```yaml
providers:
  llm:
    primary:
      kind: openai
      timeout: 60                 # Request timeout
      max_retries: 3              # Retry attempts
      retry_delay: 1.0            # Delay between retries
      exponential_backoff: true   # Exponential backoff
```

## Troubleshooting

### Provider Connection Failed

```yaml
# Add retries and timeouts
providers:
  llm:
    primary:
      kind: openai
      timeout: 120                # Longer timeout
      max_retries: 5              # More retries
```

### API Rate Limits

```yaml
# Add rate limiting
providers:
  llm:
    primary:
      kind: openai
      rate_limit:
        requests_per_minute: 60
        tokens_per_minute: 90000
```

### Vector Store Performance

```yaml
# Optimize connection pool
providers:
  vector_store:
    main:
      kind: pgvector
      pool_size: 50               # More connections
      index_type: hnsw            # Faster index
```

## Further Reading

- **[Workspace Overview](overview.md)** - Understanding workspaces
- **[Configuration Guide](configuration.md)** - Complete configuration
- **[Shops & Techniques](shops-and-techniques.md)** - Configure techniques
- **[Best Practices](best-practices.md)** - Design patterns

---

**Previous**: [Configuration Guide](configuration.md) | **Next**: [Shops & Techniques](shops-and-techniques.md)

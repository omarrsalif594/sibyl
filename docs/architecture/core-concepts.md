# Core Concepts

Understanding Sibyl's core concepts is essential for effectively using and extending the platform.

## Overview

Sibyl is built around five fundamental concepts:

1. **Protocols** - Abstract interfaces defining contracts
2. **Providers** - Concrete implementations of protocols
3. **Techniques** - Modular AI processing components
4. **Shops** - Collections of related techniques
5. **Workspaces** - Configuration environments
6. **Pipelines** - Orchestrated sequences of techniques

## Protocols

### What are Protocols?

Protocols are abstract interfaces that define contracts for implementations. They specify what methods a class must implement without dictating how.

**Example**:

```python
from typing import Protocol

class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion from prompt."""
        ...

    async def complete_async(self, prompt: str, **kwargs) -> str:
        """Async completion generation."""
        ...
```

### Why Protocols?

- **Interchangeability**: Swap implementations without code changes
- **Type Safety**: Catch errors at development time
- **Testability**: Easy to mock for testing
- **Extensibility**: Add new implementations easily

### Key Protocols

- **`LLMProvider`**: Language model interface
- **`EmbeddingProvider`**: Text embedding interface
- **`VectorStoreProvider`**: Vector storage and search
- **`DocumentSourceProvider`**: Document retrieval
- **`SQLDataProvider`**: Database operations
- **`TechniqueProtocol`**: Base for all techniques

**Location**: `sibyl/core/protocols/`

## Providers

### What are Providers?

Providers are concrete implementations of protocols that interact with specific technologies or services.

**Example**:

```python
from sibyl.core.protocols import LLMProvider

class OpenAIProvider:
    """OpenAI LLM provider implementation."""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=api_key)

    def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion using OpenAI."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message.content

    async def complete_async(self, prompt: str, **kwargs) -> str:
        """Async version."""
        # Async implementation
        ...
```

### Provider Categories

#### 1. LLM Providers

Interact with language models:

- **OpenAI**: GPT-3.5, GPT-4, GPT-4 Turbo
- **Anthropic**: Claude, Claude Instant, Claude 2
- **Ollama**: Local LLMs (Llama 2, Mistral, etc.)
- **Local**: Direct local model integration

**Configuration**:

```yaml
providers:
  llm:
    primary:
      kind: openai
      model: gpt-4
      temperature: 0.7
      max_tokens: 2000
```

#### 2. Embedding Providers

Generate text embeddings:

- **Sentence Transformers**: Local embedding models
- **OpenAI**: text-embedding-ada-002, text-embedding-3-small
- **FastEmbed**: Fast local embeddings
- **Cohere**: Cohere embedding models

**Configuration**:

```yaml
providers:
  embedding:
    default:
      kind: sentence-transformer
      model: all-MiniLM-L6-v2
      device: cpu
```

#### 3. Vector Store Providers

Store and search vector embeddings:

- **DuckDB**: Embedded vector database (development)
- **pgvector**: PostgreSQL extension (production)
- **Qdrant**: Dedicated vector search engine
- **FAISS**: Facebook AI similarity search

**Configuration**:

```yaml
providers:
  vector_store:
    docs_index:
      kind: duckdb
      dsn: "duckdb://./data/vectors.duckdb"
      collection_name: embeddings
      distance_metric: cosine
      dimension: 384
```

#### 4. Document Source Providers

Retrieve documents from various sources:

- **Filesystem Markdown**: Local markdown files
- **Database**: SQL database documents
- **API**: External API documents
- **Cloud Storage**: S3, GCS, Azure Blob

**Configuration**:

```yaml
providers:
  document_sources:
    local_docs:
      type: filesystem_markdown
      config:
        root: ./docs
        pattern: "**/*.md"
        recursive: true
```

#### 5. SQL Data Providers

Database operations:

- **SQLite**: Lightweight embedded database
- **PostgreSQL**: Production-grade relational database
- **MySQL**: Alternative relational database

**Configuration**:

```yaml
providers:
  sql:
    metadata_db:
      type: sqlite
      config:
        path: ./data/metadata.db
```

### Provider Factory Pattern

Providers are instantiated through factory functions:

```python
def create_llm_provider(config: dict) -> LLMProvider:
    """Factory function for LLM providers."""
    kind = config["kind"]

    if kind == "openai":
        return OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=config.get("model", "gpt-4")
        )
    elif kind == "anthropic":
        return AnthropicProvider(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model=config.get("model", "claude-3-opus-20240229")
        )
    elif kind == "ollama":
        return OllamaProvider(
            base_url=config.get("base_url", "http://localhost:11434"),
            model=config.get("model", "llama2")
        )
    else:
        raise ValueError(f"Unknown LLM provider: {kind}")
```

## Techniques

### What are Techniques?

Techniques are modular AI processing components that perform specific tasks. Each technique can have multiple implementations called subtechniques.

**Example**:

```python
from sibyl.techniques.base import BaseTechnique

class ChunkingTechnique(BaseTechnique):
    """Technique for chunking documents into smaller segments."""

    async def execute(
        self,
        input_data: dict,
        config: ChunkConfig,
        subtechnique: str = "fixed-size"
    ) -> dict:
        """Execute chunking on documents."""
        documents = input_data["documents"]

        # Delegate to subtechnique
        chunker = self.get_subtechnique(subtechnique)
        chunks = await chunker.chunk(documents, config)

        return {
            "chunks": chunks,
            "metadata": {
                "total_chunks": len(chunks),
                "subtechnique_used": subtechnique
            }
        }
```

### Technique Structure

Each technique follows a standard structure:

```
technique/
├── __init__.py
├── README.md              # Documentation
├── base.py                # Base technique class
├── config.py              # Configuration schemas
└── subtechniques/         # Alternative implementations
    ├── fixed_size/
    │   └── technique.py
    ├── semantic/
    │   └── technique.py
    └── markdown/
        └── technique.py
```

### Subtechniques

Subtechniques provide alternative implementations for the same task:

**Example - Chunking Subtechniques**:

1. **Fixed-size**: Split by character/token count
2. **Semantic**: Split by meaning using embeddings
3. **Markdown**: Split by markdown structure (headers, sections)
4. **SQL**: Split SQL code by statements

**Usage**:

```python
# Use different chunking strategies
result = await chunking.execute(
    input_data,
    config=config,
    subtechnique="semantic"  # or "fixed-size", "markdown", etc.
)
```

### Technique Categories

Techniques are organized by domain:

1. **RAG Pipeline Techniques**
   - Chunking, embedding, retrieval, reranking
   - Query processing, augmentation

2. **AI Generation Techniques**
   - Generation strategies, consensus, validation

3. **Workflow Orchestration Techniques**
   - Session management, context management, graph execution

4. **Infrastructure Techniques**
   - Caching, security, evaluation, optimization

## Shops

### What are Shops?

Shops are collections of related techniques organized by domain. They provide a namespace and runtime context for techniques.

**Example**:

```python
class RAGShop:
    """Shop for RAG pipeline techniques."""

    def __init__(self):
        self.techniques = {
            "chunking": ChunkingTechnique(),
            "embedding": EmbeddingTechnique(),
            "retrieval": RetrievalTechnique(),
            "reranking": RerankingTechnique(),
            "synthesis": SynthesisTechnique(),
        }

    async def execute_technique(
        self,
        technique_name: str,
        input_data: dict,
        config: dict
    ) -> dict:
        """Execute a technique from this shop."""
        technique = self.techniques[technique_name]
        return await technique.execute(input_data, config)
```

### Available Shops

#### 1. RAG Shop

**Purpose**: Document processing and retrieval-augmented generation

**Techniques**:
- `chunking`: Split documents into chunks
- `embedding`: Generate embeddings
- `search`: Vector/keyword/hybrid search
- `retrieval`: Retrieve relevant documents
- `ranking`: Rank retrieved documents
- `reranking`: Re-rank with advanced models
- `augmentation`: Add metadata, citations, context
- `query_processing`: Expand, rewrite, decompose queries

**Location**: `sibyl/shops/rag/`

#### 2. AI Generation Shop

**Purpose**: Content generation and quality control

**Techniques**:
- `generation`: Generate content (CoT, ReAct, ToT)
- `consensus`: Combine multiple generations
- `validation`: Validate output quality
- `voting`: Vote on best generation

**Location**: `sibyl/shops/ai_generation/`

#### 3. Workflow Shop

**Purpose**: Orchestration and execution control

**Techniques**:
- `session_management`: Manage conversation sessions
- `context_management`: Handle context windows
- `graph`: Graph-based workflow execution
- `orchestration`: Coordinate multiple steps

**Location**: `sibyl/shops/workflow/`

#### 4. Infrastructure Shop

**Purpose**: Cross-cutting concerns

**Techniques**:
- `caching`: Multi-level caching
- `security`: PII redaction, content filtering, prompt injection detection
- `evaluation`: Quality metrics (faithfulness, relevance, groundedness)
- `workflow_optimization`: Adaptive retrieval, cost optimization
- `checkpointing`: Save and resume state
- `learning`: Pattern learning and feedback

**Location**: `sibyl/shops/infrastructure/`

### Shop Runtime

Shops have runtime contexts that manage:

- Technique initialization
- Configuration cascading
- State management
- Observability

**Example**:

```python
from sibyl.runtime import ShopRuntime

# Initialize shop runtime
shop_runtime = ShopRuntime(
    shop=rag_shop,
    config=workspace.shops["rag"]
)

# Execute technique
result = await shop_runtime.execute(
    technique="chunking",
    subtechnique="semantic",
    input_data=documents,
    config={"chunk_size": 512}
)
```

## Workspaces

### What are Workspaces?

Workspaces are YAML configuration files that define complete execution environments. They specify providers, shops, pipelines, and settings.

**Example Workspace**:

```yaml
name: local_docs_duckdb
description: "Local document Q&A with DuckDB vector store"

# Provider configuration
providers:
  llm:
    primary:
      kind: openai
      model: gpt-4
      temperature: 0.7

  embedding:
    default:
      kind: sentence-transformer
      model: all-MiniLM-L6-v2

  vector_store:
    docs_index:
      kind: duckdb
      dsn: "duckdb://./data/vectors.duckdb"
      collection_name: embeddings

# Shop configuration
shops:
  rag:
    enabled: true
    techniques:
      chunking:
        default_subtechnique: semantic
        config:
          chunk_size: 512
          chunk_overlap: 50

      reranking:
        default_subtechnique: cross-encoder
        config:
          model: cross-encoder/ms-marco-MiniLM-L-6-v2

# Pipeline definitions
pipelines:
  build_docs_index:
    shop: rag
    description: "Index markdown documents"
    steps:
      - use: rag.chunking
        config:
          subtechnique: semantic

      - use: rag.embedding

      - use: data.store_vectors
        config:
          vector_store: docs_index

  qa_over_docs:
    shop: rag
    description: "Question answering over documents"
    steps:
      - use: rag.query_processing
        config:
          subtechnique: multi-query

      - use: rag.retrieval
        config:
          top_k: 5

      - use: rag.reranking

      - use: ai_generation.generation
        config:
          subtechnique: chain-of-thought

# Budget limits
budget:
  max_cost_usd: 10.0
  max_tokens: 1000000

# MCP server configuration
mcp:
  enabled: true
  tools:
    - name: search_documents
      description: "Search indexed documents"
      pipeline: qa_over_docs
```

### Workspace Components

#### 1. Metadata

```yaml
name: workspace_name
description: "Workspace description"
version: "1.0.0"
```

#### 2. Providers

Define external service connections:

```yaml
providers:
  llm:
    primary: {...}
    fallback: {...}
  embedding:
    default: {...}
  vector_store:
    main: {...}
```

#### 3. Shops

Configure shop behavior:

```yaml
shops:
  rag:
    enabled: true
    techniques:
      chunking:
        default_subtechnique: semantic
        config: {...}
```

#### 4. Pipelines

Define execution sequences:

```yaml
pipelines:
  my_pipeline:
    shop: rag
    description: "Pipeline description"
    timeout_s: 300
    steps:
      - use: rag.chunking
      - use: rag.embedding
```

#### 5. Budget

Resource limits:

```yaml
budget:
  max_cost_usd: 1.0
  max_tokens: 100000
  max_requests: 50
```

#### 6. MCP Configuration

Expose tools:

```yaml
mcp:
  enabled: true
  transport: stdio  # or http
  tools:
    - name: tool_name
      pipeline: pipeline_name
```

### Workspace Lifecycle

```
Load YAML → Parse Config → Validate → Initialize Providers
    ↓
Load Shops → Initialize Techniques → Ready for Execution
```

### Configuration Cascading

Configuration follows a hierarchy:

```
1. Workspace defaults (lowest priority)
   ↓
2. Shop configuration
   ↓
3. Technique defaults
   ↓
4. Pipeline step config
   ↓
5. Runtime overrides (highest priority)
```

**Example**:

```yaml
# Workspace level (applies to all)
shops:
  rag:
    config:
      chunk_size: 512  # Default for all chunking

# Pipeline level (overrides workspace)
pipelines:
  my_pipeline:
    steps:
      - use: rag.chunking
        config:
          chunk_size: 1024  # Overrides workspace default
```

## Pipelines

### What are Pipelines?

Pipelines are orchestrated sequences of technique executions that transform data and produce results.

**Example**:

```yaml
pipelines:
  rag_pipeline:
    shop: rag
    description: "Complete RAG pipeline"
    timeout_s: 300
    steps:
      # Step 1: Load documents
      - use: data.load_documents
        config:
          source: local_docs

      # Step 2: Chunk documents
      - use: rag.chunking
        config:
          subtechnique: semantic
          chunk_size: 512

      # Step 3: Generate embeddings
      - use: rag.embedding

      # Step 4: Store in vector database
      - use: data.store_vectors
        config:
          vector_store: docs_index
```

### Pipeline Execution

Pipelines execute sequentially by default:

```
Input → Step 1 → Step 2 → Step 3 → ... → Output
```

Each step:
1. Receives output from previous step
2. Executes technique with configuration
3. Produces output for next step
4. Tracks budget and time

### Data Flow

```python
# Initial input
input_data = {"query": "What is Sibyl?"}

# Step 1 output becomes Step 2 input
step1_output = await execute_step1(input_data)
# {"query": "What is Sibyl?", "expanded_queries": [...]}

# Step 2 output becomes Step 3 input
step2_output = await execute_step2(step1_output)
# {"query": "...", "retrieved_docs": [...]}

# Final output
final_output = await execute_step3(step2_output)
# {"answer": "Sibyl is...", "sources": [...]}
```

### Pipeline Configuration

```yaml
pipelines:
  my_pipeline:
    shop: rag                    # Which shop provides techniques
    description: "Description"   # Human-readable description
    timeout_s: 300               # Maximum execution time
    budget:                      # Per-pipeline budget
      max_cost_usd: 1.0
    steps:
      - use: shop.technique      # Technique reference
        config:                  # Step-specific config
          param: value
        timeout_s: 60            # Per-step timeout
```

### Running Pipelines

**Via CLI**:

```bash
sibyl pipeline run \
  --workspace config/workspaces/my_workspace.yaml \
  --pipeline my_pipeline \
  --param key=value
```

**Via Python API**:

```python
from sibyl.runtime import load_workspace_runtime

runtime = load_workspace_runtime("config/workspaces/my_workspace.yaml")
result = await runtime.run_pipeline("my_pipeline", param=value)
```

**Via MCP**:

```python
# Exposed as MCP tool
# Claude Desktop can call it automatically
```

## Putting It All Together

Here's how the concepts interact:

```
┌─────────────────────────────────────────┐
│           Workspace YAML                │
│  Defines: Providers, Shops, Pipelines  │
└──────────────┬──────────────────────────┘
               ↓
┌──────────────────────────────────────────┐
│         Provider Initialization          │
│  Protocols → Factories → Provider Instances
└──────────────┬───────────────────────────┘
               ↓
┌──────────────────────────────────────────┐
│          Shop Initialization             │
│  Load Techniques with Subtechniques      │
└──────────────┬───────────────────────────┘
               ↓
┌──────────────────────────────────────────┐
│        Pipeline Execution                │
│  Step 1 → Step 2 → Step 3 → ...         │
│  (Each step uses Techniques from Shops)  │
└──────────────┬───────────────────────────┘
               ↓
┌──────────────────────────────────────────┐
│         Technique Execution              │
│  Uses Providers to interact with services│
└──────────────────────────────────────────┘
```

## Key Takeaways

1. **Protocols** define what something should do
2. **Providers** implement protocols for specific technologies
3. **Techniques** are modular processing components
4. **Shops** organize related techniques
5. **Workspaces** configure the entire environment
6. **Pipelines** orchestrate technique execution

Understanding these concepts enables you to:
- Configure Sibyl for your use case
- Extend Sibyl with custom components
- Debug and optimize pipelines
- Build sophisticated AI applications

## Further Reading

- **[Architecture Overview](overview.md)** - System architecture
- **[Data Flow](data-flow.md)** - How data moves through Sibyl
- **[Workspace Configuration](../workspaces/configuration.md)** - Detailed workspace guide
- **[Techniques Catalog](../techniques/catalog.md)** - Browse all techniques

---

**Next**: [Data Flow](data-flow.md) | [Design Patterns](design-patterns.md)

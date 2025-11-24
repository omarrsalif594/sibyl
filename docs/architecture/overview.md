# Architecture Overview

Sibyl is built on a clean, layered architecture that separates concerns and promotes modularity, extensibility, and testability.

## Architectural Principles

Sibyl's architecture follows these key principles:

1. **Separation of Concerns**: Each layer has a specific responsibility
2. **Dependency Inversion**: High-level modules don't depend on low-level modules
3. **Protocol-Oriented Design**: Interfaces defined as protocols, implementations as providers
4. **Composition over Inheritance**: Techniques composed from smaller, reusable components
5. **Configuration as Code**: YAML workspaces define behavior declaratively

## Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Application Layer                      │
│         (CLI, REST API, MCP Server)                     │
├─────────────────────────────────────────────────────────┤
│                   Runtime Layer                         │
│     (Orchestration, Budget Tracking, Observability)     │
├─────────────────────────────────────────────────────────┤
│                  Technique Layer                        │
│      (RAG, AI Generation, Workflow, Infrastructure)     │
├─────────────────────────────────────────────────────────┤
│                  Provider Layer                         │
│        (LLM, Embeddings, Vector Stores, Documents)      │
├─────────────────────────────────────────────────────────┤
│                  Protocol Layer                         │
│         (Abstract interfaces and contracts)             │
└─────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### Protocol Layer

At the foundation, Sibyl defines protocol interfaces for all major components. These protocols establish contracts that implementations must follow, enabling interchangeability and testability.

**Key Protocols**:

- **`LLMProvider`**: Interface for language model interactions
- **`EmbeddingProvider`**: Interface for generating text embeddings
- **`VectorStoreProvider`**: Interface for vector similarity search
- **`DocumentSourceProvider`**: Interface for reading documents from various sources
- **`SQLDataProvider`**: Interface for database operations
- **`TechniqueProtocol`**: Base interface for all techniques

**Location**: `sibyl/core/protocols/`

**Example**:

```python
class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    def complete(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate completion from prompt."""
        ...

    async def complete_async(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Async completion generation."""
        ...
```

### Provider Layer

The provider layer implements the protocol interfaces for specific technologies. Providers are the concrete implementations that interact with external services, databases, and data sources.

**Provider Categories**:

1. **Document Source Providers**
   - `FilesystemMarkdownSource`: Reads markdown files from filesystem
   - Extensible for databases, APIs, cloud storage

2. **Vector Store Providers**
   - `DuckDBVectorStore`: Embedded vector database using DuckDB
   - `PgVectorStore`: PostgreSQL with pgvector extension
   - `QdrantVectorStore`: Dedicated vector search engine
   - `FAISSVectorStore`: FAISS-based vector search

3. **LLM Providers**
   - `OpenAIProvider`: OpenAI GPT models
   - `AnthropicProvider`: Anthropic Claude models
   - `OllamaProvider`: Local LLMs via Ollama
   - `LocalLLMProvider`: Direct local model integration

4. **Embedding Providers**
   - `SentenceTransformerProvider`: Local embedding models
   - `OpenAIEmbeddingProvider`: OpenAI text-embedding-ada-002
   - `FastEmbedProvider`: Fast local embeddings

5. **SQL Data Providers**
   - `SQLiteDataProvider`: SQLite database operations
   - Extensible for PostgreSQL, MySQL

**Location**: `sibyl/providers/`

**Configuration**: Providers are configured through workspace files and instantiated via factory functions.

**Example Configuration**:

```yaml
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
      distance_metric: cosine
```

### Technique Layer

Techniques implement AI processing algorithms and workflows. They are organized into shops (technique collections) and can have multiple subtechniques for different implementation strategies.

**Shop Organization**:

1. **RAG Shop** (`sibyl/techniques/rag_pipeline/`)
   - Chunking, embedding, retrieval, reranking, synthesis techniques
   - Query processing (expansion, rewriting, HyDE, decomposition)
   - Augmentation (metadata injection, citations, cross-references)

2. **AI Generation Shop** (`sibyl/techniques/ai_generation/`)
   - Generation strategies (CoT, ReAct, ToT, self-consistency)
   - Consensus mechanisms (quorum voting, weighted voting)
   - Quality validation with retry strategies

3. **Workflow Shop** (`sibyl/techniques/workflow_orchestration/`)
   - Session management and context preservation
   - Graph-based workflow execution
   - Parallel execution and routing

4. **Infrastructure Shop** (`sibyl/techniques/infrastructure/`)
   - Caching (embedding, retrieval, semantic, query)
   - Security (content filtering, PII redaction, prompt injection detection)
   - Evaluation metrics (faithfulness, relevance, groundedness)
   - Workflow optimization (adaptive retrieval, cost optimization)

**Location**: `sibyl/techniques/`

**Technique Structure**:

```
technique/
├── __init__.py
├── README.md                    # Technique documentation
├── base.py                      # Base technique class
├── config.py                    # Configuration schemas
└── subtechniques/
    ├── implementation_a/
    │   ├── __init__.py
    │   └── technique.py         # Specific implementation
    └── implementation_b/
        ├── __init__.py
        └── technique.py
```

Each technique can have multiple subtechniques, allowing for different implementation strategies.

**Example**:

```python
from sibyl.techniques.base import BaseTechnique

class ChunkingTechnique(BaseTechnique):
    """Technique for chunking documents."""

    async def execute(
        self,
        input_data: dict,
        config: ChunkConfig
    ) -> dict:
        """Execute chunking on documents."""
        documents = input_data["documents"]
        chunks = await self._chunk_documents(documents, config)
        return {"chunks": chunks}
```

### Runtime Layer

The runtime layer orchestrates pipeline execution, managing state, budgets, and observability.

**Key Components**:

1. **WorkspaceRuntime** (`sibyl/runtime/workspace_runtime.py`)
   - Loads workspace configuration
   - Initializes providers and shops
   - Executes pipelines
   - Manages workspace lifecycle

2. **ShopRuntime** (`sibyl/runtime/shop_runtime.py`)
   - Executes techniques within a shop context
   - Resolves technique references
   - Manages technique state

3. **BudgetTracker** (`sibyl/runtime/budget_tracker.py`)
   - Monitors resource usage (cost, tokens, requests)
   - Enforces budget limits
   - Provides usage reporting

4. **StateManager** (`sibyl/state/`)
   - Persists pipeline state to DuckDB
   - Enables checkpointing and resume
   - Tracks execution history

5. **Observability** (`sibyl/observability/`)
   - Structured logging
   - Prometheus metrics
   - OpenTelemetry tracing
   - Health checks

**Location**: `sibyl/runtime/`, `sibyl/state/`, `sibyl/observability/`

**Runtime Flow**:

```
Load Workspace → Initialize Providers → Load Shops → Execute Pipeline
     ↓                   ↓                   ↓              ↓
  Config YAML     Factory Functions    Technique Loading  Step Execution
                                                            ↓
                                           Budget Tracking, Logging, Metrics
```

### Application Layer

The application layer provides user-facing interfaces for interacting with Sibyl.

**Interfaces**:

1. **CLI** (`sibyl/cli.py`)
   - Command-line interface for all operations
   - Pipeline execution
   - Workspace management
   - Configuration validation

2. **REST API** (`sibyl/server/rest_api.py`)
   - HTTP API for remote pipeline execution
   - OpenAI-compatible endpoints
   - Health checks and metrics

3. **MCP Server** (`sibyl/server/mcp_server.py`)
   - Model Context Protocol server implementation
   - stdio and HTTP transports
   - Tool exposure through workspace configuration
   - Integration with Claude Desktop and other MCP clients

**Location**: `sibyl/cli.py`, `sibyl/server/`

**Example CLI Usage**:

```bash
# Execute a pipeline
sibyl pipeline run \
  --workspace config/workspaces/local_docs_duckdb.yaml \
  --pipeline qa_over_docs \
  --param query="What is Sibyl?"

# Start MCP server
sibyl-mcp --workspace config/workspaces/local_docs_duckdb.yaml
```

## Data Flow

A typical RAG pipeline follows this data flow through the layers:

```
┌─────────────────────────────────────────────────────┐
│  User Request (CLI/API/MCP)                         │
└────────────────┬────────────────────────────────────┘
                 ↓
┌────────────────────────────────────────────────────┐
│  Application Layer: Parse request, load workspace  │
└────────────────┬───────────────────────────────────┘
                 ↓
┌────────────────────────────────────────────────────┐
│  Runtime Layer: Initialize pipeline, start budget  │
└────────────────┬───────────────────────────────────┘
                 ↓
┌────────────────────────────────────────────────────┐
│  Technique Layer: Execute pipeline steps           │
│   1. Load documents (RAG shop)                     │
│   2. Chunk documents (RAG shop)                    │
│   3. Generate embeddings (RAG shop)                │
│   4. Store vectors (Infrastructure)                │
│   5. Retrieve relevant chunks (RAG shop)           │
│   6. Rerank results (RAG shop)                     │
│   7. Generate answer (AI Generation shop)          │
└────────────────┬───────────────────────────────────┘
                 ↓
┌────────────────────────────────────────────────────┐
│  Provider Layer: Interact with external services   │
│   - Document provider reads files                  │
│   - Embedding provider generates vectors           │
│   - Vector store provider searches/stores          │
│   - LLM provider generates answers                 │
└────────────────┬───────────────────────────────────┘
                 ↓
┌────────────────────────────────────────────────────┐
│  Protocol Layer: Type-safe interfaces              │
└────────────────┬───────────────────────────────────┘
                 ↓
┌────────────────────────────────────────────────────┐
│  External Services: OpenAI, DuckDB, Filesystem     │
└────────────────────────────────────────────────────┘
```

## Extension Points

Sibyl is designed for extensibility at multiple levels:

### 1. Custom Providers

Implement protocol interfaces for new data sources or services:

```python
from sibyl.core.protocols import LLMProvider

class MyCustomLLMProvider:
    """Custom LLM provider implementation."""

    def complete(self, prompt: str, **kwargs) -> str:
        # Your custom LLM logic
        return self._call_my_llm_service(prompt)

    async def complete_async(self, prompt: str, **kwargs) -> str:
        # Async version
        return await self._call_my_llm_service_async(prompt)
```

See [Custom Providers](../extending/custom-providers.md).

### 2. Custom Techniques

Create new processing techniques and register them with shops:

```python
from sibyl.techniques.base import BaseTechnique

class MyCustomTechnique(BaseTechnique):
    """Custom technique implementation."""

    async def execute(self, input_data: dict, config: dict) -> dict:
        # Your custom processing logic
        result = await self.process(input_data)
        return {"output": result}
```

See [Custom Techniques](../techniques/custom-techniques.md).

### 3. Custom Subtechniques

Add alternative implementations for existing techniques:

```python
# Add to existing technique
my_technique.register_subtechnique(
    "my_custom_implementation",
    MyCustomSubtechnique()
)
```

### 4. Workspace Plugins

Extend workspace capabilities with custom logic:

```python
from sibyl.plugins.base import BasePlugin

class MyPlugin(BasePlugin):
    """Custom workspace plugin."""

    def on_workspace_load(self, workspace):
        # Custom initialization logic
        pass

    def on_pipeline_start(self, pipeline):
        # Custom pre-pipeline logic
        pass
```

See [Plugin Development](../plugins/creating-plugins.md).

## Design Patterns

### Factory Pattern

Providers are instantiated through factory functions:

```python
def create_llm_provider(config: dict) -> LLMProvider:
    """Factory for LLM providers."""
    kind = config["kind"]

    if kind == "openai":
        return OpenAIProvider(**config)
    elif kind == "anthropic":
        return AnthropicProvider(**config)
    # ... more providers
```

### Strategy Pattern

Techniques use subtechniques as interchangeable strategies:

```python
# Different chunking strategies
chunker = ChunkingTechnique()
result = await chunker.execute(
    input_data,
    subtechnique="semantic",  # or "fixed-size", "markdown"
    config=config
)
```

### Observer Pattern

Observability uses observers for metrics and logging:

```python
runtime.add_observer(MetricsObserver())
runtime.add_observer(LoggingObserver())
runtime.add_observer(TracingObserver())
```

### Chain of Responsibility

Pipelines chain technique executions:

```python
# Each step processes and passes to next
Step 1 Output → Step 2 Input → Step 2 Output → Step 3 Input → ...
```

## Performance Considerations

### Asynchronous Execution

Sibyl uses `async/await` throughout for efficient I/O:

```python
# Multiple I/O operations in parallel
results = await asyncio.gather(
    embed_batch_1,
    embed_batch_2,
    embed_batch_3
)
```

### Caching

Multiple cache levels reduce redundant computation:

- **Embedding cache**: Avoid re-embedding same text
- **Retrieval cache**: Cache retrieval results
- **Semantic cache**: Match similar queries
- **Query cache**: Exact query matching

### Batch Processing

Batch operations for efficiency:

```python
# Batch embedding generation
embeddings = await provider.embed_batch(texts)

# Batch vector storage
vector_store.upsert_batch(vectors)
```

### Lazy Loading

Techniques and providers loaded only when needed:

```python
# Providers instantiated on-demand
provider = await runtime.get_provider("my_llm")
```

## Security Considerations

### Input Validation

All inputs validated at protocol boundaries:

```python
# Pydantic models for validation
class ChunkConfig(BaseModel):
    chunk_size: int = Field(gt=0, le=10000)
    chunk_overlap: int = Field(ge=0)
```

### Prompt Injection Detection

Built-in prompt injection detection technique:

```python
# Detect malicious prompts
result = await security.detect_prompt_injection(user_input)
if result.is_malicious:
    raise SecurityError("Prompt injection detected")
```

### PII Redaction

Automatic PII detection and redaction:

```python
# Redact sensitive information
redacted_text = await security.redact_pii(text)
```

### Access Control

Role-based access control for pipelines and tools:

```yaml
access_control:
  roles:
    admin:
      pipelines: ["*"]
    user:
      pipelines: ["qa_over_docs", "search_documents"]
```

## Scalability

### Horizontal Scaling

Multiple server instances behind load balancer:

```
Load Balancer
    ↓
[Server 1] [Server 2] [Server 3]
    ↓           ↓           ↓
Shared Vector Store (pgvector/Qdrant)
    ↓           ↓           ↓
Shared State Store (PostgreSQL)
```

### Vertical Scaling

Optimize resource usage per instance:

- Batch size tuning
- Connection pooling
- Cache sizing
- Worker thread configuration

### Distributed Deployment

Separate components for scale:

```
API Servers ←→ Vector Database Cluster
     ↓
Message Queue
     ↓
Worker Pool ←→ LLM Provider (multiple instances)
```

See [Distributed Deployment](../advanced/distributed-deployment.md).

## Further Reading

- **[Core Concepts](core-concepts.md)** - Detailed concept explanations
- **[Data Flow](data-flow.md)** - How data moves through Sibyl
- **[Design Patterns](design-patterns.md)** - Patterns used in Sibyl
- **[API Reference](../api/overview.md)** - Detailed API documentation

---

**Next**: [Core Concepts](core-concepts.md) | [Data Flow](data-flow.md)

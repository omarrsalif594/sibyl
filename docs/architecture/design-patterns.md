# Design Patterns

Sibyl employs proven design patterns to achieve modularity, extensibility, and maintainability.

## Overview

Key patterns used throughout Sibyl:

1. **Protocol-Oriented Design** - Interfaces over implementations
2. **Factory Pattern** - Object creation abstraction
3. **Strategy Pattern** - Interchangeable algorithms
4. **Observer Pattern** - Event notification
5. **Chain of Responsibility** - Sequential processing
6. **Dependency Injection** - Loose coupling
7. **Repository Pattern** - Data access abstraction
8. **Facade Pattern** - Simplified interfaces

## Protocol-Oriented Design

### Pattern

Define behavior through protocols (interfaces) rather than concrete classes.

### Implementation

```python
from typing import Protocol

class LLMProvider(Protocol):
    """Protocol defining LLM provider interface."""

    def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion from prompt."""
        ...

    async def complete_async(self, prompt: str, **kwargs) -> str:
        """Async completion generation."""
        ...
```

### Usage

```python
def generate_answer(provider: LLMProvider, prompt: str) -> str:
    """Works with any LLM provider implementing the protocol."""
    return provider.complete(prompt)

# Works with OpenAI
answer = generate_answer(OpenAIProvider(), prompt)

# Works with Anthropic
answer = generate_answer(AnthropicProvider(), prompt)

# Works with custom provider
answer = generate_answer(MyCustomProvider(), prompt)
```

### Benefits

- **Type Safety**: Catch errors at development time
- **Interchangeability**: Swap implementations easily
- **Testability**: Mock providers for testing
- **Extensibility**: Add new providers without modifying existing code

## Factory Pattern

### Pattern

Centralize object creation to abstract instantiation logic.

### Implementation

```python
def create_llm_provider(config: dict) -> LLMProvider:
    """Factory for creating LLM providers."""
    kind = config["kind"]

    if kind == "openai":
        return OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=config.get("model", "gpt-4"),
            temperature=config.get("temperature", 0.7)
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
        raise ValueError(f"Unknown provider kind: {kind}")
```

### Usage

```yaml
# Configuration
providers:
  llm:
    primary:
      kind: openai
      model: gpt-4
```

```python
# Runtime
config = workspace.providers.llm.primary
provider = create_llm_provider(config)
```

### Benefits

- **Centralized Creation**: One place to manage instantiation
- **Configuration-Driven**: Create objects from YAML/JSON
- **Validation**: Validate configuration before creation
- **Environment Variables**: Resolve secrets at creation time

## Strategy Pattern

### Pattern

Define a family of algorithms, encapsulate each one, and make them interchangeable.

### Implementation

```python
class ChunkingTechnique:
    """Technique with multiple chunking strategies."""

    def __init__(self):
        self.strategies = {
            "fixed-size": FixedSizeChunker(),
            "semantic": SemanticChunker(),
            "markdown": MarkdownChunker(),
            "sql": SQLChunker()
        }

    async def execute(
        self,
        documents: list[Document],
        strategy: str = "fixed-size",
        config: dict = None
    ) -> list[Chunk]:
        """Execute using specified strategy."""
        chunker = self.strategies[strategy]
        return await chunker.chunk(documents, config)
```

### Usage

```python
# Use different strategies
chunks = await technique.execute(docs, strategy="semantic")
chunks = await technique.execute(docs, strategy="fixed-size")
chunks = await technique.execute(docs, strategy="markdown")
```

### Benefits

- **Flexibility**: Choose algorithm at runtime
- **Extensibility**: Add new strategies without modifying technique
- **Testability**: Test each strategy independently
- **Configuration**: Strategy selection via YAML

## Observer Pattern

### Pattern

Define a one-to-many dependency where observers are notified of state changes.

### Implementation

```python
class Observable:
    """Base class for observable objects."""

    def __init__(self):
        self._observers: list[Observer] = []

    def add_observer(self, observer: Observer) -> None:
        """Add an observer."""
        self._observers.append(observer)

    def notify_observers(self, event: Event) -> None:
        """Notify all observers of an event."""
        for observer in self._observers:
            observer.update(event)

class PipelineRuntime(Observable):
    """Pipeline runtime with observer support."""

    async def execute_step(self, step: Step) -> Result:
        """Execute step and notify observers."""
        # Notify step start
        self.notify_observers(StepStartEvent(step))

        # Execute step
        result = await step.execute()

        # Notify step complete
        self.notify_observers(StepCompleteEvent(step, result))

        return result
```

### Usage

```python
# Add observers
runtime.add_observer(MetricsObserver())
runtime.add_observer(LoggingObserver())
runtime.add_observer(TracingObserver())

# Execute pipeline - observers are notified automatically
await runtime.run_pipeline("my_pipeline")
```

### Benefits

- **Decoupling**: Observers don't depend on observable
- **Extensibility**: Add new observers without modifying runtime
- **Observability**: Easy to add metrics, logging, tracing
- **Testing**: Mock observers for testing

## Chain of Responsibility

### Pattern

Pass requests along a chain of handlers until one handles it.

### Implementation

```python
class Pipeline:
    """Pipeline as chain of technique executions."""

    def __init__(self, steps: list[Step]):
        self.steps = steps

    async def execute(self, initial_input: dict) -> dict:
        """Execute steps in sequence, passing output to next."""
        data = initial_input

        for step in self.steps:
            # Each step receives previous step's output
            data = await step.execute(data)

            # Can short-circuit if needed
            if data.get("early_stop"):
                break

        return data
```

### Usage

```yaml
pipelines:
  rag_pipeline:
    steps:
      - use: rag.chunking        # Input: documents
      - use: rag.embedding       # Input: chunks from previous
      - use: rag.retrieval       # Input: embeddings from previous
      - use: ai_generation.gen   # Input: retrieved docs from previous
```

### Benefits

- **Sequential Processing**: Clear data flow
- **Composability**: Build complex pipelines from simple steps
- **Flexibility**: Add, remove, reorder steps easily
- **Short-Circuiting**: Stop early if needed

## Dependency Injection

### Pattern

Inject dependencies rather than creating them internally.

### Implementation

```python
class RetrievalTechnique:
    """Technique with injected dependencies."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStoreProvider
    ):
        # Dependencies injected, not created internally
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    async def execute(self, query: str, top_k: int) -> list[Document]:
        """Retrieve documents using injected dependencies."""
        # Use injected embedding provider
        query_embedding = await self.embedding_provider.embed(query)

        # Use injected vector store
        results = await self.vector_store.search(
            query_embedding,
            limit=top_k
        )

        return results
```

### Usage

```python
# Inject dependencies
technique = RetrievalTechnique(
    embedding_provider=sentence_transformer,
    vector_store=duckdb_store
)

# Easy to swap implementations
technique = RetrievalTechnique(
    embedding_provider=openai_embeddings,
    vector_store=pgvector_store
)

# Easy to test with mocks
technique = RetrievalTechnique(
    embedding_provider=mock_embeddings,
    vector_store=mock_vector_store
)
```

### Benefits

- **Loose Coupling**: Technique doesn't depend on specific implementations
- **Testability**: Easy to inject mocks
- **Configuration**: Inject different implementations per environment
- **Flexibility**: Change dependencies without modifying technique

## Repository Pattern

### Pattern

Abstract data access behind a repository interface.

### Implementation

```python
class VectorStoreRepository(Protocol):
    """Repository for vector storage operations."""

    async def save(self, vectors: list[Vector]) -> None:
        """Save vectors to store."""
        ...

    async def search(
        self,
        query_vector: Vector,
        limit: int,
        filters: dict = None
    ) -> list[SearchResult]:
        """Search for similar vectors."""
        ...

    async def delete(self, ids: list[str]) -> None:
        """Delete vectors by ID."""
        ...

class DuckDBVectorRepository:
    """DuckDB implementation of vector repository."""

    def __init__(self, connection: duckdb.Connection):
        self.conn = connection

    async def save(self, vectors: list[Vector]) -> None:
        """Save to DuckDB."""
        # Implementation specific to DuckDB
        ...

    async def search(self, query_vector: Vector, limit: int, filters: dict = None):
        """Search in DuckDB."""
        # Implementation specific to DuckDB
        ...
```

### Benefits

- **Data Access Abstraction**: Hide storage details
- **Swappable Backends**: Easy to change database
- **Testability**: Mock repository for testing
- **Query Optimization**: Optimize queries per backend

## Facade Pattern

### Pattern

Provide a simplified interface to a complex subsystem.

### Implementation

```python
class WorkspaceRuntime:
    """Facade for Sibyl's complex subsystems."""

    def __init__(self, workspace: Workspace):
        # Complex subsystems
        self._provider_factory = ProviderFactory()
        self._shop_loader = ShopLoader()
        self._pipeline_executor = PipelineExecutor()
        self._budget_tracker = BudgetTracker()
        self._state_manager = StateManager()
        self._observability = ObservabilityStack()

    async def run_pipeline(
        self,
        pipeline_name: str,
        **params
    ) -> Result:
        """Simple interface to run a pipeline."""
        # Internally coordinates complex subsystems
        pipeline = self._load_pipeline(pipeline_name)
        self._budget_tracker.start(pipeline)
        self._observability.track(pipeline)

        result = await self._pipeline_executor.execute(
            pipeline,
            params
        )

        self._state_manager.save(result)
        return result
```

### Usage

```python
# Simple API hides complexity
runtime = WorkspaceRuntime(workspace)
result = await runtime.run_pipeline("qa_over_docs", query="What is ML?")
```

### Benefits

- **Simplicity**: Easy-to-use API for complex operations
- **Encapsulation**: Hide internal complexity
- **Flexibility**: Can change internals without affecting API
- **Usability**: Reduces learning curve

## Composite Pattern

### Pattern

Compose objects into tree structures to represent part-whole hierarchies.

### Implementation

```python
class CompositeStep:
    """Step that contains other steps."""

    def __init__(self, steps: list[Step]):
        self.steps = steps

    async def execute(self, input_data: dict) -> dict:
        """Execute all child steps."""
        results = []
        for step in self.steps:
            result = await step.execute(input_data)
            results.append(result)
        return {"results": results}

class ParallelStep(CompositeStep):
    """Execute steps in parallel."""

    async def execute(self, input_data: dict) -> dict:
        """Execute all steps concurrently."""
        tasks = [
            step.execute(input_data)
            for step in self.steps
        ]
        results = await asyncio.gather(*tasks)
        return {"results": results}
```

### Usage

```python
# Create composite pipeline
pipeline = Pipeline([
    LoadDocumentsStep(),
    ChunkingStep(),
    ParallelStep([  # Parallel composite
        EmbeddingStep(model="openai"),
        EmbeddingStep(model="sentence-transformer")
    ]),
    StorageStep()
])
```

### Benefits

- **Hierarchical Structure**: Organize steps in trees
- **Uniform Treatment**: Treat single and composite steps the same
- **Flexibility**: Nest steps arbitrarily
- **Parallelism**: Easy to implement parallel execution

## Builder Pattern

### Pattern

Separate construction of complex objects from their representation.

### Implementation

```python
class PipelineBuilder:
    """Builder for constructing pipelines."""

    def __init__(self):
        self._steps = []
        self._config = {}

    def add_step(self, technique: str, config: dict = None) -> 'PipelineBuilder':
        """Add a step to the pipeline."""
        self._steps.append(Step(technique, config))
        return self

    def set_budget(self, max_cost: float) -> 'PipelineBuilder':
        """Set budget limit."""
        self._config["budget"] = {"max_cost_usd": max_cost}
        return self

    def set_timeout(self, seconds: int) -> 'PipelineBuilder':
        """Set timeout."""
        self._config["timeout_s"] = seconds
        return self

    def build(self) -> Pipeline:
        """Build the pipeline."""
        return Pipeline(
            steps=self._steps,
            config=self._config
        )
```

### Usage

```python
# Fluent API for building pipelines
pipeline = (PipelineBuilder()
    .add_step("rag.chunking", {"chunk_size": 512})
    .add_step("rag.embedding")
    .add_step("rag.retrieval", {"top_k": 5})
    .set_budget(1.0)
    .set_timeout(300)
    .build())
```

### Benefits

- **Fluent Interface**: Readable, chainable API
- **Step-by-Step Construction**: Build complex objects incrementally
- **Validation**: Validate at each step
- **Flexibility**: Different representations from same builder

## Singleton Pattern (Used Sparingly)

### Pattern

Ensure a class has only one instance with global access.

### Implementation

```python
class ObservabilityStack:
    """Singleton observability stack."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize once."""
        self.metrics = PrometheusMetrics()
        self.logger = StructuredLogger()
        self.tracer = OpenTelemetryTracer()
```

### Usage

```python
# Always returns same instance
obs1 = ObservabilityStack()
obs2 = ObservabilityStack()
assert obs1 is obs2  # True
```

### Benefits

- **Global Access**: Single point of access
- **Resource Sharing**: Share expensive resources
- **Consistency**: Ensure consistent state

### Cautions

- **Testing**: Can make testing harder
- **Global State**: Can introduce hidden dependencies
- **Thread Safety**: Requires careful implementation

## Anti-Patterns Avoided

### 1. God Object

**Anti-Pattern**: One object that knows/does too much

**Sibyl's Approach**: Layered architecture with single-responsibility classes

### 2. Tight Coupling

**Anti-Pattern**: Classes directly depend on concrete implementations

**Sibyl's Approach**: Protocol-oriented design and dependency injection

### 3. Copy-Paste Programming

**Anti-Pattern**: Duplicating code instead of abstracting

**Sibyl's Approach**: Reusable techniques and subtechniques

### 4. Magic Numbers

**Anti-Pattern**: Hard-coded constants in code

**Sibyl's Approach**: Configuration-driven with YAML

### 5. Premature Optimization

**Anti-Pattern**: Optimizing before measuring

**Sibyl's Approach**: Observability first, then optimize based on data

## Summary

Design patterns in Sibyl provide:

1. **Modularity**: Components are independent and reusable
2. **Extensibility**: Easy to add new functionality
3. **Maintainability**: Changes localized to specific components
4. **Testability**: Easy to mock and test components
5. **Clarity**: Proven patterns aid understanding

Understanding these patterns helps you:
- Extend Sibyl effectively
- Write clean, maintainable code
- Make architectural decisions
- Contribute to the project

## Further Reading

- **[Architecture Overview](overview.md)** - System architecture
- **[Core Concepts](core-concepts.md)** - Fundamental concepts
- **[Developer Guide](../extending/developer-guide.md)** - Extend Sibyl

---

**Previous**: [Data Flow](data-flow.md) | **Next**: [Workspaces](../workspaces/overview.md)

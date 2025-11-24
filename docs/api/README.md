# API Reference

Complete API documentation for Sibyl core components and techniques.

---

## Core APIs

- **[Core](./core.md)** - Application context, configuration, and base classes
- **[Contracts](./contracts.md)** - Data models and contracts
- **[Result Pattern](./result.md)** - Error handling with Result type
- **[Protocols](./protocols.md)** - Interface definitions

---

## Technique APIs

- **[RAG Pipeline](./rag-pipeline.md)** - Chunking, embedding, retrieval, reranking
- **[AI Generation](./ai-generation.md)** - Generation, consensus, voting
- **[Data Integration](./data-integration.md)** - Document loading, SQL queries, vector storage
- **[Workflow Orchestration](./workflow.md)** - Orchestration, routing, session management
- **[Infrastructure](./infrastructure.md)** - Caching, evaluation, security

---

## Quick Reference

### ApplicationContext

```python
from sibyl.core.application.context import ApplicationContext

# Create from workspace
ctx = ApplicationContext.from_workspace("path/to/workspace")

# Get configuration
config = ctx.get_technique_config(
    shop="rag_pipeline",
    technique="retrieval",
    subtechnique="semantic_search"
)

# Access providers
anthropic_client = ctx.get_provider("anthropic")
```

### Result Pattern

```python
from sibyl.core.domain.contracts import Result

# Success
result = Result.success(value="result data")

# Failure
result = Result.failure(
    error_type="validation_error",
    message="Invalid input",
    details={"field": "chunk_size"}
)

# Check result
if result.is_success:
    data = result.value
else:
    print(f"Error: {result.error}")
```

### Technique Execution

```python
from sibyl.techniques.rag_pipeline import retrieval

# Execute technique
result = await retrieval.execute(
    ctx=ctx,
    technique="semantic_search",
    params={
        "query": "search query",
        "top_k": 5
    }
)

if result.is_success:
    chunks = result.value
```

---

## Documentation Conventions

- **Required parameters** are marked with `*`
- **Optional parameters** show default values
- **Type hints** indicate expected types
- **Async functions** use `async def`
- **Return types** use `Result[T]` for fallible operations

---

## See Also

- [Examples](../examples/)
- [Techniques Catalog](../techniques/catalog.md)
- [Custom Techniques](../techniques/custom-techniques.md)

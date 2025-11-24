# Advanced Topics

Advanced patterns, optimizations, and architectural guidance for production Sibyl applications.

---

## Contents

1. **[Agent Patterns](./agent-patterns.md)** - Advanced agent architectures
2. **[Performance Optimization](./performance.md)** - Scaling and optimization
3. **[Production Architecture](./production-architecture.md)** - Enterprise deployments
4. **[Security Deep Dive](./security.md)** - Advanced security patterns

---

## Agent Patterns

### Self-Healing Agents

Agents that recover from errors automatically:

```python
class SelfHealingAgent:
    async def execute_with_recovery(self, task: str):
        for attempt in range(3):
            try:
                return await self.execute(task)
            except Exception as e:
                if attempt < 2:
                    # Analyze error and adjust strategy
                    await self.adjust_strategy(e)
                else:
                    raise
```

### Multi-Agent Coordination

Coordinate multiple specialized agents:

```python
class AgentOrchestrator:
    def __init__(self):
        self.rag_agent = RAGAgent()
        self.sql_agent = SQLAgent()
        self.web_agent = WebSearchAgent()

    async def coordinate(self, task: str):
        # Route to appropriate agents
        if self.needs_database(task):
            sql_result = await self.sql_agent.query(task)

        if self.needs_documents(task):
            rag_result = await self.rag_agent.search(task)

        # Synthesize results
        return await self.synthesize([sql_result, rag_result])
```

---

## Performance Optimization

### Batch Processing

Process multiple items efficiently:

```python
async def batch_embed(chunks: List[str], batch_size: int = 32):
    """Batch embedding for better throughput."""
    results = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        embeddings = await embed_batch(batch)
        results.extend(embeddings)
    return results
```

### Caching Strategies

Multi-level caching for optimal performance:

```python
# workspace_config.yaml
shops:
  infrastructure:
    caching:
      # L1: In-memory cache
      memory_cache:
        technique: memory_cache
        config:
          max_size: 1000
          ttl: 300

      # L2: Redis cache
      redis_cache:
        technique: redis_cache
        config:
          ttl: 3600

      # L3: Semantic cache
      semantic_cache:
        technique: semantic_cache
        config:
          similarity_threshold: 0.95
```

### Parallel Execution

Execute independent operations concurrently:

```python
async def parallel_retrieval(queries: List[str]):
    """Retrieve multiple queries in parallel."""
    tasks = [retrieval.execute(ctx, params={"query": q}) for q in queries]
    results = await asyncio.gather(*tasks)
    return results
```

---

## Production Architecture

### Microservices Architecture

```
┌─────────────┐
│   API GW    │
└──────┬──────┘
       │
   ┌───┴────────────────┬──────────────┐
   │                    │              │
┌──▼───────┐    ┌──────▼─────┐  ┌─────▼─────┐
│   RAG    │    │    SQL     │  │    MCP    │
│ Service  │    │  Service   │  │  Service  │
└──────────┘    └────────────┘  └───────────┘
       │              │               │
       └──────┬───────┴───────────────┘
              │
       ┌──────▼────────┐
       │  Vector DB    │
       │  (Qdrant)     │
       └───────────────┘
```

### Horizontal Scaling

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sibyl-rag-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sibyl-rag
  template:
    spec:
      containers:
      - name: sibyl
        image: sibyl:latest
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
```

---

## Security

### API Key Rotation

```python
class RotatingAPIKeyProvider:
    """Provider with automatic key rotation."""

    def __init__(self):
        self.keys = self.load_keys()
        self.current_index = 0

    async def get_key(self) -> str:
        # Rotate keys periodically
        if self.should_rotate():
            await self.rotate_key()
        return self.keys[self.current_index]

    async def rotate_key(self):
        self.current_index = (self.current_index + 1) % len(self.keys)
```

### Input Sanitization

```python
def sanitize_query(query: str) -> str:
    """Sanitize user input."""
    # Remove SQL injection attempts
    query = re.sub(r"(DROP|DELETE|UPDATE|INSERT)\s", "", query, flags=re.IGNORECASE)

    # Remove prompt injection attempts
    query = re.sub(r"(ignore previous|system:|assistant:)", "", query, flags=re.IGNORECASE)

    # Limit length
    return query[:1000]
```

---

## Learn More

- [Performance Tuning](../operations/performance-tuning.md)
- [Security Best Practices](../operations/security.md)
- [Deployment Guide](../operations/deployment.md)
- [Agent Workflow Example](../examples/agent-workflow.md)

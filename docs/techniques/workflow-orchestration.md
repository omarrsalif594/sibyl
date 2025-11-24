# Workflow Orchestration Techniques

Complete guide to orchestrating complex multi-step AI workflows in Sibyl.

## Overview

The Workflow Orchestration shop provides techniques for managing complex, stateful AI workflows. It includes:

1. **Session Management** - Manage conversation state and memory
2. **Context Management** - Handle context windows efficiently
3. **Graph Orchestration** - Execute graph-based workflows
4. **Orchestration** - Coordinate multi-step processes

## Session Management

Manage stateful conversations and user sessions.

### Memory-Based Sessions

Store conversation history with full memory.

```yaml
pipelines:
  conversational_qa:
    shop: workflow_orchestration
    steps:
      - use: workflow_orchestration.session_management
        config:
          subtechnique: memory
          timeout: 3600                # 1 hour timeout
          max_messages: 100            # Max messages to store
          storage: redis               # redis, memory, database
          session_id: "${user_id}"
```

**How it works**:
1. Load previous messages for session
2. Add new message to history
3. Include relevant history in context
4. Store updated history

**Example**:
```python
# First message
result = await pipeline.execute({
    "session_id": "user_123",
    "message": "What is Python?"
})
# Response: "Python is a programming language..."

# Follow-up message
result = await pipeline.execute({
    "session_id": "user_123",
    "message": "What's it used for?"
})
# Response: "Python is used for..." (knows "it" refers to Python)
```

**Configuration**:
```yaml
config:
  subtechnique: memory

  # Storage backend
  storage: redis
  redis_url: "${REDIS_URL}"
  key_prefix: "session:"

  # Session limits
  timeout: 3600                        # Session expires after 1 hour
  max_messages: 100                    # Store up to 100 messages
  max_tokens: 8000                     # Or 8K tokens of history

  # Memory management
  compression: true                    # Compress old messages
  summarization: true                  # Summarize old conversations
```

### Stateless Sessions

No persistent state between requests.

```yaml
steps:
  - use: workflow_orchestration.session_management
    config:
      subtechnique: stateless
```

**Best for**: Simple Q&A, no conversation context needed

### Persistent Sessions

Store sessions in database for long-term persistence.

```yaml
steps:
  - use: workflow_orchestration.session_management
    config:
      subtechnique: persistent
      storage: database
      database_url: "${DATABASE_URL}"
      table: conversations
```

**Schema**:
```sql
CREATE TABLE conversations (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    messages JSONB,
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    expires_at TIMESTAMP
);
```

### Sliding Window Sessions

Keep only recent messages in memory.

```yaml
steps:
  - use: workflow_orchestration.session_management
    config:
      subtechnique: sliding_window
      window_size: 10                  # Keep last 10 messages
      include_summary: true            # Summarize older messages
```

**Example**:
```
Message 1-5: [Summarized] "User asked about Python basics"
Message 6-15: [Full conversation history]
Message 16: Current message
```

## Context Management

Efficiently manage LLM context windows.

### Window-Based Context

Keep fixed-size context window.

```yaml
steps:
  - use: workflow_orchestration.context_management
    config:
      subtechnique: window
      max_tokens: 8000                 # GPT-4 context limit
      window_size: 10                  # Last 10 messages
      reserve_tokens: 2000             # Reserve for response
```

**How it works**:
1. Calculate token count of messages
2. Keep most recent messages that fit
3. Drop older messages
4. Reserve space for response

**Token allocation**:
```
Total: 8000 tokens
- System prompt: 200 tokens
- User messages: 5800 tokens (fits ~10 messages)
- Reserved for response: 2000 tokens
```

### Compression-Based Context

Compress older parts of conversation.

```yaml
steps:
  - use: workflow_orchestration.context_management
    config:
      subtechnique: compression
      max_tokens: 8000
      compression_ratio: 0.5           # Compress to 50%
      compression_method: extractive   # extractive, abstractive
```

**Compression methods**:

**Extractive** - Select important sentences:
```python
Original (500 tokens):
"The user asked about Python. Python is a programming language.
It was created by Guido van Rossum. Python is known for
simplicity. It has many use cases..."

Compressed (250 tokens):
"User asked about Python. Python is a programming language
created by Guido van Rossum, known for simplicity."
```

**Abstractive** - Generate summary:
```python
Original (500 tokens):
[Long conversation about Python]

Compressed (100 tokens):
"Discussion covered Python basics, its creator, and main use cases."
```

### Summary-Based Context

Summarize conversation periodically.

```yaml
steps:
  - use: workflow_orchestration.context_management
    config:
      subtechnique: summary
      max_tokens: 8000
      summary_frequency: 10            # Summarize every 10 messages
      summary_length: 200              # Summary max length
```

**Example**:
```
Messages 1-10: [Summary] "User learned about Python basics"
Messages 11-20: [Summary] "User asked about web frameworks"
Messages 21-25: [Full recent context]
Message 26: Current message
```

### Hierarchical Context

Maintain context at multiple granularities.

```yaml
steps:
  - use: workflow_orchestration.context_management
    config:
      subtechnique: hierarchical
      levels:
        - name: full
          messages: 5                  # Last 5 messages in full
        - name: compressed
          messages: 10                 # Next 10 compressed
        - name: summary
          messages: 100                # Older messages summarized
```

**Context structure**:
```
Level 1 (Full): Messages 16-20 (current context)
Level 2 (Compressed): Messages 6-15 (compressed)
Level 3 (Summary): Messages 1-5 (summarized)
```

## Graph Orchestration

Execute workflows as directed graphs.

### DAG (Directed Acyclic Graph)

Standard graph workflow without cycles.

```yaml
pipelines:
  research_workflow:
    shop: workflow_orchestration
    steps:
      - use: workflow_orchestration.graph
        config:
          subtechnique: dag
          max_iterations: 10
          graph_definition:
            nodes:
              - id: expand_query
                technique: rag.query_processing
                config:
                  subtechnique: expansion
                  num_queries: 3

              - id: search_docs
                technique: rag.search
                config:
                  subtechnique: hybrid
                  top_k: 10

              - id: search_web
                technique: external.web_search
                config:
                  max_results: 5

              - id: combine_results
                technique: rag.ranking
                config:
                  subtechnique: reciprocal_rank_fusion

              - id: generate_answer
                technique: ai_generation.generation
                config:
                  provider: primary

              - id: validate
                technique: ai_generation.validation
                config:
                  subtechnique: fact_check

            edges:
              - from: expand_query
                to: search_docs

              - from: expand_query
                to: search_web

              - from: search_docs
                to: combine_results

              - from: search_web
                to: combine_results

              - from: combine_results
                to: generate_answer

              - from: generate_answer
                to: validate
```

**Execution**:
```
expand_query
    ├─> search_docs ─┐
    └─> search_web ──┤
                     ├─> combine_results
                     └─> generate_answer
                         └─> validate
```

**Features**:
- Parallel execution where possible
- Dependency resolution
- Error handling per node
- Result passing between nodes

### Cyclic Graphs

Graphs with feedback loops.

```yaml
steps:
  - use: workflow_orchestration.graph
    config:
      subtechnique: cyclic
      max_iterations: 5                # Prevent infinite loops
      graph_definition:
        nodes:
          - id: generate
            technique: ai_generation.generation

          - id: evaluate
            technique: ai_generation.validation

          - id: refine
            technique: ai_generation.generation
            config:
              prompt: "Improve this answer: ${previous_answer}"

        edges:
          - from: generate
            to: evaluate

          - from: evaluate
            to: refine
            condition: ${evaluation.score} < 0.8  # Only if score low

          - from: refine
            to: evaluate                # Loop back
```

**Example execution**:
```
Iteration 1: generate -> evaluate (score: 0.6) -> refine
Iteration 2: evaluate (score: 0.75) -> refine
Iteration 3: evaluate (score: 0.85) -> done
```

### Conditional Graphs

Branch based on conditions.

```yaml
steps:
  - use: workflow_orchestration.graph
    config:
      subtechnique: conditional
      graph_definition:
        nodes:
          - id: classify
            technique: ai_generation.generation
            config:
              prompt: "Classify query type: factual, opinion, or creative"

          - id: factual_pipeline
            technique: rag.retrieval

          - id: opinion_pipeline
            technique: ai_generation.consensus

          - id: creative_pipeline
            technique: ai_generation.generation
            config:
              temperature: 1.2

        edges:
          - from: classify
            to: factual_pipeline
            condition: ${classify.type} == "factual"

          - from: classify
            to: opinion_pipeline
            condition: ${classify.type} == "opinion"

          - from: classify
            to: creative_pipeline
            condition: ${classify.type} == "creative"
```

### Dynamic Graphs

Build graph structure dynamically at runtime.

```yaml
steps:
  - use: workflow_orchestration.graph
    config:
      subtechnique: dynamic
      graph_builder: python            # python, javascript
      builder_code: |
        def build_graph(input_data):
            graph = Graph()

            # Add nodes based on input
            if input_data["include_search"]:
                graph.add_node("search", "rag.search")

            if input_data["include_validation"]:
                graph.add_node("validate", "ai_generation.validation")

            # Add edges
            graph.add_edge("start", "search")
            if "validate" in graph.nodes:
                graph.add_edge("search", "validate")

            return graph
```

## Multi-Step Orchestration

Coordinate complex multi-step processes.

### Sequential Orchestration

Execute steps in order.

```yaml
steps:
  - use: workflow_orchestration.orchestration
    config:
      subtechnique: sequential
      steps:
        - name: load_data
          technique: data.load_documents
          config:
            source: filesystem_markdown

        - name: chunk
          technique: rag.chunking
          depends_on: [load_data]

        - name: embed
          technique: rag.embedding
          depends_on: [chunk]

        - name: store
          technique: data.store_vectors
          depends_on: [embed]
```

### Parallel Orchestration

Execute steps in parallel.

```yaml
steps:
  - use: workflow_orchestration.orchestration
    config:
      subtechnique: parallel
      max_concurrent: 5
      steps:
        - name: search_docs
          technique: rag.search
          config:
            collection: documents

        - name: search_code
          technique: rag.search
          config:
            collection: code

        - name: search_web
          technique: external.web_search

        # All three run in parallel

      # Combine results
      combine_step:
        name: combine
        technique: rag.ranking
        depends_on: [search_docs, search_code, search_web]
```

### Conditional Orchestration

Execute steps based on conditions.

```yaml
steps:
  - use: workflow_orchestration.orchestration
    config:
      subtechnique: conditional
      steps:
        - name: retrieve
          technique: rag.retrieval
          always: true                 # Always run

        - name: rerank
          technique: rag.reranking
          condition: ${retrieve.count} > 5  # Only if >5 results

        - name: expand_query
          technique: rag.query_processing
          condition: ${retrieve.count} < 3  # Only if <3 results
          on_condition_true:
            - name: retry_retrieval
              technique: rag.retrieval
```

### Error Handling Orchestration

Handle errors gracefully.

```yaml
steps:
  - use: workflow_orchestration.orchestration
    config:
      subtechnique: error_handling
      steps:
        - name: primary_search
          technique: rag.search
          config:
            collection: primary
          on_error:
            - name: fallback_search
              technique: rag.search
              config:
                collection: backup

        - name: generate
          technique: ai_generation.generation
          retry:
            max_attempts: 3
            backoff: exponential
          on_error:
            - name: simple_generate
              technique: ai_generation.generation
              config:
                provider: fallback
                temperature: 0.3       # More deterministic
```

## Complete Workflow Examples

### Multi-Turn Conversational Agent

```yaml
pipelines:
  conversational_agent:
    shop: workflow_orchestration
    steps:
      # Manage session
      - use: workflow_orchestration.session_management
        config:
          subtechnique: memory
          timeout: 3600
          max_messages: 50

      # Manage context
      - use: workflow_orchestration.context_management
        config:
          subtechnique: hierarchical
          max_tokens: 8000

      # Process query with context
      - use: rag.query_processing
        config:
          subtechnique: rewriting
          context: "${conversation_history}"

      # Retrieve
      - use: rag.retrieval
        config:
          top_k: 5

      # Generate response
      - use: ai_generation.generation
        config:
          provider: primary
          system_prompt: |
            You are a helpful assistant in an ongoing conversation.
            Previous context: ${conversation_summary}
```

### Research Workflow

```yaml
pipelines:
  research_workflow:
    shop: workflow_orchestration
    steps:
      - use: workflow_orchestration.graph
        config:
          subtechnique: dag
          graph_definition:
            nodes:
              # Phase 1: Query expansion
              - id: expand
                technique: rag.query_processing
                config:
                  subtechnique: decomposition

              # Phase 2: Parallel search
              - id: search_internal
                technique: rag.search
                config:
                  collection: internal_docs

              - id: search_external
                technique: external.web_search

              # Phase 3: Process results
              - id: combine
                technique: rag.ranking

              - id: analyze
                technique: ai_generation.generation
                config:
                  prompt: "Analyze these sources: ${sources}"

              # Phase 4: Synthesize
              - id: synthesize
                technique: ai_generation.generation
                config:
                  prompt: "Create comprehensive report"

              - id: validate
                technique: ai_generation.validation

            edges:
              - from: expand
                to: search_internal
              - from: expand
                to: search_external
              - from: search_internal
                to: combine
              - from: search_external
                to: combine
              - from: combine
                to: analyze
              - from: analyze
                to: synthesize
              - from: synthesize
                to: validate
```

### Iterative Refinement Workflow

```yaml
pipelines:
  iterative_refinement:
    shop: workflow_orchestration
    steps:
      - use: workflow_orchestration.graph
        config:
          subtechnique: cyclic
          max_iterations: 5
          graph_definition:
            nodes:
              - id: generate
                technique: ai_generation.generation
                config:
                  temperature: 0.8

              - id: critique
                technique: ai_generation.generation
                config:
                  prompt: |
                    Critique this answer: ${answer}
                    Rate quality 0-10:

              - id: refine
                technique: ai_generation.generation
                config:
                  prompt: |
                    Previous: ${answer}
                    Critique: ${critique}
                    Improved:

            edges:
              - from: generate
                to: critique

              - from: critique
                to: refine
                condition: ${critique.score} < 8

              - from: refine
                to: critique
```

### Adaptive Workflow

```yaml
pipelines:
  adaptive_workflow:
    shop: workflow_orchestration
    steps:
      - use: workflow_orchestration.orchestration
        config:
          subtechnique: conditional
          steps:
            # Classify query complexity
            - name: classify
              technique: ai_generation.generation
              config:
                prompt: "Classify complexity: simple, medium, complex"

            # Simple path
            - name: simple_search
              technique: rag.retrieval
              condition: ${classify.complexity} == "simple"

            # Medium path
            - name: medium_search
              technique: rag.retrieval
              condition: ${classify.complexity} == "medium"
              config:
                top_k: 10

            - name: medium_rerank
              technique: rag.reranking
              condition: ${classify.complexity} == "medium"

            # Complex path
            - name: complex_expand
              technique: rag.query_processing
              condition: ${classify.complexity} == "complex"

            - name: complex_search
              technique: rag.search
              condition: ${classify.complexity} == "complex"
              config:
                subtechnique: hybrid
                top_k: 20

            - name: complex_rerank
              technique: rag.reranking
              condition: ${classify.complexity} == "complex"
              config:
                subtechnique: llm

            - name: complex_consensus
              technique: ai_generation.consensus
              condition: ${classify.complexity} == "complex"
```

## State Management

### State Storage

```yaml
steps:
  - use: workflow_orchestration.state_management
    config:
      backend: redis
      redis_url: "${REDIS_URL}"
      namespace: "workflow:"
      ttl: 3600
```

### State Operations

```python
# Save state
await workflow.save_state(
    workflow_id="workflow_123",
    state={
        "current_step": "generate",
        "iteration": 2,
        "results": {...}
    }
)

# Load state
state = await workflow.load_state("workflow_123")

# Update state
await workflow.update_state(
    workflow_id="workflow_123",
    updates={"current_step": "validate"}
)
```

### Checkpointing

```yaml
shops:
  infrastructure:
    config:
      checkpointing:
        enabled: true
        frequency: 5                   # Checkpoint every 5 steps
        storage: database
```

## Performance Optimization

### Parallel Execution

```yaml
# Execute independent steps in parallel
steps:
  - use: workflow_orchestration.orchestration
    config:
      subtechnique: parallel
      max_concurrent: 10
      steps:
        - name: task1
        - name: task2
        - name: task3
        # All run in parallel
```

### Lazy Evaluation

```yaml
# Only execute steps when needed
steps:
  - use: workflow_orchestration.orchestration
    config:
      lazy: true
      steps:
        - name: expensive_step
          condition: ${needs_expensive_step}
```

### Caching

```yaml
# Cache workflow results
shops:
  infrastructure:
    config:
      caching:
        enabled: true
        ttl: 3600
        cache_key_template: "workflow:${workflow_id}:${step_name}"
```

## Monitoring and Debugging

### Workflow Logging

```yaml
observability:
  logging:
    level: INFO
    workflow_tracing: true
    log_step_transitions: true
    log_state_changes: true
```

### Workflow Metrics

```yaml
observability:
  metrics:
    workflow_duration: true
    step_duration: true
    error_rate: true
    retry_count: true
```

### Workflow Visualization

```bash
# Generate workflow graph
sibyl workflow visualize \
  --pipeline research_workflow \
  --output workflow.png
```

## Further Reading

- **[Technique Catalog](catalog.md)** - All techniques
- **[RAG Pipeline](rag-pipeline.md)** - RAG techniques
- **[AI Generation](ai-generation.md)** - Generation techniques
- **[Graph Patterns](../examples/graph-patterns.md)** - Workflow patterns

---

**Previous**: [AI Generation](ai-generation.md) | **Next**: [Infrastructure Techniques](infrastructure.md)

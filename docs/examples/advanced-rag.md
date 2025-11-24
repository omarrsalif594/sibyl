# Advanced RAG Pipeline Example

Build a production-ready RAG pipeline with advanced techniques including hybrid search, reranking, query processing, and evaluation.

## Overview

This tutorial demonstrates advanced RAG patterns:
- **Hybrid Search:** Combine semantic and keyword search
- **Query Processing:** Expand and rewrite queries for better retrieval
- **Reranking:** Use cross-encoders to improve result quality
- **Citation Tracking:** Show which sources were used
- **Evaluation:** Measure pipeline quality
- **Caching:** Optimize performance

**Time to complete:** 30-40 minutes
**Difficulty:** Intermediate
**Prerequisites:** Complete [Basic RAG Tutorial](./basic-rag.md)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Query Processing                        │
│  • Query Expansion    • Query Rewriting    • Multi-Query     │
└───────────────────┬─────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│                      Hybrid Search                           │
│         ┌────────────────────┬────────────────────┐         │
│         │  Semantic Search   │  Keyword Search    │         │
│         │  (Vector DB)       │  (BM25)           │         │
│         └─────────┬──────────┴─────────┬──────────┘         │
│                   │                    │                     │
│                   └────────┬───────────┘                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                        Reranking                             │
│              Cross-Encoder + Diversity                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                 Generation + Citations                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 1: Advanced Workspace Configuration

**workspace_config.yaml:**
```yaml
workspace_name: advanced_rag_workspace
workspace_description: "Production RAG with advanced techniques"

data_paths:
  documents:
    - path: "data/docs"
      recursive: true
      file_patterns: ["*.md", "*.txt", "*.pdf"]

shops:
  rag_pipeline:
    # Semantic chunking for better boundaries
    chunking:
      technique: semantic
      config:
        max_chunk_size: 1024
        similarity_threshold: 0.7
        min_chunk_size: 256

    # High-quality embeddings
    embedding:
      technique: sentence_transformer
      config:
        model_name: "all-mpnet-base-v2"
        device: "cuda"  # Use GPU if available
        batch_size: 32

    # Query processing
    query_processing:
      multi_query:
        technique: multi_query
        config:
          num_queries: 3
          model: "claude-3-5-sonnet-20241022"

      query_expansion:
        technique: query_expansion
        config:
          expansion_terms: 5
          use_synonyms: true

    # Hybrid search
    search:
      hybrid_search:
        technique: hybrid_search
        config:
          # Vector search component
          vector_search:
            index_type: "HNSW"
            metric: "cosine"
            ef_construction: 200
            m: 16

          # Keyword search component
          keyword_search:
            algorithm: "bm25"
            k1: 1.5
            b: 0.75

          # Fusion weights
          vector_weight: 0.7
          keyword_weight: 0.3
          fusion_method: "rrf"  # Reciprocal Rank Fusion

    # Retrieval
    retrieval:
      technique: semantic_search
      config:
        top_k: 20  # Get more candidates for reranking
        similarity_threshold: 0.6

    # Reranking
    reranking:
      cross_encoder:
        technique: cross_encoder
        config:
          model_name: "cross-encoder/ms-marco-MiniLM-L-12-v2"
          top_k: 5
          batch_size: 16

      diversity:
        technique: diversity_rerank
        config:
          diversity_weight: 0.3
          mmr_lambda: 0.7

  ai_generation:
    # Advanced generation with citations
    generation:
      technique: basic_generation
      config:
        model: "claude-3-5-sonnet-20241022"
        temperature: 0.7
        max_tokens: 3000
        include_citations: true
        citation_format: "numbered"

    # Consensus for critical queries
    consensus:
      technique: hybrid_consensus
      config:
        num_generations: 3
        consensus_threshold: 0.7
        voting_method: "weighted"

  infrastructure:
    # Caching for performance
    caching:
      embedding_cache:
        technique: embedding_cache
        config:
          cache_type: "redis"
          ttl: 86400  # 24 hours

      semantic_cache:
        technique: semantic_cache
        config:
          similarity_threshold: 0.95
          ttl: 3600  # 1 hour

    # Evaluation
    evaluation:
      faithfulness:
        technique: faithfulness
        config:
          check_hallucinations: true
          model: "claude-3-5-sonnet-20241022"

      relevance:
        technique: relevance
        config:
          min_score: 0.7

      groundedness:
        technique: groundedness
        config:
          require_citations: true

providers:
  anthropic:
    api_key_env: ANTHROPIC_API_KEY

  redis:
    host: "localhost"
    port: 6379
    db: 0
```

---

## Step 2: Implement Advanced Pipeline

**advanced_rag.py:**
```python
#!/usr/bin/env python3
"""Advanced RAG pipeline with hybrid search and reranking."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from sibyl.core.application.context import ApplicationContext
from sibyl.core.domain.contracts import QueryRequest, Citation
from sibyl.techniques.data_integration import load_documents, store_vectors
from sibyl.techniques.rag_pipeline import (
    chunking,
    embedding,
    query_processing,
    search,
    retrieval,
    reranking,
)
from sibyl.techniques.ai_generation import generation
from sibyl.techniques.infrastructure import caching, evaluation


@dataclass
class AdvancedRAGResult:
    """Result from advanced RAG pipeline."""
    answer: str
    citations: List[Citation]
    retrieved_chunks: int
    reranked_chunks: int
    confidence_score: float
    evaluation_scores: dict


class AdvancedRAGPipeline:
    """Production-ready RAG pipeline."""

    def __init__(self, workspace_path: str):
        self.ctx = ApplicationContext.from_workspace(workspace_path)
        self.initialized = False

    async def setup(self):
        """Initialize and index documents."""
        print("🚀 Setting up Advanced RAG Pipeline...")

        # Load documents
        print("📚 Loading documents...")
        docs_result = await load_documents.execute(
            ctx=self.ctx,
            technique="loader",
            params={"source": "workspace"}
        )

        if not docs_result.is_success:
            raise ValueError(f"Failed to load documents: {docs_result.error}")

        documents = docs_result.value
        print(f"✅ Loaded {len(documents)} documents")

        # Semantic chunking
        print("🔪 Semantic chunking...")
        chunks_result = await chunking.execute(
            ctx=self.ctx,
            technique="semantic",
            params={"documents": documents}
        )

        if not chunks_result.is_success:
            raise ValueError(f"Failed to chunk: {chunks_result.error}")

        chunks = chunks_result.value
        print(f"✅ Created {len(chunks)} semantic chunks")

        # Embed with caching
        print("🧮 Embedding chunks (with caching)...")
        embeddings_result = await embedding.execute(
            ctx=self.ctx,
            technique="sentence_transformer",
            params={
                "chunks": chunks,
                "use_cache": True
            }
        )

        if not embeddings_result.is_success:
            raise ValueError(f"Failed to embed: {embeddings_result.error}")

        embeddings = embeddings_result.value
        print(f"✅ Created {len(embeddings)} embeddings")

        # Build hybrid index
        print("🔧 Building hybrid search index...")
        store_result = await store_vectors.execute(
            ctx=self.ctx,
            technique="storer",
            params={
                "chunks": chunks,
                "embeddings": embeddings,
                "build_keyword_index": True  # Enable BM25
            }
        )

        if not store_result.is_success:
            raise ValueError(f"Failed to store: {store_result.error}")

        print("✅ Hybrid index built successfully")
        self.initialized = True

    async def query(
        self,
        question: str,
        enable_multi_query: bool = True,
        enable_reranking: bool = True,
        enable_evaluation: bool = True
    ) -> AdvancedRAGResult:
        """Query the pipeline with advanced techniques."""

        if not self.initialized:
            raise RuntimeError("Pipeline not initialized. Call setup() first.")

        print(f"\n{'='*60}")
        print(f"❓ Question: {question}")
        print(f"{'='*60}")

        # Step 1: Query Processing
        queries = [question]
        if enable_multi_query:
            print("🔄 Generating multiple query variations...")
            multi_query_result = await query_processing.execute(
                ctx=self.ctx,
                technique="multi_query",
                params={"query": question}
            )

            if multi_query_result.is_success:
                queries = multi_query_result.value
                print(f"✅ Generated {len(queries)} query variations:")
                for i, q in enumerate(queries, 1):
                    print(f"   {i}. {q}")

        # Step 2: Hybrid Search
        print("🔍 Performing hybrid search...")
        search_result = await search.execute(
            ctx=self.ctx,
            technique="hybrid_search",
            params={
                "queries": queries,
                "top_k": 20
            }
        )

        if not search_result.is_success:
            raise ValueError(f"Search failed: {search_result.error}")

        candidates = search_result.value
        print(f"✅ Retrieved {len(candidates)} candidate chunks")

        # Step 3: Reranking
        final_chunks = candidates
        if enable_reranking:
            print("🎯 Reranking with cross-encoder...")
            rerank_result = await reranking.execute(
                ctx=self.ctx,
                technique="cross_encoder",
                params={
                    "query": question,
                    "chunks": candidates,
                    "top_k": 5
                }
            )

            if rerank_result.is_success:
                final_chunks = rerank_result.value
                print(f"✅ Reranked to top {len(final_chunks)} chunks")

                # Add diversity reranking
                diversity_result = await reranking.execute(
                    ctx=self.ctx,
                    technique="diversity_rerank",
                    params={"chunks": final_chunks}
                )

                if diversity_result.is_success:
                    final_chunks = diversity_result.value
                    print("✅ Applied diversity reranking")

        # Step 4: Build context with citations
        context_parts = []
        citations = []

        for i, chunk in enumerate(final_chunks, 1):
            context_parts.append(f"[{i}] {chunk.content}")
            citations.append(Citation(
                index=i,
                source=chunk.metadata.get("source", "unknown"),
                chunk_id=chunk.id,
                relevance_score=chunk.metadata.get("score", 0.0)
            ))

        context = "\n\n".join(context_parts)

        # Step 5: Generation
        print("🤖 Generating answer with citations...")
        query_request = QueryRequest(
            query=question,
            context=context,
            include_citations=True
        )

        gen_result = await generation.execute(
            ctx=self.ctx,
            technique="basic_generation",
            params={"request": query_request}
        )

        if not gen_result.is_success:
            raise ValueError(f"Generation failed: {gen_result.error}")

        answer = gen_result.value

        # Step 6: Evaluation
        eval_scores = {}
        if enable_evaluation:
            print("📊 Evaluating answer quality...")

            # Faithfulness
            faith_result = await evaluation.execute(
                ctx=self.ctx,
                technique="faithfulness",
                params={
                    "answer": answer,
                    "context": context
                }
            )
            if faith_result.is_success:
                eval_scores["faithfulness"] = faith_result.value

            # Relevance
            rel_result = await evaluation.execute(
                ctx=self.ctx,
                technique="relevance",
                params={
                    "answer": answer,
                    "query": question
                }
            )
            if rel_result.is_success:
                eval_scores["relevance"] = rel_result.value

            # Groundedness
            ground_result = await evaluation.execute(
                ctx=self.ctx,
                technique="groundedness",
                params={
                    "answer": answer,
                    "context": context
                }
            )
            if ground_result.is_success:
                eval_scores["groundedness"] = ground_result.value

            print(f"✅ Evaluation complete")

        # Calculate confidence
        confidence = sum(eval_scores.values()) / len(eval_scores) if eval_scores else 0.0

        return AdvancedRAGResult(
            answer=answer,
            citations=citations,
            retrieved_chunks=len(candidates),
            reranked_chunks=len(final_chunks),
            confidence_score=confidence,
            evaluation_scores=eval_scores
        )


async def main():
    """Main entry point."""

    # Initialize pipeline
    pipeline = AdvancedRAGPipeline("workspaces/advanced_rag_workspace")
    await pipeline.setup()

    print("\n" + "="*60)
    print("Advanced RAG Pipeline Ready!")
    print("="*60)

    # Example queries
    questions = [
        "What security certifications does Acme have?",
        "Compare the pricing tiers and their features",
        "How fast is the response time and what factors affect it?"
    ]

    for question in questions:
        result = await pipeline.query(
            question,
            enable_multi_query=True,
            enable_reranking=True,
            enable_evaluation=True
        )

        # Display results
        print(f"\n💡 Answer:\n{result.answer}\n")

        print(f"📚 Citations:")
        for citation in result.citations:
            print(f"   [{citation.index}] {citation.source} "
                  f"(relevance: {citation.relevance_score:.3f})")

        print(f"\n📊 Quality Metrics:")
        print(f"   Retrieved: {result.retrieved_chunks} chunks")
        print(f"   Reranked: {result.reranked_chunks} chunks")
        print(f"   Confidence: {result.confidence_score:.2%}")

        if result.evaluation_scores:
            print(f"   Evaluation:")
            for metric, score in result.evaluation_scores.items():
                print(f"      - {metric}: {score:.2%}")

        print("\n" + "-"*60)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Step 3: Run Advanced Pipeline

```bash
# Start Redis for caching (optional)
docker run -d -p 6379:6379 redis:latest

# Set API key
export ANTHROPIC_API_KEY="your-api-key"

# Run pipeline
python advanced_rag.py
```

**Expected Output:**
```
🚀 Setting up Advanced RAG Pipeline...
📚 Loading documents...
✅ Loaded 2 documents
🔪 Semantic chunking...
✅ Created 12 semantic chunks
🧮 Embedding chunks (with caching)...
✅ Created 12 embeddings
🔧 Building hybrid search index...
✅ Hybrid index built successfully

============================================================
Advanced RAG Pipeline Ready!
============================================================

============================================================
❓ Question: What security certifications does Acme have?
============================================================
🔄 Generating multiple query variations...
✅ Generated 3 query variations:
   1. What security certifications does Acme have?
   2. Which compliance standards does Acme meet?
   3. What are Acme's security credentials and certifications?
🔍 Performing hybrid search...
✅ Retrieved 20 candidate chunks
🎯 Reranking with cross-encoder...
✅ Reranked to top 5 chunks
✅ Applied diversity reranking
🤖 Generating answer with citations...
📊 Evaluating answer quality...
✅ Evaluation complete

💡 Answer:
Acme AI Assistant has the following security certifications and compliance
standards [1][2]:

- SOC 2 Type II certified
- GDPR compliant

All customer data is encrypted both in transit and at rest, ensuring enterprise-
grade security for your sensitive information [2].

📚 Citations:
   [1] data/docs/faq.md (relevance: 0.892)
   [2] data/docs/faq.md (relevance: 0.854)
   [3] data/docs/product_info.md (relevance: 0.721)

📊 Quality Metrics:
   Retrieved: 20 chunks
   Reranked: 5 chunks
   Confidence: 94.3%
   Evaluation:
      - faithfulness: 0.98
      - relevance: 0.95
      - groundedness: 0.89
```

---

## Advanced Patterns

### Pattern 1: Adaptive Retrieval

Adjust retrieval based on query complexity:

```python
async def adaptive_query(self, question: str):
    """Adaptive retrieval based on query complexity."""

    # Classify query complexity
    complexity = await self._classify_complexity(question)

    if complexity == "simple":
        # Use basic retrieval
        top_k = 3
        enable_reranking = False
    elif complexity == "medium":
        # Standard approach
        top_k = 5
        enable_reranking = True
    else:  # complex
        # Maximum quality
        top_k = 10
        enable_reranking = True
        enable_multi_query = True

    return await self.query(
        question,
        enable_multi_query=enable_multi_query,
        enable_reranking=enable_reranking
    )
```

### Pattern 2: Streaming Responses

Stream answers in real-time:

```python
async def query_streaming(self, question: str):
    """Stream answer generation."""

    # Retrieve context (same as before)
    context = await self._retrieve_context(question)

    # Stream generation
    print("🤖 Answer: ", end="", flush=True)

    async for chunk in generation.execute_streaming(
        ctx=self.ctx,
        technique="basic_generation",
        params={
            "query": question,
            "context": context
        }
    ):
        print(chunk, end="", flush=True)

    print()  # Newline
```

### Pattern 3: Multi-Turn Conversations

Maintain conversation history:

```python
class ConversationalRAG(AdvancedRAGPipeline):
    """RAG with conversation history."""

    def __init__(self, workspace_path: str):
        super().__init__(workspace_path)
        self.history = []

    async def query_with_history(self, question: str):
        """Query with conversation context."""

        # Rewrite query using history
        if self.history:
            rewritten = await self._rewrite_with_history(
                question,
                self.history
            )
        else:
            rewritten = question

        # Standard query
        result = await self.query(rewritten)

        # Update history
        self.history.append({
            "question": question,
            "answer": result.answer
        })

        # Keep last 5 turns
        self.history = self.history[-5:]

        return result
```

---

## Performance Optimization

### Enable GPU Acceleration

```python
# In workspace_config.yaml
embedding:
  config:
    device: "cuda"
    batch_size: 64  # Larger batches on GPU
```

### Use Approximate Search

```python
# HNSW for faster search
search:
  config:
    index_type: "HNSW"
    ef_search: 50  # Lower = faster, less accurate
```

### Enable Redis Caching

```python
# Cache embeddings and results
caching:
  embedding_cache:
    technique: embedding_cache
    config:
      cache_type: "redis"
      ttl: 86400

  semantic_cache:
    technique: semantic_cache
    config:
      similarity_threshold: 0.95
```

---

## Next Steps

1. **Add SQL Integration:** Query structured data alongside documents
2. **Implement Agent Workflows:** Multi-step reasoning with tools
3. **Deploy to Production:** See [Deployment Guide](../operations/deployment.md)
4. **Add Monitoring:** Track metrics with [Observability](../operations/observability.md)

---

## Learn More

- [Query Processing Techniques](../techniques/rag-pipeline.md#query-processing)
- [Reranking Strategies](../techniques/rag-pipeline.md#reranking)
- [Evaluation Metrics](../techniques/infrastructure.md#evaluation)
- [SQL Integration Example](./sql-agent.md)

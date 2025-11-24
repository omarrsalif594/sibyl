# Basic RAG Pipeline Example

A complete, working example of building a basic RAG (Retrieval-Augmented Generation) pipeline with Sibyl.

## Overview

This tutorial walks through creating a simple RAG pipeline that:
- Loads documents from a directory
- Chunks them for processing
- Embeds and stores them in a vector database
- Retrieves relevant context for user queries
- Generates answers using an LLM

**Time to complete:** 15-20 minutes
**Difficulty:** Beginner
**Prerequisites:** Sibyl installed, basic Python knowledge

---

## Step 1: Set Up Your Workspace

First, create a workspace configuration for your RAG pipeline:

```bash
# Create workspace directory
mkdir -p workspaces/my_rag_workspace/data/docs

# Create configuration file
touch workspaces/my_rag_workspace/workspace_config.yaml
```

**workspace_config.yaml:**
```yaml
workspace_name: my_rag_workspace
workspace_description: "Basic RAG pipeline for document Q&A"

data_paths:
  documents:
    - path: "data/docs"
      recursive: true
      file_patterns: ["*.md", "*.txt"]

shops:
  rag_pipeline:
    chunking:
      technique: fixed_size
      config:
        chunk_size: 512
        chunk_overlap: 50

    embedding:
      technique: sentence_transformer
      config:
        model_name: "all-MiniLM-L6-v2"

    search:
      technique: faiss_index
      config:
        index_type: "Flat"
        metric: "cosine"

    retrieval:
      technique: semantic_search
      config:
        top_k: 5
        similarity_threshold: 0.7

  ai_generation:
    generation:
      technique: basic_generation
      config:
        model: "claude-3-5-sonnet-20241022"
        temperature: 0.7
        max_tokens: 2000

providers:
  anthropic:
    api_key_env: ANTHROPIC_API_KEY
```

---

## Step 2: Add Sample Documents

Create some sample documents to work with:

**data/docs/product_info.md:**
```markdown
# Product Information

## Acme AI Assistant

The Acme AI Assistant is a powerful tool for customer support automation.

**Key Features:**
- Natural language understanding
- Multi-language support (15+ languages)
- Integration with existing CRM systems
- 24/7 availability

**Pricing:**
- Starter: $99/month (up to 1,000 queries)
- Professional: $299/month (up to 10,000 queries)
- Enterprise: Custom pricing
```

**data/docs/faq.md:**
```markdown
# Frequently Asked Questions

## General Questions

### What is Acme AI Assistant?
Acme AI Assistant is an enterprise-grade customer support automation platform
powered by advanced natural language processing.

### How does it integrate with my existing systems?
We provide REST APIs, webhooks, and native integrations with popular CRM
platforms including Salesforce, Zendesk, and Intercom.

### Is my data secure?
Yes. All data is encrypted in transit and at rest. We are SOC 2 Type II
certified and GDPR compliant.

## Technical Questions

### What languages are supported?
We support 15+ languages including English, Spanish, French, German, Chinese,
Japanese, and more.

### What's the response time?
Average response time is under 500ms for most queries.
```

---

## Step 3: Initialize the Pipeline

Create a Python script to set up and run the RAG pipeline:

**run_rag.py:**
```python
#!/usr/bin/env python3
"""Basic RAG pipeline example."""

import asyncio
from pathlib import Path

from sibyl.core.application.context import ApplicationContext
from sibyl.core.domain.contracts import QueryRequest
from sibyl.techniques.data_integration import load_documents, store_vectors
from sibyl.techniques.rag_pipeline import chunking, embedding, retrieval
from sibyl.techniques.ai_generation import generation


async def setup_pipeline(workspace_path: str):
    """Initialize the RAG pipeline and index documents."""

    # Create application context
    ctx = ApplicationContext.from_workspace(workspace_path)

    print("📚 Loading documents...")
    # Load documents from workspace
    docs_result = await load_documents.execute(
        ctx=ctx,
        technique="loader",
        params={"source": "workspace"}
    )

    if not docs_result.is_success:
        print(f"❌ Error loading documents: {docs_result.error}")
        return None

    documents = docs_result.value
    print(f"✅ Loaded {len(documents)} documents")

    # Chunk documents
    print("🔪 Chunking documents...")
    chunks_result = await chunking.execute(
        ctx=ctx,
        technique="fixed_size",
        params={"documents": documents}
    )

    if not chunks_result.is_success:
        print(f"❌ Error chunking: {chunks_result.error}")
        return None

    chunks = chunks_result.value
    print(f"✅ Created {len(chunks)} chunks")

    # Embed chunks
    print("🧮 Embedding chunks...")
    embeddings_result = await embedding.execute(
        ctx=ctx,
        technique="sentence_transformer",
        params={"chunks": chunks}
    )

    if not embeddings_result.is_success:
        print(f"❌ Error embedding: {embeddings_result.error}")
        return None

    embeddings = embeddings_result.value
    print(f"✅ Created {len(embeddings)} embeddings")

    # Store in vector database
    print("💾 Storing vectors...")
    store_result = await store_vectors.execute(
        ctx=ctx,
        technique="storer",
        params={
            "chunks": chunks,
            "embeddings": embeddings
        }
    )

    if not store_result.is_success:
        print(f"❌ Error storing vectors: {store_result.error}")
        return None

    print("✅ Vectors stored successfully")
    return ctx


async def query_pipeline(ctx: ApplicationContext, question: str):
    """Query the RAG pipeline."""

    print(f"\n❓ Question: {question}")
    print("🔍 Retrieving relevant context...")

    # Retrieve relevant chunks
    retrieval_result = await retrieval.execute(
        ctx=ctx,
        technique="semantic_search",
        params={"query": question}
    )

    if not retrieval_result.is_success:
        print(f"❌ Error retrieving: {retrieval_result.error}")
        return

    context_chunks = retrieval_result.value
    print(f"✅ Found {len(context_chunks)} relevant chunks")

    # Build context from chunks
    context = "\n\n".join([chunk.content for chunk in context_chunks])

    # Generate answer
    print("🤖 Generating answer...")

    query_request = QueryRequest(
        query=question,
        context=context
    )

    generation_result = await generation.execute(
        ctx=ctx,
        technique="basic_generation",
        params={"request": query_request}
    )

    if not generation_result.is_success:
        print(f"❌ Error generating: {generation_result.error}")
        return

    answer = generation_result.value
    print(f"\n💡 Answer:\n{answer}\n")


async def main():
    """Main entry point."""

    workspace_path = "workspaces/my_rag_workspace"

    # Setup pipeline
    ctx = await setup_pipeline(workspace_path)
    if not ctx:
        return

    print("\n" + "="*60)
    print("RAG Pipeline Ready! Ask me anything about the documents.")
    print("="*60)

    # Example queries
    questions = [
        "What are the pricing tiers for Acme AI Assistant?",
        "What languages are supported?",
        "How does Acme AI Assistant integrate with existing systems?",
        "Is the data secure?"
    ]

    for question in questions:
        await query_pipeline(ctx, question)
        print("-"*60)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Step 4: Run the Pipeline

```bash
# Set your API key
export ANTHROPIC_API_KEY="your-api-key-here"

# Run the pipeline
python run_rag.py
```

**Expected Output:**
```
📚 Loading documents...
✅ Loaded 2 documents
🔪 Chunking documents...
✅ Created 8 chunks
🧮 Embedding chunks...
✅ Created 8 embeddings
💾 Storing vectors...
✅ Vectors stored successfully

============================================================
RAG Pipeline Ready! Ask me anything about the documents.
============================================================

❓ Question: What are the pricing tiers for Acme AI Assistant?
🔍 Retrieving relevant context...
✅ Found 5 relevant chunks
🤖 Generating answer...

💡 Answer:
Acme AI Assistant offers three pricing tiers:

1. **Starter**: $99/month - Includes up to 1,000 queries
2. **Professional**: $299/month - Includes up to 10,000 queries
3. **Enterprise**: Custom pricing for higher volumes

Each tier is designed to scale with your business needs.

------------------------------------------------------------
```

---

## Step 5: Customize and Extend

### Add More Documents

Simply add more `.md` or `.txt` files to `data/docs/` and re-run the pipeline.

### Adjust Chunk Size

Modify the `chunk_size` in `workspace_config.yaml`:

```yaml
shops:
  rag_pipeline:
    chunking:
      config:
        chunk_size: 1024  # Larger chunks
        chunk_overlap: 100
```

### Use Different Embedding Model

```yaml
shops:
  rag_pipeline:
    embedding:
      config:
        model_name: "all-mpnet-base-v2"  # More powerful model
```

### Add Reranking

```yaml
shops:
  rag_pipeline:
    reranking:
      technique: cross_encoder
      config:
        model_name: "cross-encoder/ms-marco-MiniLM-L-6-v2"
        top_k: 3
```

---

## Common Issues and Solutions

### Issue: "No documents found"

**Solution:** Check your `data_paths` configuration and ensure files match `file_patterns`.

### Issue: Low quality answers

**Solutions:**
- Reduce `chunk_size` for more granular context
- Increase `top_k` to retrieve more context
- Adjust `similarity_threshold` to be more/less strict
- Use a more powerful embedding model

### Issue: Slow performance

**Solutions:**
- Use GPU acceleration for embeddings
- Switch to approximate search (HNSW index)
- Enable caching
- Reduce `top_k`

---

## Next Steps

1. **Add Query Processing:** Use query expansion or rewriting for better retrieval
2. **Implement Hybrid Search:** Combine semantic and keyword search
3. **Add Citations:** Track which chunks were used in the answer
4. **Enable Streaming:** Stream answers in real-time
5. **Add Evaluation:** Measure answer quality with metrics

See the [Advanced RAG Tutorial](./advanced-rag.md) for more sophisticated patterns.

---

## Complete Code

The complete working example is available at:
```
examples/basic_rag/
├── workspace_config.yaml
├── run_rag.py
└── data/
    └── docs/
        ├── product_info.md
        └── faq.md
```

Run with:
```bash
cd examples/basic_rag
export ANTHROPIC_API_KEY="your-key"
python run_rag.py
```

---

## Learn More

- [RAG Pipeline Techniques](../techniques/rag-pipeline.md)
- [Chunking Strategies](../techniques/rag-pipeline.md#chunking-techniques)
- [Embedding Models](../techniques/rag-pipeline.md#embedding-techniques)
- [Advanced RAG Tutorial](./advanced-rag.md)

# Glossary

A comprehensive reference of terms and concepts used throughout Sibyl documentation.

## A

### Agent
An autonomous AI system that can perform tasks, make decisions, and interact with tools. In Sibyl, agents can be built using the workflow orchestration techniques.

### API (Application Programming Interface)
A set of protocols and tools for building software applications. Sibyl provides both a Python API and REST API.

### Anthropic
Company that created Claude and the Model Context Protocol (MCP). One of the LLM providers supported by Sibyl.

### Augmentation
The process of enhancing retrieved documents with additional context. See [RAG Pipeline Techniques](techniques/rag-pipeline.md).

## B

### Batch Processing
Processing multiple items together rather than one at a time, often for efficiency. Sibyl supports batch embedding and batch LLM calls.

### BM25
A ranking algorithm used in information retrieval. Used in Sibyl for keyword-based search and reranking.

### Budget
Resource limits set for pipeline execution, including cost (USD), tokens, and API requests. Prevents runaway costs.

### Budget Tracker
Component that monitors resource usage during pipeline execution and enforces limits.

## C

### Caching
Storing computed results to avoid re-computation. Sibyl supports multiple cache levels: embedding cache, retrieval cache, semantic cache, and query cache.

### Chain-of-Thought (CoT)
A generation technique where the LLM explains its reasoning step-by-step before providing a final answer.

### Checkpoint
A saved state of pipeline execution that can be used to resume processing after interruption.

### Chunking
The process of breaking documents into smaller segments for processing. Sibyl supports fixed-size, semantic, markdown-aware, and SQL-aware chunking.

### Circuit Breaker
A resilience pattern that prevents repeated calls to failing services. Part of Sibyl's infrastructure techniques.

### Claude
An LLM family created by Anthropic. Supported as a provider in Sibyl.

### Claude Desktop
Anthropic's desktop application for Claude that supports MCP integrations.

### Config (Configuration)
Settings that control how Sibyl components behave. Typically defined in YAML files.

### Consensus
The process of combining multiple LLM responses to produce a final answer. Sibyl supports quorum voting, weighted voting, and hybrid consensus.

### Context Window
The maximum number of tokens an LLM can process in a single request. Different models have different context windows.

### CoT
See **Chain-of-Thought**.

### Cross-Encoder
A reranking model that scores query-document pairs directly, typically more accurate than bi-encoders but slower.

## D

### Distance Metric
A method for measuring similarity between vectors. Common metrics include cosine similarity, Euclidean distance, and dot product.

### Document
A unit of content to be processed. In Sibyl, documents have an ID, content, and metadata.

### Document Source Provider
A provider that retrieves documents from a specific source (filesystem, database, API, etc.).

### DuckDB
An embedded SQL database that Sibyl uses for vector storage and state persistence.

### DSN (Data Source Name)
A connection string that specifies how to connect to a database or service.

## E

### Embedding
A numerical vector representation of text that captures semantic meaning. Used for similarity search in RAG pipelines.

### Embedding Model
A machine learning model that converts text into embeddings. Examples: sentence-transformers, OpenAI text-embedding-ada-002.

### Embedding Provider
A provider that generates embeddings from text. Sibyl supports OpenAI, sentence-transformers, and fastembed.

### Execution Model
The strategy for running pipeline steps (sequential, parallel, conditional, etc.).

## F

### FAISS
Facebook AI Similarity Search - a library for efficient similarity search. Supported as a vector store in Sibyl.

### Faithfulness
An evaluation metric measuring whether generated answers are supported by the source documents.

### Fastembed
A library for fast, local embedding generation. Supported by Sibyl.

### Fusion
Combining results from multiple search or ranking strategies. Sibyl supports reciprocal rank fusion for reranking.

## G

### Generation
The process of creating text using an LLM. Sibyl supports multiple generation strategies (basic, CoT, ReAct, ToT, self-consistency).

### GPT (Generative Pre-trained Transformer)
OpenAI's family of large language models. Supported as providers in Sibyl.

### Graph
A data structure of nodes and edges. Sibyl uses graphs for workflow orchestration and dependency tracking.

### Groundedness
An evaluation metric measuring whether answers are based on retrieved documents rather than the model's training data.

## H

### Hybrid Search
Combining vector search (semantic) with keyword search (lexical) for improved retrieval.

### HyDE (Hypothetical Document Embeddings)
A query processing technique where the LLM generates a hypothetical answer, which is then embedded and used for retrieval.

## I

### Infrastructure Shop
A collection of techniques for cross-cutting concerns like caching, security, evaluation, and optimization.

### Injection (Prompt Injection)
A security attack where malicious instructions are inserted into prompts to manipulate LLM behavior. Sibyl includes prompt injection detection.

## K

### Keyword Search
Text search based on exact or fuzzy keyword matching (e.g., BM25). Contrasts with semantic search.

## L

### LLM (Large Language Model)
A large neural network trained on vast text corpora that can generate human-like text. Examples: GPT-4, Claude, Llama.

### LLM Provider
A provider that interfaces with an LLM service. Sibyl supports OpenAI, Anthropic, Ollama, and local models.

### Loki
A log aggregation system used in Sibyl's observability stack.

## M

### MCP (Model Context Protocol)
A protocol developed by Anthropic for connecting AI assistants to external tools and data. Sibyl implements an MCP server.

### Metadata
Additional information about a document or chunk (author, date, source, tags, etc.). Used for filtering and augmentation.

### Metric
A measurement used to evaluate system performance (accuracy, latency, cost, etc.).

### Multi-Query
A query processing technique that generates multiple variations of the user's query to improve retrieval.

## N

### NetworkX
A Python library for graph operations used by Sibyl for workflow orchestration.

## O

### Observability
The ability to understand system behavior through logs, metrics, and traces. Sibyl includes comprehensive observability tools.

### Ollama
A platform for running LLMs locally. Supported as a provider in Sibyl.

### OpenAI
Company that created GPT models and provides LLM API services. Supported as a provider in Sibyl.

### Orchestration
Coordinating the execution of multiple steps or components. Sibyl's workflow shop handles orchestration.

## P

### pgvector
PostgreSQL extension for vector similarity search. Supported as a vector store provider in Sibyl.

### PII (Personally Identifiable Information)
Sensitive data that can identify individuals. Sibyl includes PII redaction techniques.

### Pipeline
A sequence of technique executions that transform data and produce results. The core workflow unit in Sibyl.

### Plugin
An extension that adds functionality to Sibyl workspaces. Examples: custom routers, gateways, template systems.

### Prometheus
A metrics collection and monitoring system used in Sibyl's observability stack.

### Protocol
An abstract interface that defines a contract for implementations. Sibyl's protocol layer defines interfaces for all major components.

### Provider
An implementation of a protocol for a specific technology or service. Examples: OpenAI LLM provider, DuckDB vector store provider.

## Q

### Qdrant
A dedicated vector search engine supported as a vector store provider in Sibyl.

### Query
User input or search request. In RAG, queries are processed, expanded, and used to retrieve relevant documents.

### Query Decomposition
Breaking complex queries into simpler sub-queries for better retrieval.

### Query Expansion
Generating additional terms or variations of a query to improve recall.

### Query Rewriting
Transforming a query into a more effective form for retrieval.

### Quorum Voting
A consensus mechanism where the answer supported by a majority of LLM responses is selected.

## R

### RAG (Retrieval-Augmented Generation)
A technique that enhances LLM responses by retrieving relevant documents and including them in the prompt.

### RAG Shop
A collection of techniques for implementing RAG pipelines (chunking, embedding, retrieval, reranking, synthesis).

### Ranking
Ordering retrieved documents by relevance. See also **Reranking**.

### Rate Limiting
Controlling the frequency of API calls to avoid exceeding quotas or overwhelming services.

### ReAct (Reasoning and Acting)
A generation technique where the LLM alternates between reasoning about what to do and taking actions.

### Recall
The proportion of relevant documents that are retrieved. Higher recall means fewer relevant documents are missed.

### Reranking
Re-ordering retrieved documents using more sophisticated relevance scoring. Improves precision over initial retrieval.

### Resilience
The ability to handle failures gracefully. Sibyl includes circuit breakers, retries, and fallback strategies.

### Retrieval
The process of finding relevant documents from a collection based on a query.

### Runtime
The component that orchestrates pipeline execution, manages state, and provides observability.

## S

### Semantic Cache
A cache that matches semantically similar queries rather than exact matches.

### Semantic Search
Search based on meaning rather than keywords. Uses embeddings and vector similarity.

### Sentence Transformer
A type of embedding model that creates high-quality sentence embeddings. Supported by Sibyl.

### Session
A stateful context for multi-turn interactions. Sibyl's workflow shop manages sessions.

### Shop
A collection of related techniques for a specific domain (RAG, AI Generation, Workflow, Infrastructure).

### Similarity Search
Finding items similar to a query by comparing embeddings. Core operation in vector stores.

### State
Data that persists across pipeline executions. Sibyl stores state in DuckDB.

### stdio (Standard Input/Output)
A communication method using stdin and stdout. Used by MCP for Claude Desktop integration.

### Subtechnique
A specific implementation of a technique. For example, "semantic chunking" is a subtechnique of "chunking".

### Synthesis
Combining retrieved documents and a query to generate an answer using an LLM.

## T

### Technique
A modular AI processing component that performs a specific task. Organized into shops.

### Template
A pre-configured pattern for creating workspaces or components. Sibyl includes 26+ workspace templates.

### Token
The basic unit of text processing for LLMs. A token is roughly 4 characters or 0.75 words in English.

### ToT (Tree-of-Thought)
A generation technique that explores multiple reasoning paths in a tree structure to find the best answer.

### Transport
The communication method for MCP (stdio or HTTP).

## U

### Upsert
An operation that inserts a new record or updates an existing one. Used when storing embeddings in vector stores.

## V

### Validation
Checking the quality or correctness of generated content. Sibyl includes validation techniques with retry strategies.

### Vector
A numerical array representing text semantically. Used for similarity comparisons.

### Vector Database
A specialized database optimized for storing and searching vectors. Examples: pgvector, Qdrant, FAISS.

### Vector Store
See **Vector Database**.

### Vector Store Provider
A provider that interfaces with a vector database. Sibyl supports DuckDB, pgvector, Qdrant, and FAISS.

## W

### Weighted Voting
A consensus mechanism where different LLM responses have different weights based on confidence or source credibility.

### Workflow
A complex process involving multiple steps, decisions, and data transformations. Managed by Sibyl's workflow shop.

### Workflow Optimization
Techniques for improving workflow efficiency (adaptive retrieval, early stopping, parallel execution, cost optimization).

### Workspace
A YAML configuration file that defines providers, techniques, pipelines, and settings for a specific environment.

### Workspace Runtime
The component that loads a workspace configuration and executes pipelines within that context.

## Y

### YAML (YAML Ain't Markup Language)
A human-readable data serialization format used for Sibyl configuration files.

---

## See Also

- [Architecture Overview](architecture/overview.md) - System design concepts
- [Core Concepts](architecture/core-concepts.md) - Understanding Sibyl fundamentals
- [Techniques Catalog](techniques/catalog.md) - Complete technique reference
- [FAQ](FAQ.md) - Frequently asked questions

**Not finding a term?** Please [submit an issue](https://github.com/yourusername/sibyl/issues) to request its addition to the glossary.

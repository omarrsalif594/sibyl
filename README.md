# Sibyl

![Sibyl architecture](docs/sibyl-logo.png)

## Status

Sibyl is currently in an early `0.1.x` phase.

- The core ideas (workspaces, pipelines, techniques, plugins) are in place and usable.
- The public APIs are still stabilizing; breaking changes may occur between `0.x` versions.
- Some features are intentionally scoped as extension points or stubs (for example: local specialists, advanced routing policies).

**Requirements**

- Python **3.11+**
- A modern virtual environment (for example: `venv`, `uv`, or `conda`)

**License**

- This project is licensed under the **Apache License 2.0**. See [`LICENSE`](./LICENSE) for details.

---

## What is Sibyl?

Sibyl is a framework for building AI-powered applications around structured **workspaces** and **pipelines**.

It focuses on:

- **RAG-style pipelines**  
  Chunking, embedding, retrieval, reranking, and answer synthesis.
- **Multi-provider support**  
  Support for different LLMs, embedding models, and vector stores via pluggable providers.
- **Technique-based architecture**  
  Reusable, composable “techniques” grouped into domain-specific “shops”.
- **MCP server integration**  
  Expose capabilities via the Model Context Protocol for tools like Claude Desktop.
- **Workspace configuration**  
  YAML-driven configuration for different environments and use cases.
- **Operational hooks**  
  Scripts and conventions for CI, benchmarking, and containerized deployment.

At this stage, Sibyl is suitable for people who want more structure than direct SDK calls, but who are comfortable with evolving APIs and internal changes between minor versions.

---

## Quick Start

### Prerequisites

- Python **3.11+**
- `pyenv` and `uv` (recommended) or `pip`
- Optional: Docker for containerized deployment and observability stack

### Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/yourusername/sibyl.git
cd sibyl

# Using uv (recommended, if available)
./setup.sh

# Or manually with pip (adjust extras to your needs)
pip install -e ".[dev]"
```

### Configure Environment

If an example env file is present:

```bash
cp .env.example .env
```

Then edit `.env` and set any keys you plan to use, for example:

```bash
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-...
QDRANT_URL=http://localhost:6333
```

You do not need all providers enabled; only set variables for the services you intend to use.

### Run Your First Pipeline

The repository includes several "company" examples under `examples/companies/`. For example, to run a simple RAG pipeline in the Northwind example:

```bash
# Build a local index from markdown files
sibyl pipeline run \
  --workspace examples/companies/northwind_analytics/config/workspace.yaml \
  --pipeline build_docs_index_from_markdown

# Query the indexed documents
sibyl pipeline run \
  --workspace examples/companies/northwind_analytics/config/workspace.yaml \
  --pipeline qa_over_docs \
  --param query="What is Sibyl?"
```

### Start MCP Server

You can expose a workspace as an MCP server:

```bash
# Stdio mode (for MCP-aware clients like Claude Desktop)
sibyl-mcp \
  --workspace examples/companies/northwind_analytics/config/workspace.yaml

# HTTP mode
sibyl-mcp \
  --workspace examples/companies/northwind_analytics/config/workspace.yaml \
  --transport http \
  --port 8000
```

---

## Core Concepts

### 🏪 Shops

Shops are collections of related techniques for a particular domain:

- **RAG shop**
  Chunking, embedding, retrieval, reranking, and answer synthesis.

- **AI generation shop**
  Generation strategies, validation passes, multi-step prompting patterns.

- **Workflow shop**
  Orchestration, control flow, session management, and parallel execution.

- **Infrastructure shop**
  Caching, security, evaluation, cost tracking, and related utilities.

Each shop is a place to register and discover techniques that solve similar kinds of problems.

### 🛠️ Techniques

A technique is a modular AI building block with a well-defined interface. Examples include:

- **Chunkers** (fixed-length, semantic, markdown-aware, SQL-aware)
- **Embedders** (OpenAI, sentence-transformer, local models)
- **Retrievers** (vector search, keyword search, hybrid)
- **Rerankers** (cross-encoders, LLM-based rerankers, fusion strategies)
- **Generators** (one-shot, chain-of-thought-style flows, tool-using flows)

Techniques are designed to be swappable: a pipeline can choose which implementation to use via configuration.

### 📦 Workspaces

A workspace is typically defined by a YAML file and contains:

- Provider configuration (LLM, embedding, vector, document sources)
- Shop and technique selections / defaults
- Pipeline definitions (steps, inputs, outputs)
- MCP tool exposure, if used
- Budgets and resource limits

You can maintain different workspaces for different environments (local, staging, production) or different projects.

### 🔗 Providers

Providers encapsulate external services:

- **LLM providers** – clients for models such as OpenAI, Anthropic, Ollama, and others.
- **Embedding providers** – clients for embedding APIs and local models.
- **Vector stores** – connectors for DuckDB, pgvector, Qdrant, FAISS, and similar systems.
- **Document sources** – files, databases, HTTP APIs, and other content sources.

The runtime interacts with providers through abstract interfaces, so you can swap providers without changing pipeline logic.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Application Layer                      │
│         (CLI, REST API, MCP Server, Plugins)            │
├─────────────────────────────────────────────────────────┤
│                   Runtime Layer                         │
│     (Orchestration, Budgets, Tracing, Observability)    │
├─────────────────────────────────────────────────────────┤
│                  Technique Layer                        │
│      (RAG, AI Generation, Workflow, Infrastructure)     │
├─────────────────────────────────────────────────────────┤
│                  Provider Layer                         │
│        (LLM, Embeddings, Vector Stores, Documents)      │
├─────────────────────────────────────────────────────────┤
│                  Protocol Layer                         │
│         (Interfaces, Contracts, Data Types)             │
└─────────────────────────────────────────────────────────┘
```

In practice:

- The application layer exposes Sibyl via CLI commands, REST endpoints, or MCP servers (and plugins such as OpenAI-style tools).
- The runtime loads a workspace, runs pipelines, enforces budgets and timeouts, and emits observability signals.
- The technique layer provides reusable AI building blocks grouped into shops.
- The provider layer integrates external APIs and storage backends.
- The protocol layer defines common interfaces and data structures.

---

## Examples

Sibyl ships with several end-to-end examples under `examples/companies/`:

- **`examples/companies/northwind_analytics/`**
  RAG and analytics over a Northwind-style dataset.

- **`examples/companies/acme_shop/`**
  Basic retail-style time series and product Q&A.

- **`examples/companies/riverbank_finance/`**
  Compliance and analysis flows.

- **`examples/companies/vertex_foundry/`**
  ML experiment and job orchestration.

- **`examples/companies/brightops_agency/`**
  Knowledge-work and agency-style workflows.

Each example usually includes:

- A `config/workspace.yaml` file
- One or more pipelines
- Tests under `tests/examples/`
- Example-specific documentation under `docs/examples/`

These are useful as both documentation and regression tests.

---

## Development

### Running Tests

Some common patterns (depending on which markers are configured in your repo state):

```bash
# Run all tests
pytest

# Unit tests
pytest -m unit

# Integration tests
pytest -m integration

# Example tests without MCP dependencies
pytest -m "examples_e2e and not requires_mcp"

# Guardrail suite
pytest -m guardrail
```

Check `docs/examples/TESTING_CONVENTIONS.md` (if present) for the most accurate, up-to-date test commands and markers.

### Code Quality

If the relevant tools are installed:

```bash
# Format code
black sibyl tests

# Lint code
ruff sibyl tests

# Type checking
mypy sibyl
```

---

## Contributing

Contributions, bug reports, and suggestions are welcome.

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:

- How to set up a development environment
- Coding style and testing expectations
- How to propose changes and open pull requests
- Code of conduct and contribution guidelines

---

## License

Sibyl is released under the [Apache License 2.0](LICENSE).

---

## Support & Links

- **Documentation**: [docs/](docs/)
- **Issues**: https://github.com/yourusername/sibyl/issues
- **Discussions**: https://github.com/yourusername/sibyl/discussions

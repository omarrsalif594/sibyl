# Getting Started with Sibyl

Welcome to Sibyl! This guide will help you get up and running with the Sibyl Universal AI Assistant Platform.

## What You'll Learn

By the end of this guide, you'll be able to:

- Install Sibyl and its dependencies
- Configure your first workspace
- Run a RAG pipeline to index and query documents
- Start an MCP server for integration with Claude Desktop
- Understand core concepts and next steps

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11 or higher** installed
- **Git** for cloning the repository
- **API key** for at least one LLM provider (OpenAI, Anthropic, or local Ollama)
- **4GB+ RAM** (8GB+ recommended for production)
- **Basic familiarity** with Python, YAML, and command-line tools

### Recommended Tools

- **pyenv** - Python version management
- **uv** - Fast Python package installer (or use pip)
- **Docker** - For containerized deployment (optional)
- **VS Code** or **PyCharm** - For development (optional)

## Installation

### Quick Install (Recommended)

The easiest way to get started is using the setup script:

```bash
# Clone the repository
git clone https://github.com/yourusername/sibyl.git
cd sibyl

# Run the automated setup script
./setup.sh
```

The setup script will:
1. Check for pyenv and uv (install instructions provided if missing)
2. Install Python 3.11.9 via pyenv
3. Create a virtual environment
4. Install all dependencies with uv
5. Set up pre-commit hooks

### Manual Install

If you prefer manual installation:

```bash
# Clone the repository
git clone https://github.com/yourusername/sibyl.git
cd sibyl

# Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Sibyl with all optional dependencies
pip install -e ".[dev,vector,monitoring,rest]"

# Verify installation
sibyl --version
```

### Installation Options

Install only what you need:

```bash
# Minimal install (core only)
pip install -e .

# Development install (includes testing tools)
pip install -e ".[dev]"

# Production install (includes monitoring)
pip install -e ".[vector,monitoring]"

# Full install (everything)
pip install -e ".[dev,vector,monitoring,rest]"
```

## Configuration

### Set Up Environment Variables

Create a `.env` file with your API keys:

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

At minimum, configure one LLM provider:

```bash
# .env file
# OpenAI (recommended for getting started)
OPENAI_API_KEY=sk-your-openai-key-here

# Or Anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Or use local Ollama (no API key needed, install Ollama first)
# No configuration needed if running Ollama locally
```

### Verify Installation

Test that everything is working:

```bash
# Activate virtual environment if not already active
source .venv/bin/activate

# Check Sibyl CLI
sibyl --help

# Run a quick test
pytest tests/core/unit -k test_workspace_loading --maxfail=1
```

## Your First Pipeline

Let's create a simple RAG pipeline to index and query documents.

### Step 1: Prepare Sample Documents

Create a directory with some markdown documents:

```bash
# Create a docs directory
mkdir -p my_docs

# Create sample documents
cat > my_docs/introduction.md << 'EOF'
# Introduction to AI

Artificial Intelligence (AI) refers to the simulation of human intelligence
in machines programmed to think and learn like humans.

Key areas of AI include:
- Machine Learning
- Natural Language Processing
- Computer Vision
- Robotics
EOF

cat > my_docs/machine_learning.md << 'EOF'
# Machine Learning

Machine Learning is a subset of AI that enables systems to learn and improve
from experience without being explicitly programmed.

Types of Machine Learning:
1. Supervised Learning
2. Unsupervised Learning
3. Reinforcement Learning
EOF
```

### Step 2: Choose a Workspace Configuration

Sibyl comes with 26+ pre-configured workspace examples. For this tutorial, we'll use the local DuckDB workspace:

```bash
# View available workspace configurations
ls config/workspaces/

# We'll use this one for local development
cat config/workspaces/local_docs_duckdb.yaml
```

This workspace uses:
- **DuckDB** for vector storage (embedded, no server needed)
- **Sentence Transformers** for local embeddings
- **OpenAI GPT** for text generation

### Step 3: Index Your Documents

Run the indexing pipeline to process your documents:

```bash
# Index markdown documents into the vector store
sibyl pipeline run \
  --workspace config/workspaces/local_docs_duckdb.yaml \
  --pipeline build_docs_index_from_markdown \
  --param source_path=my_docs \
  --param pattern="**/*.md"
```

You should see output like:

```
[INFO] Loading workspace: config/workspaces/local_docs_duckdb.yaml
[INFO] Initializing providers...
[INFO] Starting pipeline: build_docs_index_from_markdown
[INFO] Step 1/4: Loading documents... (2 documents found)
[INFO] Step 2/4: Chunking documents... (8 chunks created)
[INFO] Step 3/4: Generating embeddings... (8 embeddings generated)
[INFO] Step 4/4: Storing in vector database... (8 vectors stored)
[SUCCESS] Pipeline completed in 5.2s
[INFO] Indexed 2 documents, 8 chunks
```

### Step 4: Query Your Documents

Now query the indexed documents:

```bash
# Ask a question about your documents
sibyl pipeline run \
  --workspace config/workspaces/local_docs_duckdb.yaml \
  --pipeline qa_over_docs \
  --param query="What are the types of machine learning?" \
  --param top_k=3
```

Expected output:

```
[INFO] Loading workspace: config/workspaces/local_docs_duckdb.yaml
[INFO] Starting pipeline: qa_over_docs
[INFO] Step 1/5: Processing query...
[INFO] Step 2/5: Retrieving relevant documents... (3 chunks retrieved)
[INFO] Step 3/5: Reranking results...
[INFO] Step 4/5: Augmenting context...
[INFO] Step 5/5: Generating answer...
[SUCCESS] Pipeline completed in 2.3s

Answer: There are three main types of machine learning:
1. Supervised Learning
2. Unsupervised Learning
3. Reinforcement Learning

These are the primary categories that enable systems to learn and improve
from experience without being explicitly programmed.

Sources: machine_learning.md
```

### Step 5: Try Different Queries

Experiment with different questions:

```bash
# Ask about AI in general
sibyl pipeline run \
  --workspace config/workspaces/local_docs_duckdb.yaml \
  --pipeline qa_over_docs \
  --param query="What is artificial intelligence?"

# Ask for a specific area
sibyl pipeline run \
  --workspace config/workspaces/local_docs_duckdb.yaml \
  --pipeline qa_over_docs \
  --param query="Name the key areas of AI"
```

## Understanding What Just Happened

Let's break down the RAG pipeline you just ran:

### 1. Document Loading
```
my_docs/*.md → Document objects with content and metadata
```

### 2. Chunking
```
Large documents → Smaller, manageable chunks (512 tokens each)
```

### 3. Embedding
```
Text chunks → Numerical vectors (embeddings) that capture meaning
```

### 4. Vector Storage
```
Embeddings → Stored in DuckDB vector database for fast similarity search
```

### 5. Query Processing
```
User question → Embedded → Similar vectors retrieved → Context assembled
```

### 6. Answer Generation
```
Context + Question → LLM → Natural language answer with citations
```

## Using the MCP Server

Sibyl can act as an MCP (Model Context Protocol) server, exposing its capabilities to AI assistants like Claude Desktop.

### Start the MCP Server

```bash
# Start MCP server in stdio mode (for Claude Desktop)
sibyl-mcp --workspace config/workspaces/local_docs_duckdb.yaml

# Or in HTTP mode (for web integrations)
sibyl-mcp \
  --workspace config/workspaces/local_docs_duckdb.yaml \
  --transport http \
  --port 8000
```

### Configure Claude Desktop

Add Sibyl to your Claude Desktop configuration:

**On macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**On Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sibyl": {
      "command": "/path/to/sibyl/.venv/bin/sibyl-mcp",
      "args": [
        "--workspace",
        "/path/to/sibyl/config/workspaces/local_docs_duckdb.yaml"
      ]
    }
  }
}
```

Restart Claude Desktop, and you'll see Sibyl's tools available!

### Test in Claude Desktop

Try asking Claude:
> "Use the search_documents tool to find information about machine learning"

Claude will use Sibyl's MCP server to query your indexed documents!

## Next Steps

Congratulations! You've successfully:
- ✅ Installed Sibyl
- ✅ Indexed documents into a vector database
- ✅ Queried documents with natural language
- ✅ Started an MCP server

### Where to Go From Here

#### 📚 Learn Core Concepts
- [Architecture Overview](architecture/overview.md) - Understand Sibyl's design
- [Core Concepts](architecture/core-concepts.md) - Shops, techniques, workspaces
- [Workspaces](workspaces/configuration.md) - Configure for your use case

#### 🛠️ Explore Techniques
- [Techniques Catalog](techniques/catalog.md) - Browse all available techniques
- [RAG Pipeline](techniques/rag-pipeline.md) - Deep dive into RAG
- [Custom Techniques](techniques/custom-techniques.md) - Build your own

#### 🎯 Try Examples
- [Examples Overview](examples/overview.md) - Real-world use cases
- [Company Examples](../examples/companies/) - Fictional company scenarios
- [Tutorials](tutorials/document-qa.md) - Step-by-step guides

#### 🚀 Deploy to Production
- [Deployment Guide](operations/deployment.md) - Production deployment
- [Observability](operations/observability.md) - Monitoring and metrics
- [Docker Deployment](operations/docker.md) - Containerized setup

#### 💻 Extend Sibyl
- [Developer Guide](extending/developer-guide.md) - Contribute to Sibyl
- [Custom Providers](extending/custom-providers.md) - Integrate new services
- [Testing Guide](extending/testing-guide.md) - Write tests

## Common Issues

### Issue: API Key Not Found

**Error**: `OpenAIError: No API key provided`

**Solution**: Ensure your `.env` file is in the project root and contains your API key:
```bash
# Check if .env exists
ls -la .env

# Verify contents (without exposing the key)
grep OPENAI_API_KEY .env
```

### Issue: Python Version Too Old

**Error**: `requires-python = ">=3.11"`

**Solution**: Install Python 3.11+ using pyenv:
```bash
# Install pyenv (if not already installed)
curl https://pyenv.run | bash

# Install Python 3.11
pyenv install 3.11.9
pyenv local 3.11.9
```

### Issue: Module Not Found

**Error**: `ModuleNotFoundError: No module named 'sibyl'`

**Solution**: Install Sibyl in editable mode:
```bash
pip install -e ".[dev,vector]"
```

### Issue: Permission Denied on setup.sh

**Error**: `Permission denied: ./setup.sh`

**Solution**: Make the script executable:
```bash
chmod +x setup.sh
./setup.sh
```

## Getting Help

If you're stuck:

1. **Check the docs**: Browse [documentation](README.md)
2. **Search issues**: Look through [GitHub Issues](https://github.com/yourusername/sibyl/issues)
3. **Ask questions**: Post in [GitHub Discussions](https://github.com/yourusername/sibyl/discussions)
4. **Read the FAQ**: Check [FAQ.md](FAQ.md) for common questions

## Summary

You've learned how to:
- Install Sibyl and its dependencies
- Configure API keys and workspaces
- Run RAG pipelines to index and query documents
- Start an MCP server for AI assistant integration
- Navigate Sibyl's documentation

Ready to dive deeper? Check out the [Architecture Overview](architecture/overview.md) to understand how Sibyl works under the hood!

---

**Next**: [Installation Guide](installation.md) | [Quick Start](quick-start.md) | [Architecture](architecture/overview.md)

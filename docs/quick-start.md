# Quick Start: 5-Minute RAG Pipeline

Get Sibyl up and running with a complete RAG pipeline in just 5 minutes.

## Prerequisites

- Python 3.11+ installed
- OpenAI API key (or Anthropic/Ollama)
- Terminal/command line access

## 1. Install (1 minute)

```bash
# Clone and setup
git clone https://github.com/yourusername/sibyl.git
cd sibyl
./setup.sh

# Activate environment
source .venv/bin/activate
```

## 2. Configure (30 seconds)

```bash
# Set your API key
cp .env.example .env
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

## 3. Index Documents (2 minutes)

```bash
# Create sample documents
mkdir -p quickstart_docs

cat > quickstart_docs/ai.md << 'EOF'
# What is AI?
Artificial Intelligence (AI) is intelligence demonstrated by machines,
as opposed to natural intelligence displayed by humans and animals.
EOF

cat > quickstart_docs/ml.md << 'EOF'
# Machine Learning
Machine Learning is a subset of AI that enables systems to learn
from data without being explicitly programmed.
EOF

# Index them
sibyl pipeline run \
  --workspace config/workspaces/local_docs_duckdb.yaml \
  --pipeline build_docs_index_from_markdown \
  --param source_path=quickstart_docs
```

## 4. Query (1 minute)

```bash
# Ask a question
sibyl pipeline run \
  --workspace config/workspaces/local_docs_duckdb.yaml \
  --pipeline qa_over_docs \
  --param query="What is machine learning?"
```

## 5. View Results (30 seconds)

You should see:

```
Answer: Machine Learning is a subset of AI that enables systems to
learn from data without being explicitly programmed.

Sources: ml.md
Confidence: High
Retrieved chunks: 1
Processing time: 1.2s
```

## 🎉 Congratulations!

You've successfully:
- ✅ Installed Sibyl
- ✅ Indexed documents
- ✅ Ran a RAG query
- ✅ Got AI-powered answers

## What Just Happened?

```
Your Documents
      ↓
  [Chunking] ← Break into smaller pieces
      ↓
  [Embedding] ← Convert to numerical vectors
      ↓
  [Vector DB] ← Store in DuckDB
      ↓
  [Query] ← Your question
      ↓
  [Retrieval] ← Find relevant chunks
      ↓
  [LLM] ← Generate answer
      ↓
  [Answer] ← With citations!
```

## Try More

### Different Questions

```bash
sibyl pipeline run \
  --workspace config/workspaces/local_docs_duckdb.yaml \
  --pipeline qa_over_docs \
  --param query="How is ML related to AI?"
```

### Add More Documents

```bash
cat > quickstart_docs/nlp.md << 'EOF'
# Natural Language Processing
NLP is a branch of AI that helps computers understand human language.
EOF

# Re-index
sibyl pipeline run \
  --workspace config/workspaces/local_docs_duckdb.yaml \
  --pipeline build_docs_index_from_markdown \
  --param source_path=quickstart_docs
```

### Start MCP Server

```bash
# For Claude Desktop integration
sibyl-mcp --workspace config/workspaces/local_docs_duckdb.yaml
```

## Next Steps

### Learn the Concepts (10 minutes)
- [Core Concepts](architecture/core-concepts.md)
- [Architecture](architecture/overview.md)

### Customize Your Setup (20 minutes)
- [Workspaces](workspaces/configuration.md)
- [Techniques](techniques/catalog.md)

### Try Real Examples (30 minutes)
- [Company Examples](examples/overview.md)
- [Tutorials](tutorials/document-qa.md)

### Deploy to Production (60 minutes)
- [Deployment Guide](operations/deployment.md)
- [Docker Setup](operations/docker.md)

## Common Commands Cheat Sheet

```bash
# Index documents
sibyl pipeline run \
  --workspace <workspace.yaml> \
  --pipeline build_docs_index_from_markdown \
  --param source_path=<path>

# Query documents
sibyl pipeline run \
  --workspace <workspace.yaml> \
  --pipeline qa_over_docs \
  --param query="<your question>"

# Start MCP server
sibyl-mcp --workspace <workspace.yaml>

# Validate workspace
sibyl workspace validate <workspace.yaml>

# List available pipelines
sibyl pipeline list --workspace <workspace.yaml>

# Run tests
pytest -m unit

# View help
sibyl --help
```

## Troubleshooting

### API Key Not Working
```bash
# Check if loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"
```

### Pipeline Fails
```bash
# Enable debug logging
export SIBYL_LOG_LEVEL=DEBUG
sibyl pipeline run ... # your command
```

### Import Errors
```bash
# Reinstall in editable mode
pip install -e ".[dev,vector]"
```

## Need Help?

- **Full Guide**: [Getting Started](getting-started.md)
- **Installation**: [Installation Guide](installation.md)
- **FAQ**: [Frequently Asked Questions](FAQ.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/sibyl/issues)

---

**⏱️ Time to complete**: 5 minutes
**💰 Estimated cost**: $0.001 - $0.01 USD (using OpenAI)
**📊 Difficulty**: Beginner

Ready for more? Check out the [Getting Started Guide](getting-started.md) for a comprehensive tutorial!

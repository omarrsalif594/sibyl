# Examples & Tutorials

Practical examples and step-by-step tutorials for building with Sibyl.

---

## Getting Started Examples

### [Basic RAG Pipeline](./basic-rag.md)
**Difficulty:** Beginner | **Time:** 15-20 minutes

Build your first RAG pipeline with document loading, chunking, embedding, and retrieval.

**What you'll learn:**
- Load and index documents
- Perform semantic search
- Generate answers with LLMs
- Basic configuration

**Prerequisites:** Sibyl installed, basic Python knowledge

---

### [MCP Integration](./mcp-integration.md)
**Difficulty:** Beginner | **Time:** 15 minutes

Expose Sibyl capabilities as MCP tools for Claude Desktop and other MCP clients.

**What you'll learn:**
- Configure MCP server
- Expose techniques as tools
- Connect Claude Desktop
- Use REST API

**Prerequisites:** Sibyl installed, Claude Desktop (optional)

---

## Intermediate Examples

### [Advanced RAG Pipeline](./advanced-rag.md)
**Difficulty:** Intermediate | **Time:** 30-40 minutes

Build a production-ready RAG pipeline with hybrid search, reranking, and evaluation.

**What you'll learn:**
- Hybrid search (semantic + keyword)
- Cross-encoder reranking
- Query processing and expansion
- Answer quality evaluation
- Performance optimization

**Prerequisites:** Complete [Basic RAG](./basic-rag.md)

---

### [SQL Agent](./sql-agent.md)
**Difficulty:** Intermediate | **Time:** 20-25 minutes

Create an intelligent agent that queries SQL databases using natural language.

**What you'll learn:**
- Text-to-SQL generation
- Query validation and safety
- Result interpretation
- Hybrid SQL + document search

**Prerequisites:** Basic SQL knowledge

---

## Advanced Examples

### [Agent Workflows](./agent-workflow.md)
**Difficulty:** Advanced | **Time:** 25-30 minutes

Build sophisticated AI agents with multi-step workflows and tool orchestration.

**What you'll learn:**
- Workflow planning and orchestration
- Multi-tool integration (RAG, SQL, web search)
- Dynamic tool selection
- Error recovery and retry logic

**Prerequisites:** Understanding of RAG and SQL agents

---

### [Custom Techniques](./custom-technique.md)
**Difficulty:** Intermediate | **Time:** 20 minutes

Extend Sibyl by creating your own custom techniques.

**What you'll learn:**
- Technique structure and contracts
- Implement custom logic
- Register and use techniques
- Package for distribution
- Testing best practices

**Prerequisites:** Python development experience

---

## Example Projects

Complete example projects with full source code:

### E-commerce Q&A System
```
examples/ecommerce_qa/
├── workspace_config.yaml
├── setup.py
├── data/
│   ├── docs/           # Product documentation
│   └── ecommerce.db    # Sales database
└── src/
    ├── rag_pipeline.py
    ├── sql_agent.py
    └── hybrid_search.py
```

**Features:**
- Product documentation search
- Sales data queries
- Customer support automation
- Multi-language support

**Run it:**
```bash
cd examples/ecommerce_qa
python -m pip install -e .
python src/hybrid_search.py
```

---

### Financial Analysis Agent
```
examples/financial_analysis/
├── workspace_config.yaml
├── data/
│   ├── reports/        # Financial reports (PDF)
│   ├── filings/        # SEC filings
│   └── market_data.db  # Market data
└── src/
    ├── document_analysis.py
    ├── data_queries.py
    └── report_generator.py
```

**Features:**
- PDF document analysis
- Financial data queries
- Automated report generation
- Time-series analysis

---

### Developer Documentation Assistant
```
examples/doc_assistant/
├── workspace_config.yaml
├── data/
│   └── docs/           # Technical documentation
└── src/
    ├── semantic_search.py
    ├── code_examples.py
    └── mcp_server.py
```

**Features:**
- Technical documentation search
- Code example extraction
- API reference queries
- MCP integration for IDEs

---

## Quick Start Templates

### Minimal RAG
```yaml
# workspace_config.yaml
workspace_name: minimal_rag

data_paths:
  documents:
    - path: "data/docs"

shops:
  rag_pipeline:
    retrieval:
      technique: semantic_search

  ai_generation:
    generation:
      technique: basic_generation
```

### SQL + RAG Hybrid
```yaml
workspace_name: hybrid

data_paths:
  documents:
    - path: "data/docs"
  database:
    - path: "data/db.sqlite"

shops:
  rag_pipeline:
    retrieval:
      technique: semantic_search

  data_integration:
    query_sql:
      technique: query

  ai_generation:
    generation:
      technique: basic_generation
```

### Multi-Agent Workflow
```yaml
workspace_name: multi_agent

shops:
  rag_pipeline:
    retrieval:
      technique: semantic_search

  data_integration:
    query_sql:
      technique: query

  workflow_orchestration:
    orchestration:
      routing:
        technique: routing
```

---

## Learning Paths

### Path 1: RAG Developer
1. [Basic RAG](./basic-rag.md) - Fundamentals
2. [Advanced RAG](./advanced-rag.md) - Production patterns
3. [Custom Techniques](./custom-technique.md) - Extend capabilities

### Path 2: Data Analyst
1. [SQL Agent](./sql-agent.md) - Natural language to SQL
2. [Basic RAG](./basic-rag.md) - Document search
3. [Agent Workflows](./agent-workflow.md) - Combine capabilities

### Path 3: Platform Developer
1. [MCP Integration](./mcp-integration.md) - Expose as tools
2. [Custom Techniques](./custom-technique.md) - Build custom logic
3. [Agent Workflows](./agent-workflow.md) - Orchestrate workflows

---

## Getting Help

- **Questions?** Check the [FAQ](../FAQ.md)
- **Concepts unclear?** See [Glossary](../GLOSSARY.md)
- **Issues?** Read [Troubleshooting](../operations/troubleshooting.md)
- **Contributing?** See [Contributing Guide](../../CONTRIBUTING.md)

---

## Next Steps

After completing the examples:

1. **Deploy to Production:** [Deployment Guide](../operations/deployment.md)
2. **Optimize Performance:** [Performance Tuning](../operations/performance-tuning.md)
3. **Add Monitoring:** [Observability](../operations/observability.md)
4. **Secure Your Application:** [Security Best Practices](../operations/security.md)

---

## Community Examples

Share your examples with the community! See [Contributing Examples](../../CONTRIBUTING.md#contributing-examples).

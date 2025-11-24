# Sibyl Documentation

Welcome to the Sibyl documentation! This comprehensive guide will help you understand, use, and extend the Sibyl Universal AI Assistant Platform.

## Documentation Structure

### 🚀 Getting Started

New to Sibyl? Start here:

- **[Getting Started Guide](getting-started.md)** - Prerequisites, installation, and first steps
- **[Installation](installation.md)** - Detailed installation for different environments
- **[Quick Start](quick-start.md)** - 5-minute tutorial to run your first RAG pipeline

### 🏗️ Architecture & Concepts

Understand how Sibyl works:

- **[Architecture Overview](architecture/overview.md)** - System design and layered architecture
- **[Core Concepts](architecture/core-concepts.md)** - Techniques, shops, workspaces, pipelines
- **[Data Flow](architecture/data-flow.md)** - How data flows through the system
- **[Design Patterns](architecture/design-patterns.md)** - Common patterns and best practices

### ⚙️ Configuration & Workspaces

Configure Sibyl for your use case:

- **[Workspace Overview](workspaces/overview.md)** - Understanding workspaces
- **[Configuration Guide](workspaces/configuration.md)** - Complete schema documentation
- **[Provider Configuration](workspaces/providers.md)** - LLM, embedding, and vector store setup
- **[Shops & Techniques](workspaces/shops-and-techniques.md)** - Selecting and configuring techniques
- **[MCP Tools](workspaces/mcp-tools.md)** - Exposing MCP tools in workspaces
- **[Best Practices](workspaces/best-practices.md)** - Workspace design patterns

### 🛠️ Techniques Reference

Explore available AI processing techniques:

- **[Techniques Catalog](techniques/catalog.md)** - Complete catalog with decision guide
- **[RAG Pipeline](techniques/rag-pipeline.md)** - Chunking, embedding, retrieval, reranking
- **[AI Generation](techniques/ai-generation.md)** - Generation strategies, consensus, validation
- **[Workflow Orchestration](techniques/workflow-orchestration.md)** - Session management, graph workflows
- **[Infrastructure](techniques/infrastructure.md)** - Caching, security, evaluation, optimization
- **[Custom Techniques](techniques/custom-techniques.md)** - Creating your own techniques

### 📚 API Reference

Technical API documentation:

- **[API Overview](api/README.md)** - API structure and quick reference
- **[Core APIs](api/core.md)** - Application context, configuration, and base classes
- **[Contracts](api/contracts.md)** - Data models and contracts
- **[Result Pattern](api/result.md)** - Error handling with Result type
- **[Protocols](api/protocols.md)** - Interface definitions

### 🔌 MCP Integration

Model Context Protocol integration:

- **[MCP Overview](mcp/overview.md)** - MCP capabilities and architecture
- **[Server Setup](mcp/server-setup.md)** - Running MCP server (HTTP and stdio)
- **[Client Integration](mcp/client-integration.md)** - Integrating with Claude Desktop
- **[Tool Exposure](mcp/tool-exposure.md)** - Exposing tools through MCP
- **[REST API](mcp/rest-api.md)** - REST API facade and OpenAI compatibility

### 🔧 Plugins & Extensions

Extend Sibyl's capabilities:

- **[Plugins Overview](plugins/README.md)** - Plugin system architecture and available plugins
- **[Plugin Development](plugins/development.md)** - Creating custom plugins
- **[Plugin Distribution](plugins/distribution.md)** - Packaging and sharing plugins

### 📖 Examples & Tutorials

Learn by doing:

- **[Examples Overview](examples/README.md)** - Index of all examples with learning paths
- **[Basic RAG Pipeline](examples/basic-rag.md)** - Build your first RAG pipeline (Beginner)
- **[Advanced RAG](examples/advanced-rag.md)** - Production RAG with hybrid search (Intermediate)
- **[SQL Agent](examples/sql-agent.md)** - Natural language to SQL queries (Intermediate)
- **[Agent Workflows](examples/agent-workflow.md)** - Multi-tool agent orchestration (Advanced)
- **[Custom Techniques](examples/custom-technique.md)** - Creating custom techniques (Intermediate)
- **[MCP Integration](examples/mcp-integration.md)** - Exposing tools via MCP (Beginner)

### 🚢 Operations & Deployment

Deploy Sibyl to production:

- **[Deployment Guide](operations/deployment.md)** - Production deployment strategies
- **[Observability](operations/observability.md)** - Monitoring, metrics, and logging
- **[Troubleshooting](operations/troubleshooting.md)** - Common issues and solutions
- **[Performance Tuning](operations/performance-tuning.md)** - Optimization guide
- **[Security](operations/security.md)** - Security best practices and hardening
- **[Docker Deployment](operations/docker.md)** - Containerized deployment guide

### 💻 Development & Extending

Contribute to Sibyl:

- **[Testing Guide](development/testing-guide.md)** - Unit, integration, and E2E testing
- **[Code Style Guide](development/code-style.md)** - Code conventions and best practices

### 🔄 Migrations

Upgrade and migration guides:

- **[Migration Guide](migrations/README.md)** - Version upgrades and framework migrations
- **[From LangChain](migrations/README.md#from-langchain)** - Migrating from LangChain
- **[From LlamaIndex](migrations/README.md#from-llamaindex)** - Migrating from LlamaIndex

### 🎓 Advanced Topics

Deep dives into advanced features:

- **[Advanced Overview](advanced/README.md)** - Advanced patterns and architectures
- **[Agent Patterns](advanced/agent-patterns.md)** - Self-healing and multi-agent systems
- **[Performance Optimization](advanced/performance.md)** - Scaling and optimization techniques
- **[Production Architecture](advanced/production-architecture.md)** - Enterprise deployment patterns
- **[Security Deep Dive](advanced/security.md)** - Advanced security implementations

### 📝 Additional Resources

- **[FAQ](FAQ.md)** - Frequently asked questions
- **[Glossary](GLOSSARY.md)** - Terms and definitions
- **[Contributing](../CONTRIBUTING.md)** - How to contribute to Sibyl
- **[Changelog](../CHANGELOG.md)** - Version history and release notes

## Quick Navigation by Role

### 👤 I'm a User

Building AI applications with Sibyl:

1. Start with [Getting Started](getting-started.md)
2. Learn [Core Concepts](architecture/core-concepts.md)
3. Explore [Techniques Catalog](techniques/catalog.md)
4. Follow [Examples & Tutorials](examples/overview.md)
5. Configure [Workspaces](workspaces/configuration.md)

### 👨‍💻 I'm a Developer

Extending Sibyl with custom components:

1. Read the [Developer Guide](extending/developer-guide.md)
2. Understand [Architecture](architecture/overview.md)
3. Review [API Reference](api/overview.md)
4. Learn about [Custom Techniques](techniques/custom-techniques.md)
5. Follow [Testing Guide](extending/testing-guide.md)

### 🚀 I'm a DevOps Engineer

Deploying Sibyl to production:

1. Check [Deployment Guide](operations/deployment.md)
2. Set up [Observability](operations/observability.md)
3. Review [Security](operations/security.md) practices
4. Learn [Performance Tuning](operations/performance-tuning.md)
5. Use [Troubleshooting](operations/troubleshooting.md) guide

### 🔌 I'm Integrating MCP

Using Sibyl as an MCP server:

1. Read [MCP Overview](mcp/overview.md)
2. Follow [Server Setup](mcp/server-setup.md)
3. Configure [Client Integration](mcp/client-integration.md)
4. Learn [Tool Exposure](mcp/tool-exposure.md)
5. Use [REST API](mcp/rest-api.md) if needed

## Documentation Conventions

### Code Examples

Code examples are provided in context with full working samples:

```python
# Example code blocks include imports and are runnable
from sibyl.runtime import load_workspace_runtime

runtime = load_workspace_runtime("config/workspaces/example.yaml")
result = await runtime.run_pipeline("my_pipeline")
```

### File References

File paths and line numbers are provided for easy navigation:

- `sibyl/techniques/rag_pipeline/chunking.py:45` - Chunking implementation
- `config/workspaces/local_docs_duckdb.yaml` - Example workspace configuration

### Callouts

Special notes are highlighted:

> **Note**: Additional information or clarification

> **Warning**: Important warnings about potential issues

> **Tip**: Helpful tips and best practices

> **Deprecated**: Features that will be removed in future versions

## Documentation Status

| Section | Status | Last Updated |
|---------|--------|--------------|
| Getting Started | ✅ Complete | 2025-11-24 |
| Architecture | ✅ Complete | 2025-11-24 |
| Workspaces | ✅ Complete | 2025-11-24 |
| Techniques | ✅ Complete | 2025-11-24 |
| API Reference | ✅ Complete | 2025-11-24 |
| MCP Integration | ✅ Complete | 2025-11-24 |
| Plugins | ✅ Complete | 2025-11-24 |
| Examples | ✅ Complete | 2025-11-24 |
| Operations | ✅ Complete | 2025-11-24 |
| Development | ✅ Complete | 2025-11-24 |
| Migrations | ✅ Complete | 2025-11-24 |
| Advanced Topics | ✅ Complete | 2025-11-24 |

## Contributing to Documentation

Found an error or want to improve the docs?

1. Documentation source is in `/docs/`
2. Follow the [Contributing Guide](../CONTRIBUTING.md)
3. Submit a pull request with your changes
4. Ensure all links work and examples are tested

## Getting Help

- **Search**: Use the search function (if available) or `grep` through docs
- **Examples**: Check [examples/](../examples/) for working code
- **Issues**: Report documentation issues on [GitHub](https://github.com/yourusername/sibyl/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/yourusername/sibyl/discussions)

---

**Documentation Version**: 0.1.0
**Last Updated**: 2025-11-24
**Sibyl Version**: 0.1.0+

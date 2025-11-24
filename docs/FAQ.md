# Frequently Asked Questions (FAQ)

## General Questions

### What is Sibyl?

Sibyl is a Universal AI Assistant Platform that provides a flexible, production-ready framework for building AI-powered applications. It features advanced RAG pipelines, multi-provider support, and a technique-based architecture that allows you to mix and match different AI processing components.

### Who should use Sibyl?

Sibyl is designed for:

- **Developers** building AI applications with RAG capabilities
- **Data Scientists** experimenting with different AI techniques and models
- **Organizations** needing a production-ready AI infrastructure
- **Integrators** looking to expose AI capabilities through MCP (Model Context Protocol)

### How is Sibyl different from other RAG frameworks?

Sibyl stands out with:

- **Technique-based architecture**: Modular, swappable components organized into "shops"
- **Workspace configuration**: YAML-driven setup for different environments
- **Multi-provider support**: Work with multiple LLMs and vector stores simultaneously
- **MCP integration**: Native Model Context Protocol server capabilities
- **Production focus**: Built-in observability, monitoring, and DevOps tooling

### Is Sibyl open source?

Yes, Sibyl is released under the Apache License 2.0, allowing free use, modification, and distribution.

## Installation & Setup

### What are the system requirements?

- **Python**: 3.11 or higher
- **RAM**: Minimum 4GB, recommended 8GB+ for production
- **Storage**: Varies by use case (vector stores can be large)
- **OS**: Linux, macOS, Windows (with WSL recommended)

### Do I need GPU for Sibyl?

No, GPU is not required. However, if you're using local embedding models or LLMs, a GPU can significantly improve performance.

### How do I install Sibyl?

```bash
# Clone the repository
git clone https://github.com/yourusername/sibyl.git
cd sibyl

# Run the setup script
./setup.sh

# Or install manually
pip install -e ".[dev,vector,monitoring]"
```

See [Installation Guide](installation.md) for details.

### Which API keys do I need?

At minimum, you need **one LLM provider API key**:

- **OpenAI**: For GPT models (`OPENAI_API_KEY`)
- **Anthropic**: For Claude models (`ANTHROPIC_API_KEY`)
- **Ollama**: No API key needed (run locally)

Optional keys for enhanced features:

- **EmbedDing providers**: OpenAI embeddings (can use local models instead)
- **Other LLM providers**: Cohere, Together, etc.

### Can I use Sibyl without external APIs?

Yes! You can run Sibyl completely offline using:

- **Ollama** for local LLMs
- **Sentence Transformers** for local embeddings
- **DuckDB** for local vector storage

See [Multi-Provider Setup](examples/multi-provider.md) for configuration.

## Usage & Features

### What is a "workspace"?

A workspace is a YAML configuration file that defines:

- Which providers to use (LLM, embeddings, vector stores)
- Which techniques and shops to enable
- Pipeline definitions
- MCP tool exposure settings
- Budget and resource limits

Workspaces allow you to have different configurations for development, staging, and production.

### What is a "technique"?

A technique is a modular AI processing component that performs a specific task, such as:

- Chunking documents
- Generating embeddings
- Retrieving relevant context
- Reranking results
- Generating answers

Techniques are organized into "shops" (collections) and can have multiple implementations (subtechniques).

### What is a "shop"?

A shop is a collection of related techniques for a specific domain:

- **RAG Shop**: Document processing, retrieval, and synthesis
- **AI Generation Shop**: Content generation and validation
- **Workflow Shop**: Orchestration and session management
- **Infrastructure Shop**: Cross-cutting concerns (caching, security, evaluation)

### How do I create a custom technique?

See [Custom Techniques Guide](techniques/custom-techniques.md) for a complete tutorial. In brief:

```python
from sibyl.techniques.base import BaseTechnique

class MyTechnique(BaseTechnique):
    async def execute(self, input_data, config):
        # Your processing logic
        return {"result": processed_data}
```

### Can I use multiple LLM providers in the same pipeline?

Yes! You can configure multiple LLM providers in your workspace and route different steps to different providers. For example:

- Use GPT-4 for complex reasoning
- Use GPT-3.5 for simple tasks
- Use Claude for long context processing
- Use Ollama for cost-sensitive operations

See [Multi-Provider Setup](examples/multi-provider.md).

### How do I monitor costs?

Sibyl includes built-in budget tracking:

```yaml
budget:
  max_cost_usd: 1.0
  max_tokens: 100000
  max_requests: 50
```

Set budgets at workspace, pipeline, or step level. The budget tracker monitors usage in real-time and stops execution when limits are reached.

## MCP Integration

### What is MCP?

MCP (Model Context Protocol) is a protocol developed by Anthropic for connecting AI assistants to external tools and data sources. Sibyl can act as an MCP server, exposing its AI capabilities to MCP clients like Claude Desktop.

### How do I use Sibyl with Claude Desktop?

1. Start Sibyl MCP server:
   ```bash
   sibyl-mcp --workspace config/workspaces/your-workspace.yaml
   ```

2. Configure Claude Desktop to connect to Sibyl

3. Use exposed tools in Claude conversations

See [Client Integration Guide](mcp/client-integration.md).

### Can I expose custom tools through MCP?

Yes! Configure tool exposure in your workspace:

```yaml
mcp:
  tools:
    - name: search_documents
      description: "Search indexed documents"
      pipeline: qa_over_docs
```

See [Tool Exposure](mcp/tool-exposure.md).

### What's the difference between stdio and HTTP transport?

- **stdio**: Communication through standard input/output (used by Claude Desktop)
- **HTTP**: Communication through HTTP REST API (for web integrations)

Choose based on your integration needs. See [Server Setup](mcp/server-setup.md).

## Performance & Scaling

### How many documents can Sibyl handle?

Sibyl can handle:

- **Development**: Thousands of documents with DuckDB
- **Production**: Millions of documents with pgvector or Qdrant
- **Large-scale**: Billions with dedicated vector databases

Performance depends on your vector store choice and infrastructure.

### How can I improve retrieval performance?

Strategies for better performance:

1. **Use hybrid search**: Combine vector and keyword search
2. **Enable reranking**: Improve result quality
3. **Tune chunk size**: Balance granularity and context
4. **Use semantic caching**: Cache frequent queries
5. **Add query expansion**: Improve recall
6. **Optimize embeddings**: Use faster embedding models
7. **Scale infrastructure**: Use dedicated vector databases

See [Performance Tuning](operations/performance-tuning.md).

### Does Sibyl support distributed deployment?

Yes, Sibyl can be deployed in distributed configurations:

- **Horizontal scaling**: Multiple server instances behind load balancer
- **Separate components**: Dedicated vector store, separate LLM instances
- **Caching layers**: Redis for shared caching

See [Distributed Deployment](advanced/distributed-deployment.md).

### How do I reduce LLM costs?

Cost optimization strategies:

1. **Use appropriate models**: Don't use GPT-4 when GPT-3.5 suffices
2. **Implement caching**: Cache embedding and LLM responses
3. **Enable budget limits**: Prevent runaway costs
4. **Optimize prompts**: Reduce token usage
5. **Use local models**: Ollama for development/testing
6. **Batch operations**: Process in batches when possible

See [Cost Optimization](advanced/cost-optimization.md).

## Troubleshooting

### My pipeline is slow. How do I debug it?

1. **Enable observability**: Check logs and metrics
2. **Profile steps**: Identify bottlenecks
3. **Check providers**: Ensure external APIs are responsive
4. **Review configuration**: Look for inefficient settings
5. **Monitor resources**: Check CPU, memory, network usage

See [Troubleshooting Guide](operations/troubleshooting.md).

### I'm getting authentication errors with my LLM provider

Common solutions:

1. **Check API key**: Verify key is correct in `.env`
2. **Check environment**: Ensure `.env` is loaded
3. **Verify provider**: Check provider is configured correctly in workspace
4. **Test API key**: Use provider's CLI or curl to test key
5. **Check quotas**: Ensure you haven't exceeded rate limits

### Vector search returns irrelevant results

Improvements to try:

1. **Adjust chunk size**: Smaller chunks = more precise, larger = more context
2. **Try different embedding models**: Some models work better for your domain
3. **Enable reranking**: Add cross-encoder or LLM reranking
4. **Use query expansion**: Expand user queries for better matching
5. **Add metadata filtering**: Filter by document type, date, etc.
6. **Tune similarity threshold**: Adjust minimum similarity score

### How do I enable debug logging?

Set logging level in your workspace or environment:

```yaml
# In workspace YAML
logging:
  level: DEBUG
  format: detailed
```

Or via environment variable:
```bash
export SIBYL_LOG_LEVEL=DEBUG
sibyl pipeline run ...
```

## Development

### How do I contribute to Sibyl?

See [Contributing Guide](../CONTRIBUTING.md) for:

- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

### How do I run tests?

```bash
# Run all tests
pytest

# Run specific categories
pytest -m unit
pytest -m integration

# Run with coverage
pytest --cov=sibyl --cov-report=html
```

See [Testing Guide](extending/testing-guide.md).

### Where can I find example code?

Examples are located in several places:

- **`/examples/`**: Complete example applications
- **`/config/workspaces/`**: 26+ workspace configurations
- **Documentation**: Code snippets throughout docs
- **Tests**: Real-world usage in `/tests/`

See [Examples Overview](examples/overview.md).

## Security & Privacy

### Is my data secure with Sibyl?

Sibyl includes several security features:

- **PII redaction**: Automatically detect and redact sensitive information
- **Content filtering**: Block inappropriate content
- **Access control**: Role-based access control (configurable)
- **Audit logging**: Track all operations
- **Prompt injection detection**: Detect and block malicious prompts

However, when using external LLM providers, data is sent to those services. Use local models for sensitive data.

See [Security Guide](operations/security.md).

### Can I run Sibyl completely on-premises?

Yes! Use:

- **Ollama** for local LLMs
- **Sentence Transformers** for local embeddings
- **DuckDB** or **local pgvector** for vector storage
- **Local deployment** via Docker

No data leaves your infrastructure.

### How do I handle sensitive documents?

Best practices:

1. **Use local models**: Keep data on-premises
2. **Enable PII redaction**: Automatic sensitive data detection
3. **Implement access control**: Restrict who can query what
4. **Encrypt at rest**: Use encrypted storage
5. **Enable audit logs**: Track all access
6. **Review provider policies**: Understand where data goes

## Still Have Questions?

- **Documentation**: Search the [docs](README.md)
- **Examples**: Browse [examples/](../examples/)
- **Issues**: Check [GitHub Issues](https://github.com/yourusername/sibyl/issues)
- **Discussions**: Ask in [GitHub Discussions](https://github.com/yourusername/sibyl/discussions)
- **Chat**: Join our community (link TBD)

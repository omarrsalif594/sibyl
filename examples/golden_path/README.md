# Golden Path: Web Research with Sibyl

This is **THE** reference implementation for using Sibyl. It demonstrates the flagship `prod_web_research.yaml` workspace and serves as the template for all Sibyl deployments.

## Overview

This example showcases:

1. **Production-ready workspace configuration** (`config/workspaces/prod_web_research.yaml`)
2. **Two flagship pipelines**:
   - `web_research`: Full RAG pipeline with query processing, retrieval, augmentation, and generation
   - `summarize_url`: Fast URL content summarization
3. **Proper provider management**: LLM, embeddings, vector store, and MCP providers
4. **Error handling and observability**: Trace IDs, logging, and result processing
5. **Multiple execution modes**: Python script and MCP server

## Quick Start

### Prerequisites

1. **Python 3.11+** installed
2. **Sibyl installed**:
   ```bash
   pip install -e /path/to/sibyl
   # or
   pip install sibyl-mcp
   ```

3. **API Keys** (for cloud providers):
   ```bash
   export OPENAI_API_KEY=your-openai-api-key
   ```

### Run the Example

```bash
cd examples/golden_path
python run_web_research.py
```

This runs both flagship pipelines with demo data and shows the complete workflow.

## What Gets Executed

### Pipeline 1: web_research

**Input**: Research query
**Flow**:
1. Query processing (expand and extract keywords)
2. Document retrieval (semantic search in vector store)
3. Context augmentation (add metadata and limit tokens)
4. Response generation (with citations)
5. Quality validation (check quality and citations)

**Output**: Comprehensive research response with sources

### Pipeline 2: summarize_url

**Input**: URL
**Flow**:
1. Content chunking (split into manageable pieces)
2. Embedding generation (for semantic analysis)
3. Summary generation (concise, fast summary)

**Output**: Concise summary of URL content

## Usage Examples

### 1. Run Full Demo (Both Pipelines)

```bash
python run_web_research.py
```

Shows the complete golden path with both pipelines.

### 2. Run Specific Pipeline with Custom Query

```bash
python run_web_research.py --pipeline web_research --query "What is machine learning?"
```

### 3. Summarize a URL

```bash
python run_web_research.py --pipeline summarize_url --url "https://example.com/article"
```

### 4. Use Custom Workspace

```bash
python run_web_research.py --workspace /path/to/my_workspace.yaml
```

### 5. Verbose Output for Debugging

```bash
python run_web_research.py --verbose
```

### 6. Pass Additional Parameters

```bash
python run_web_research.py --pipeline web_research \
  --query "What is AI?" \
  --param top_k=20 \
  --param include_citations=true
```

## Using via MCP Server

The pipelines in `prod_web_research.yaml` are exposed as MCP tools and can be used by AI assistants like Claude Code.

### 1. Start the MCP Server

```bash
python -m sibyl.server.mcp_server --workspace config/workspaces/prod_web_research.yaml
```

### 2. Configure Your AI Assistant

Add to your MCP configuration (e.g., Claude Code settings):

```json
{
  "mcpServers": {
    "sibyl-web-research": {
      "command": "python",
      "args": ["-m", "sibyl.server.mcp_server", "--workspace", "/path/to/prod_web_research.yaml"]
    }
  }
}
```

### 3. Use in AI Assistant

The assistant can now call:

- `web_research(query="What is RAG?", top_k=10, include_citations=true)`
- `summarize_url(url="https://example.com", max_length=500)`

## Understanding the Workspace Configuration

The `prod_web_research.yaml` workspace is structured as follows:

### Providers

```yaml
providers:
  llm:
    default: # OpenAI GPT-4 for high-quality generation
    fast:    # GPT-3.5-turbo for faster, cheaper operations

  embeddings:
    default: # OpenAI text-embedding-3-small

  vector_store:
    default: # DuckDB for local vector storage

  mcp:
    browser:     # Optional: Web browsing capabilities
    filesystem:  # Optional: File operations
```

### Shop: web_research_shop

Combines techniques from RAG and AI generation domains:

```yaml
techniques:
  # RAG
  chunker: "rag_pipeline.chunking:semantic"
  embedder: "rag_pipeline.embedding:openai"
  retriever: "rag_pipeline.retrieval:semantic_search"
  augmenter: "rag_pipeline.augmentation:context"

  # AI Generation
  generator: "ai_generation.generation:basic"
  validator: "ai_generation.validation:qc_verdict"

  # Query Processing
  query_processor: "rag_pipeline.query_processing:standard"
```

### Pipelines

**web_research**: 5-step comprehensive research pipeline
**summarize_url**: 3-step fast summarization pipeline

### MCP Tools

Both pipelines are exposed as MCP tools with JSON schemas for validation.

## Customization

### Modify Provider Configuration

Edit `config/workspaces/prod_web_research.yaml`:

```yaml
providers:
  llm:
    default:
      provider: "anthropic"  # Use Claude instead
      model: "claude-3-5-sonnet-20241022"
      api_key_env: "ANTHROPIC_API_KEY"
```

### Add Custom Technique

1. Implement your technique in `sibyl/techniques/`
2. Register in `sibyl/techniques/registry.py`
3. Add to shop in workspace:

```yaml
shops:
  web_research_shop:
    techniques:
      my_custom_technique: "my_category.my_technique:implementation"
```

### Add Pipeline Step

```yaml
pipelines:
  web_research:
    steps:
      - use: "web_research_shop.query_processor"
      - use: "web_research_shop.my_custom_technique"  # Add here
      - use: "web_research_shop.retriever"
      # ... rest of steps
```

### Adjust Timeouts

```yaml
pipelines:
  web_research:
    timeout_s: 600  # Increase to 10 minutes
```

## Environment Variables

Required for cloud providers:

```bash
# OpenAI (default)
export OPENAI_API_KEY=sk-...

# Anthropic (if using Claude)
export ANTHROPIC_API_KEY=sk-ant-...

# Optional: Custom endpoints
export OPENAI_BASE_URL=https://custom-endpoint.com
```

## Troubleshooting

### Workspace Validation Error

```
WorkspaceLoadError: Workspace validation failed
```

**Solution**: Validate the workspace file:
```bash
# Check syntax
python -c "import yaml; yaml.safe_load(open('config/workspaces/prod_web_research.yaml'))"

# Validate against schema
python -m sibyl.workspace.loader config/workspaces/prod_web_research.yaml
```

### Missing API Key

```
Error: OPENAI_API_KEY environment variable not set
```

**Solution**: Set the required API key:
```bash
export OPENAI_API_KEY=your-api-key-here
```

### Technique Not Found

```
TechniqueResolutionError: Technique 'chunker' not found in shop
```

**Solution**: Check that:
1. Technique is registered in `sibyl/techniques/registry.py`
2. Technique mapping is correct in workspace YAML
3. Technique implementation exists

### Pipeline Timeout

```
PipelineExecutionError: Pipeline 'web_research' timed out after 300s
```

**Solution**: Increase timeout in workspace:
```yaml
pipelines:
  web_research:
    timeout_s: 600  # Increase timeout
```

### Provider Build Failed

```
Failed to create LLM provider 'default': Provider not available
```

**Solution**:
1. Check API keys are set
2. Verify provider type is supported
3. Check network connectivity for cloud providers

## Architecture Notes

### Why This is the "Golden Path"

1. **Production-ready**: Uses battle-tested providers and techniques
2. **Well-documented**: Clear configuration and usage examples
3. **Extensible**: Easy to customize for specific use cases
4. **Observable**: Built-in trace IDs and logging
5. **Multi-modal**: Works via Python API and MCP server
6. **Reference implementation**: Other workspaces should follow this pattern

### Design Principles

1. **Explicit over implicit**: All configuration in YAML, no magic
2. **Composability**: Techniques are building blocks for pipelines
3. **Separation of concerns**: Providers, shops, pipelines are distinct
4. **Fail-fast validation**: Errors caught early with clear messages
5. **Production-first**: Timeouts, error handling, observability built-in

## Next Steps

### For Users

1. **Run this example** to understand the workflow
2. **Modify parameters** to see how pipelines adapt
3. **Try via MCP** to integrate with AI assistants
4. **Read the docs**: `docs/getting_started.md` and `docs/architecture/`

### For Developers

1. **Study the workspace**: `config/workspaces/prod_web_research.yaml`
2. **Understand the runtime**: `sibyl/runtime/pipeline/workspace_runtime.py`
3. **Explore techniques**: `sibyl/techniques/registry.py`
4. **Build custom shops**: Add domain-specific technique collections
5. **Contribute back**: Share your pipelines and techniques

## Resources

- **Workspace Schema**: `sibyl/workspace/schema.py`
- **Technique Registry**: `sibyl/techniques/registry.py`
- **Runtime Implementation**: `sibyl/runtime/pipeline/`
- **Provider Factories**: `sibyl/runtime/providers/`
- **MCP Server**: `sibyl/server/mcp_server.py`

## Feedback and Contributions

This is the flagship example - feedback is welcome!

- Report issues: GitHub Issues
- Propose enhancements: Pull Requests
- Ask questions: Discussions

## License

Apache License 2.0 - See repository root for details

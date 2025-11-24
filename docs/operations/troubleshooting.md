# Troubleshooting Guide

Complete guide to diagnosing and resolving common issues in Sibyl.

## Overview

This guide covers common issues, their symptoms, causes, and solutions. Use the table of contents to quickly find your issue.

## Quick Diagnostics

### Health Check

```bash
# Check overall system health
curl http://localhost:8001/health | jq '.'

# Check specific component
curl http://localhost:8001/health/database | jq '.'
```

### View Logs

```bash
# Recent logs
tail -f /var/log/sibyl/app.log

# Errors only
grep ERROR /var/log/sibyl/app.log | tail -20

# Specific component
grep "component.*rag" /var/log/sibyl/app.log | tail -20
```

### Check Metrics

```bash
# Get metrics
curl http://localhost:9090/metrics | grep sibyl

# Error rate
curl http://localhost:9090/metrics | grep sibyl_mcp_tool_errors_total
```

## Installation Issues

### Python Version Error

**Symptom**:
```
ERROR: Python 3.11 or higher is required
```

**Cause**: Wrong Python version

**Solution**:
```bash
# Check Python version
python --version

# Use pyenv to install correct version
pyenv install 3.11.7
pyenv global 3.11.7

# Or use specific Python
python3.11 -m venv .venv
```

### Dependency Installation Fails

**Symptom**:
```
ERROR: Could not install package X
```

**Cause**: Missing system dependencies or conflicting versions

**Solution**:
```bash
# Update pip
pip install --upgrade pip setuptools wheel

# Install system dependencies
# Ubuntu/Debian
sudo apt-get install python3.11-dev build-essential

# macOS
brew install python@3.11

# Reinstall with verbose output
pip install -e ".[vector,monitoring]" --verbose
```

### Import Errors

**Symptom**:
```python
ImportError: cannot import name 'X' from 'sibyl'
```

**Cause**: Incorrect installation or missing dependencies

**Solution**:
```bash
# Reinstall in editable mode
pip uninstall sibyl
pip install -e ".[dev,vector,monitoring]"

# Verify installation
python -c "import sibyl; print(sibyl.__version__)"
```

## Configuration Issues

### Workspace Validation Fails

**Symptom**:
```
ValidationError: Invalid workspace configuration
```

**Cause**: Invalid YAML or missing required fields

**Solution**:
```bash
# Validate workspace
sibyl workspace validate config/workspaces/my_workspace.yaml

# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config/workspaces/my_workspace.yaml'))"

# Common issues:
# - Incorrect indentation (use spaces, not tabs)
# - Missing required fields (name, providers, etc.)
# - Invalid provider configuration
```

**Example fixes**:
```yaml
# ❌ Bad - tabs instead of spaces
providers:
	llm:  # This uses a tab

# ✅ Good - spaces
providers:
  llm:    # This uses spaces

# ❌ Bad - missing required field
providers:
  llm:
    primary:
      kind: openai
      # Missing api_key

# ✅ Good
providers:
  llm:
    primary:
      kind: openai
      api_key: "${OPENAI_API_KEY}"
```

### Environment Variables Not Found

**Symptom**:
```
KeyError: 'OPENAI_API_KEY'
```

**Cause**: Environment variable not set

**Solution**:
```bash
# Check if variable is set
echo $OPENAI_API_KEY

# Set temporarily
export OPENAI_API_KEY=sk-...

# Set permanently (add to .bashrc or .zshrc)
echo 'export OPENAI_API_KEY=sk-...' >> ~/.bashrc
source ~/.bashrc

# Use .env file
cat > .env << EOF
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://...
EOF

# Load .env (automatically loaded by Sibyl)
export $(cat .env | xargs)
```

### Provider Connection Failed

**Symptom**:
```
ConnectionError: Failed to connect to provider
```

**Cause**: Invalid credentials or provider unavailable

**Solution**:
```bash
# Test OpenAI connection
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test database connection
psql $DATABASE_URL -c "SELECT 1"

# Test Redis connection
redis-cli -u $REDIS_URL ping

# Check provider configuration
sibyl workspace validate --check providers config/workspaces/my_workspace.yaml
```

## Pipeline Execution Issues

### Pipeline Not Found

**Symptom**:
```
PipelineNotFoundError: Pipeline 'my_pipeline' not found
```

**Cause**: Pipeline not defined in workspace

**Solution**:
```bash
# List available pipelines
sibyl pipeline list --workspace config/workspaces/my_workspace.yaml

# Check pipeline definition
grep -A 10 "my_pipeline:" config/workspaces/my_workspace.yaml

# Ensure pipeline is defined:
```yaml
pipelines:
  my_pipeline:  # Must match the name you're using
    shop: rag
    steps:
      - use: rag.retrieval
```

### Technique Not Found

**Symptom**:
```
TechniqueNotFoundError: Technique 'rag.unknown' not found
```

**Cause**: Invalid technique name or shop not enabled

**Solution**:
```bash
# List available techniques
sibyl technique list

# Check if shop is enabled
```yaml
shops:
  rag:
    enabled: true  # Must be enabled

pipelines:
  my_pipeline:
    shop: rag
    steps:
      - use: rag.retrieval  # Correct technique name
```

**Available techniques**:
- RAG: `rag.chunking`, `rag.embedding`, `rag.retrieval`, `rag.reranking`
- AI Gen: `ai_generation.generation`, `ai_generation.consensus`
- Workflow: `workflow_orchestration.session_management`, `workflow_orchestration.graph`
- Infrastructure: `infrastructure.caching`, `infrastructure.security`

### Parameter Validation Error

**Symptom**:
```
ValidationError: Parameter 'query' is required
```

**Cause**: Missing or invalid parameter

**Solution**:
```bash
# Check parameter requirements
sibyl pipeline describe --workspace config/workspaces/my_workspace.yaml --pipeline my_pipeline

# Provide required parameters
sibyl pipeline run \
  --workspace config/workspaces/my_workspace.yaml \
  --pipeline search_docs \
  --param query="your question"  # Required parameter
  --param top_k=5                # Optional parameter
```

## Vector Store Issues

### DuckDB File Locked

**Symptom**:
```
Error: database is locked
```

**Cause**: Another process has the DuckDB file open

**Solution**:
```bash
# Find processes using the file
lsof ./data/vectors.duckdb

# Kill the process
kill <PID>

# Or use a different file
```yaml
providers:
  vector_store:
    main:
      kind: duckdb
      dsn: "duckdb://./data/vectors_new.duckdb"
```

### pgvector Connection Pool Exhausted

**Symptom**:
```
PoolError: Connection pool exhausted
```

**Cause**: Too many concurrent connections

**Solution**:
```yaml
providers:
  vector_store:
    main:
      kind: pgvector
      dsn: "${DATABASE_URL}"
      pool_size: 50              # Increase pool size
      max_overflow: 20           # Allow overflow
      pool_timeout: 60           # Longer timeout
```

### Vector Dimension Mismatch

**Symptom**:
```
DimensionError: Vector dimension mismatch (expected 384, got 1536)
```

**Cause**: Embedding model changed but vector store not updated

**Solution**:
```bash
# Option 1: Re-index with correct model
sibyl pipeline run \
  --workspace config/workspaces/my_workspace.yaml \
  --pipeline build_docs_index

# Option 2: Update provider to match
```yaml
providers:
  embedding:
    default:
      kind: sentence-transformer
      model: all-MiniLM-L6-v2    # 384 dimensions

  vector_store:
    main:
      kind: duckdb
      dimension: 384              # Must match embedding
```

## LLM Provider Issues

### Rate Limit Exceeded

**Symptom**:
```
RateLimitError: Rate limit exceeded
```

**Cause**: Too many requests to LLM provider

**Solution**:
```yaml
# Add retry logic
providers:
  llm:
    primary:
      kind: openai
      model: gpt-4
      max_retries: 5
      retry_delay: 2.0
      exponential_backoff: true

# Or use rate limiting
shops:
  infrastructure:
    config:
      rate_limiting:
        enabled: true
        requests_per_minute: 60
```

### Timeout Error

**Symptom**:
```
TimeoutError: Request timed out after 60s
```

**Cause**: LLM taking too long to respond

**Solution**:
```yaml
providers:
  llm:
    primary:
      kind: openai
      timeout: 120              # Increase timeout to 2 minutes
      max_tokens: 1000          # Reduce tokens for faster response

# Or use streaming
steps:
  - use: ai_generation.generation
    config:
      subtechnique: streaming
```

### Token Limit Exceeded

**Symptom**:
```
TokenLimitError: Context length exceeded (10000 > 8192)
```

**Cause**: Input + output exceeds model's context window

**Solution**:
```yaml
# Reduce chunk size
steps:
  - use: rag.chunking
    config:
      chunk_size: 256           # Smaller chunks
      chunk_overlap: 25

# Or use context compression
steps:
  - use: workflow_orchestration.context_management
    config:
      subtechnique: compression
      max_tokens: 4000
```

### Invalid API Key

**Symptom**:
```
AuthenticationError: Invalid API key
```

**Cause**: Wrong or expired API key

**Solution**:
```bash
# Verify API key
echo $OPENAI_API_KEY

# Test directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Update API key
export OPENAI_API_KEY=sk-new-key

# Or in workspace
```yaml
providers:
  llm:
    primary:
      api_key: "${OPENAI_API_KEY}"  # From environment
```

## MCP Server Issues

### MCP Server Won't Start

**Symptom**:
```
Error: Failed to start MCP server
```

**Cause**: Invalid configuration or port already in use

**Solution**:
```bash
# Check if port is in use
lsof -i :8000

# Use different port
sibyl-mcp \
  --workspace config/workspaces/my_workspace.yaml \
  --port 8001

# Check workspace validity
sibyl workspace validate config/workspaces/my_workspace.yaml

# Check logs
tail -f ~/.sibyl/logs/mcp_server.log
```

### Claude Desktop Can't Connect

**Symptom**: Tools don't appear in Claude Desktop

**Cause**: Configuration issues

**Solution**:
```bash
# Check Claude Desktop config
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Use absolute paths
```json
{
  "mcpServers": {
    "sibyl": {
      "command": "/Users/username/sibyl/.venv/bin/sibyl-mcp",
      "args": [
        "--workspace",
        "/Users/username/sibyl/config/workspaces/docs.yaml"
      ]
    }
  }
}
```

```bash
# Test server independently
/Users/username/sibyl/.venv/bin/sibyl-mcp \
  --workspace /Users/username/sibyl/config/workspaces/docs.yaml

# Restart Claude Desktop
killall Claude
open -a Claude
```

### Tool Not Found

**Symptom**:
```
ToolNotFoundError: Tool 'search_documents' not found
```

**Cause**: Tool not exposed in MCP configuration

**Solution**:
```yaml
mcp:
  enabled: true
  tools:
    - name: search_documents  # Must match tool name
      pipeline: search_docs
      parameters:
        query:
          type: string
          required: true
```

```bash
# List available tools
sibyl-mcp --workspace config/workspaces/my_workspace.yaml list-tools
```

## Performance Issues

### Slow Query Performance

**Symptom**: Queries take >5 seconds

**Diagnosis**:
```bash
# Enable debug logging
export SIBYL_LOG_LEVEL=DEBUG

# Run query and check logs
sibyl pipeline run \
  --workspace config/workspaces/my_workspace.yaml \
  --pipeline search_docs \
  --param query="test"

# Check metrics
curl http://localhost:9090/metrics | grep duration
```

**Solutions**:

**1. Optimize retrieval**:
```yaml
steps:
  - use: rag.retrieval
    config:
      top_k: 5              # Reduce from 20
      similarity_threshold: 0.8  # Higher threshold
```

**2. Enable caching**:
```yaml
shops:
  infrastructure:
    config:
      caching:
        enabled: true
        backend: redis
        ttl: 3600
```

**3. Optimize vector index**:
```yaml
providers:
  vector_store:
    main:
      kind: pgvector
      index_type: hnsw      # Faster than ivfflat
```

**4. Use batch processing**:
```yaml
steps:
  - use: rag.embedding
    config:
      batch_size: 64        # Process in batches
```

### High Memory Usage

**Symptom**: Process uses >4GB RAM

**Diagnosis**:
```bash
# Check memory usage
ps aux | grep sibyl-mcp

# Check metrics
curl http://localhost:9090/metrics | grep memory
```

**Solutions**:

**1. Reduce cache size**:
```yaml
shops:
  infrastructure:
    config:
      caching:
        max_size: 1000      # Limit cache entries
```

**2. Reduce connection pool**:
```yaml
providers:
  vector_store:
    main:
      pool_size: 10         # Reduce from 50
      max_overflow: 5
```

**3. Limit concurrent requests**:
```yaml
mcp:
  max_concurrent_requests: 10
```

### Database Connection Errors

**Symptom**:
```
OperationalError: could not connect to server
```

**Cause**: Database unavailable or connection limit reached

**Solution**:
```bash
# Check database is running
pg_isready -h localhost -p 5432

# Check connection limit
psql -c "SHOW max_connections"

# Check active connections
psql -c "SELECT count(*) FROM pg_stat_activity"

# Reduce pool size
```yaml
providers:
  vector_store:
    main:
      pool_size: 20         # Reduce if hitting limit
```

## Document Indexing Issues

### No Documents Indexed

**Symptom**: Index completes but no documents found

**Cause**: Wrong path or glob pattern

**Solution**:
```bash
# Check path exists
ls -la ./docs

# Test glob pattern
find ./docs -name "*.md"

# Update provider
```yaml
providers:
  document_sources:
    local_docs:
      type: filesystem_markdown
      config:
        root: ./docs
        pattern: "**/*.md"      # Recursive
        recursive: true
```

### Chunking Produces Empty Chunks

**Symptom**: Documents indexed but chunks are empty

**Cause**: Incorrect chunk size or separators

**Solution**:
```yaml
steps:
  - use: rag.chunking
    config:
      subtechnique: recursive
      chunk_size: 512           # Reasonable size
      chunk_overlap: 50
      separators:
        - "\n\n"                # Try paragraphs first
        - "\n"
        - ". "
        - " "
```

### Embedding Fails

**Symptom**:
```
EmbeddingError: Failed to generate embeddings
```

**Cause**: Model not downloaded or incorrect configuration

**Solution**:
```bash
# For sentence-transformers, model auto-downloads
# Check if download is stuck
ls ~/.cache/torch/sentence_transformers/

# Or specify cache directory
```yaml
providers:
  embedding:
    local:
      kind: sentence-transformer
      model: all-MiniLM-L6-v2
      cache_dir: ./cache/models
```

## Cache Issues

### Redis Connection Failed

**Symptom**:
```
ConnectionError: Error connecting to Redis
```

**Cause**: Redis not running or wrong URL

**Solution**:
```bash
# Check Redis is running
redis-cli ping

# Start Redis
# macOS
brew services start redis

# Linux
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:7-alpine

# Update URL
export REDIS_URL=redis://localhost:6379/0
```

### Cache Not Working

**Symptom**: No cache hits, all misses

**Cause**: Cache key mismatch or TTL too short

**Solution**:
```yaml
shops:
  infrastructure:
    config:
      caching:
        enabled: true
        ttl: 3600               # 1 hour (increase if needed)
        cache_key_prefix: "sibyl:"
        backend: redis

# Check cache metrics
```

```bash
curl http://localhost:9090/metrics | grep cache_hits
```

## Budget and Cost Issues

### Budget Exceeded

**Symptom**:
```
BudgetError: Maximum cost exceeded ($100.00)
```

**Cause**: Hit configured budget limit

**Solution**:
```yaml
# Increase budget
budget:
  max_cost_usd: 200.0

# Or reset budget
sibyl budget reset

# Check current usage
sibyl budget status
```

### Unexpected High Costs

**Symptom**: LLM costs higher than expected

**Diagnosis**:
```bash
# Check cost metrics
curl http://localhost:9090/metrics | grep cost

# Check logs for expensive queries
grep "cost_usd" /var/log/sibyl/app.log | tail -20
```

**Solutions**:

**1. Use cheaper models**:
```yaml
providers:
  llm:
    primary:
      kind: openai
      model: gpt-3.5-turbo    # Cheaper than gpt-4
```

**2. Reduce max_tokens**:
```yaml
steps:
  - use: ai_generation.generation
    config:
      max_tokens: 1000        # Reduce from 2000
```

**3. Enable caching**:
```yaml
shops:
  infrastructure:
    config:
      caching:
        enabled: true
```

## Getting Help

### Collect Diagnostic Information

```bash
# System information
uname -a
python --version
sibyl --version

# Configuration
sibyl workspace validate config/workspaces/my_workspace.yaml

# Logs (last 100 lines)
tail -100 /var/log/sibyl/app.log > debug.log

# Metrics snapshot
curl http://localhost:9090/metrics > metrics.txt

# Health check
curl http://localhost:8001/health | jq '.' > health.json
```

### Enable Debug Logging

```bash
# Temporary
export SIBYL_LOG_LEVEL=DEBUG
sibyl pipeline run ...

# Permanent
```yaml
observability:
  logging:
    level: DEBUG
```

### Report an Issue

Include in your issue report:
1. Sibyl version: `sibyl --version`
2. Python version: `python --version`
3. OS: `uname -a`
4. Error message (full stack trace)
5. Minimal reproduction steps
6. Relevant configuration (redact secrets!)
7. Logs (last 50-100 lines)

**GitHub Issues**: https://github.com/yourusername/sibyl/issues

## Common Error Messages

| Error | Likely Cause | Quick Fix |
|-------|--------------|-----------|
| `ModuleNotFoundError` | Missing dependency | `pip install sibyl[vector]` |
| `ValidationError` | Invalid config | `sibyl workspace validate` |
| `ConnectionError` | Service down | Check service is running |
| `AuthenticationError` | Invalid API key | Check environment variable |
| `RateLimitError` | Too many requests | Add retry logic or wait |
| `TimeoutError` | Request too slow | Increase timeout |
| `OutOfMemoryError` | Memory exhausted | Reduce batch size or pool |
| `DatabaseError` | DB issue | Check connection and permissions |

## Further Reading

- **[Observability Guide](observability.md)** - Monitoring and logging
- **[Performance Tuning](performance-tuning.md)** - Optimization
- **[Deployment Guide](deployment.md)** - Production setup
- **[FAQ](../FAQ.md)** - Frequently asked questions

---

**Previous**: [Observability](observability.md) | **Next**: [Security Guide](security.md)

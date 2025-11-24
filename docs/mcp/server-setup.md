# MCP Server Setup

Complete guide to setting up and configuring Sibyl as an MCP server.

## Overview

Sibyl can act as a Model Context Protocol (MCP) server, exposing its AI capabilities as tools that Claude Desktop and other MCP clients can use. This guide covers all aspects of server setup, from basic configuration to production deployment.

## Installation

### Prerequisites

```bash
# Python 3.11+
python --version

# Sibyl with MCP support
pip install sibyl[mcp]

# Or install from source
git clone https://github.com/yourusername/sibyl.git
cd sibyl
pip install -e ".[mcp]"
```

### Verify Installation

```bash
# Check MCP server is available
sibyl-mcp --version

# List available commands
sibyl-mcp --help
```

## Basic Configuration

### Minimal MCP Workspace

Create `config/workspaces/mcp_server.yaml`:

```yaml
name: mcp_server

providers:
  llm:
    primary:
      kind: openai
      model: gpt-4
      api_key: "${OPENAI_API_KEY}"

  embedding:
    default:
      kind: sentence-transformer
      model: all-MiniLM-L6-v2

  vector_store:
    main:
      kind: duckdb
      dsn: "duckdb://./data/vectors.duckdb"

pipelines:
  search_docs:
    shop: rag
    steps:
      - use: rag.retrieval
        config:
          top_k: 5
      - use: ai_generation.generation
        config:
          provider: primary

# MCP Configuration
mcp:
  enabled: true
  transport: stdio              # For Claude Desktop

  tools:
    - name: search_documents
      description: "Search indexed documents and answer questions"
      pipeline: search_docs
      parameters:
        query:
          type: string
          description: "Your question"
          required: true
```

### Start MCP Server

```bash
# stdio mode (for Claude Desktop)
sibyl-mcp --workspace config/workspaces/mcp_server.yaml

# HTTP mode (for web integration)
sibyl-mcp \
  --workspace config/workspaces/mcp_server.yaml \
  --transport http \
  --port 8000
```

## Transport Configurations

### stdio Transport (Claude Desktop)

**Use case**: Desktop applications, command-line MCP clients

**Configuration**:
```yaml
mcp:
  transport: stdio

  # Optional stdio settings
  stdio:
    buffer_size: 8192
    encoding: utf-8
```

**Start server**:
```bash
sibyl-mcp --workspace config/workspaces/my_workspace.yaml
```

**Claude Desktop config** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "sibyl-docs": {
      "command": "/Users/username/sibyl/.venv/bin/sibyl-mcp",
      "args": [
        "--workspace",
        "/Users/username/sibyl/config/workspaces/docs.yaml"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Tips**:
- Use absolute paths for `command` and workspace file
- Set environment variables in `env` section
- Test server independently before adding to Claude Desktop
- Check logs: `~/.sibyl/logs/mcp_server.log`

### HTTP Transport (REST API)

**Use case**: Web applications, remote clients, microservices

**Configuration**:
```yaml
mcp:
  transport: http
  port: 8000
  host: "0.0.0.0"              # Listen on all interfaces

  # CORS for web clients
  cors:
    enabled: true
    origins:
      - "http://localhost:3000"
      - "https://myapp.com"
    methods: ["GET", "POST", "OPTIONS"]
    headers: ["Content-Type", "Authorization"]
    credentials: true

  # Request limits
  max_request_size: 10485760   # 10MB
  timeout: 300                 # 5 minutes

  # TLS/SSL
  tls:
    enabled: false
    cert_file: /path/to/cert.pem
    key_file: /path/to/key.pem
```

**Start server**:
```bash
sibyl-mcp \
  --workspace config/workspaces/my_workspace.yaml \
  --transport http \
  --port 8000 \
  --host 0.0.0.0
```

**Test server**:
```bash
# List tools
curl http://localhost:8000/mcp/tools

# Call tool
curl -X POST http://localhost:8000/mcp/tools/search_documents \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Sibyl?"}'
```

### SSE Transport (Server-Sent Events)

**Use case**: Real-time updates, streaming responses

**Configuration**:
```yaml
mcp:
  transport: sse
  port: 8000
  host: "0.0.0.0"

  sse:
    heartbeat_interval: 30     # Keep-alive interval (seconds)
    max_connections: 100
    event_buffer_size: 1000
```

**Client example**:
```javascript
const eventSource = new EventSource('http://localhost:8000/mcp/stream');

eventSource.addEventListener('tool_result', (event) => {
  const result = JSON.parse(event.data);
  console.log('Tool result:', result);
});
```

## Authentication and Security

### API Key Authentication

```yaml
mcp:
  transport: http
  authentication:
    type: api_key
    header: X-API-Key              # Header name
    keys:
      - "${API_KEY_1}"             # From environment
      - "${API_KEY_2}"

    # Optional: key metadata
    key_metadata:
      "${API_KEY_1}":
        name: "Production Key"
        permissions: ["*"]
      "${API_KEY_2}":
        name: "Read-Only Key"
        permissions: ["search_*"]
```

**Usage**:
```bash
curl -X POST http://localhost:8000/mcp/tools/search_documents \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

**Generate API keys**:
```python
import secrets

# Generate secure API key
api_key = secrets.token_urlsafe(32)
print(f"API_KEY={api_key}")
```

### JWT Authentication

```yaml
mcp:
  authentication:
    type: jwt
    secret: "${JWT_SECRET}"        # From environment
    algorithm: HS256
    expiration: 3600               # 1 hour

    # Optional claims validation
    required_claims:
      - sub                        # Subject (user ID)
      - exp                        # Expiration

    audience: "sibyl-mcp"
    issuer: "your-auth-service"
```

**Generate JWT**:
```python
import jwt
import datetime

payload = {
    'sub': 'user_123',
    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    'aud': 'sibyl-mcp',
    'iss': 'your-auth-service'
}

token = jwt.encode(payload, 'your-secret', algorithm='HS256')
```

**Usage**:
```bash
curl -X POST http://localhost:8000/mcp/tools/search_documents \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

### OAuth2 Authentication

```yaml
mcp:
  authentication:
    type: oauth2
    provider: google               # google, github, custom
    client_id: "${OAUTH_CLIENT_ID}"
    client_secret: "${OAUTH_CLIENT_SECRET}"
    redirect_uri: "http://localhost:8000/oauth/callback"
    scopes:
      - openid
      - email
```

### mTLS (Mutual TLS)

```yaml
mcp:
  transport: http
  tls:
    enabled: true
    cert_file: /path/to/server-cert.pem
    key_file: /path/to/server-key.pem

    # Client certificate validation
    client_auth: required
    ca_cert_file: /path/to/ca-cert.pem
```

## Rate Limiting

### Token Bucket

```yaml
mcp:
  rate_limiting:
    enabled: true
    algorithm: token_bucket

    # Rate limits
    requests_per_minute: 60
    burst: 10                      # Allow burst of 10

    # Tracking
    by_ip: true                    # Limit by IP address
    by_api_key: true               # Limit by API key

    # Storage
    storage: redis
    redis_url: "${REDIS_URL}"
```

### Sliding Window

```yaml
mcp:
  rate_limiting:
    algorithm: sliding_window
    requests_per_hour: 1000
    window_size: 3600              # 1 hour in seconds
```

### Cost-Based Limiting

```yaml
mcp:
  rate_limiting:
    algorithm: cost_based
    max_cost_per_hour: 10.0        # $10/hour per user
    track_by: user_id
```

**Response when rate limited**:
```json
{
  "error": "Rate limit exceeded",
  "limit": "60 requests per minute",
  "retry_after": 45,
  "reset_at": "2024-01-01T12:01:00Z"
}
```

## Observability

### Logging Configuration

```yaml
mcp:
  logging:
    level: INFO                    # DEBUG, INFO, WARNING, ERROR
    format: json                   # json, text

    # What to log
    log_requests: true
    log_responses: false           # Don't log responses (privacy)
    log_errors: true
    log_slow_requests: true
    slow_request_threshold: 5.0    # Log if >5 seconds

    # File output
    file:
      enabled: true
      path: /var/log/sibyl/mcp.log
      rotation:
        max_bytes: 10485760        # 10MB
        backup_count: 10

    # Structured logging
    extra_fields:
      service: sibyl-mcp
      environment: production
      version: "1.0.0"
```

**Log example**:
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "service": "sibyl-mcp",
  "environment": "production",
  "event": "tool_called",
  "tool": "search_documents",
  "user_id": "user_123",
  "duration_ms": 1234,
  "status": "success"
}
```

### Metrics Configuration

```yaml
mcp:
  metrics:
    enabled: true
    port: 9090                     # Prometheus metrics port
    path: /metrics

    # Metric collection
    collect_tool_metrics: true
    collect_request_metrics: true
    collect_error_metrics: true

    # Custom labels
    labels:
      service: sibyl-mcp
      environment: production
      region: us-west-2
```

**Available metrics**:
```
# Tool metrics
sibyl_mcp_tool_calls_total{tool="search_documents",status="success"} 1234
sibyl_mcp_tool_duration_seconds{tool="search_documents"} 1.23
sibyl_mcp_tool_errors_total{tool="search_documents",error_type="timeout"} 5

# Request metrics
sibyl_mcp_requests_total{method="POST",status="200"} 5678
sibyl_mcp_request_duration_seconds{method="POST"} 0.5

# System metrics
sibyl_mcp_active_connections 42
sibyl_mcp_cache_hit_rate 0.85
sibyl_mcp_rate_limit_rejections_total 10
```

**Prometheus scrape config**:
```yaml
scrape_configs:
  - job_name: 'sibyl-mcp'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 15s
```

### Tracing Configuration

```yaml
mcp:
  tracing:
    enabled: true
    exporter: jaeger               # jaeger, zipkin, otlp

    # Jaeger configuration
    jaeger:
      endpoint: "http://jaeger:14268/api/traces"
      service_name: sibyl-mcp

    # Sampling
    sampling:
      type: probabilistic          # always, never, probabilistic
      rate: 0.1                    # Sample 10% of requests

    # Trace all tools
    trace_tools: true
    trace_pipelines: true
```

### Health Checks

```yaml
mcp:
  health:
    enabled: true
    port: 8001                     # Separate health check port
    path: /health

    # Health check endpoints
    endpoints:
      liveness: /health/live       # Is server running?
      readiness: /health/ready     # Is server ready for traffic?

    # Checks to perform
    checks:
      - name: database
        type: database
        connection: "${DATABASE_URL}"
        timeout: 5

      - name: vector_store
        type: vector_store
        provider: main
        timeout: 5

      - name: llm_provider
        type: llm
        provider: primary
        timeout: 10
```

**Health check response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 5
    },
    "vector_store": {
      "status": "healthy",
      "latency_ms": 12
    },
    "llm_provider": {
      "status": "healthy",
      "latency_ms": 45
    }
  }
}
```

**Kubernetes liveness/readiness probes**:
```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8001
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8001
  initialDelaySeconds: 10
  periodSeconds: 5
```

## Advanced Configuration

### Multiple Workspaces

Run multiple MCP servers for different domains:

```bash
# Documentation server
sibyl-mcp \
  --workspace config/workspaces/docs.yaml \
  --port 8000

# Code analysis server
sibyl-mcp \
  --workspace config/workspaces/code.yaml \
  --port 8001

# Customer support server
sibyl-mcp \
  --workspace config/workspaces/support.yaml \
  --port 8002
```

**Claude Desktop config**:
```json
{
  "mcpServers": {
    "docs": {
      "command": "sibyl-mcp",
      "args": ["--workspace", "config/workspaces/docs.yaml"]
    },
    "code": {
      "command": "sibyl-mcp",
      "args": ["--workspace", "config/workspaces/code.yaml"]
    },
    "support": {
      "command": "sibyl-mcp",
      "args": ["--workspace", "config/workspaces/support.yaml"]
    }
  }
}
```

### Dynamic Tool Loading

```yaml
mcp:
  tools:
    # Load tools from directory
    auto_discover: true
    tools_directory: ./custom_tools

    # Or list explicitly
    - name: tool1
      pipeline: pipeline1
    - name: tool2
      pipeline: pipeline2
```

### Tool Versioning

```yaml
mcp:
  tools:
    - name: search_documents
      version: v1
      pipeline: search_v1
      deprecated: false

    - name: search_documents
      version: v2
      pipeline: search_v2
      default: true               # Use this version by default

    # Support both versions
    version_in_path: true         # /v1/tools/search, /v2/tools/search
```

### Request/Response Transformation

```yaml
mcp:
  transformations:
    # Transform incoming requests
    request:
      - name: normalize_query
        type: python
        code: |
          def transform(request):
              request['query'] = request['query'].lower().strip()
              return request

    # Transform outgoing responses
    response:
      - name: add_metadata
        type: python
        code: |
          def transform(response):
              response['metadata'] = {
                  'timestamp': datetime.utcnow().isoformat(),
                  'version': '1.0.0'
              }
              return response
```

## Production Deployment

### systemd Service

Create `/etc/systemd/system/sibyl-mcp.service`:

```ini
[Unit]
Description=Sibyl MCP Server
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=sibyl
Group=sibyl
WorkingDirectory=/home/sibyl/sibyl
Environment="PATH=/home/sibyl/sibyl/.venv/bin"
EnvironmentFile=/home/sibyl/sibyl/.env

ExecStart=/home/sibyl/sibyl/.venv/bin/sibyl-mcp \
  --workspace /home/sibyl/sibyl/config/workspaces/prod.yaml \
  --transport http \
  --port 8000

Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/sibyl/sibyl/data /home/sibyl/sibyl/logs

[Install]
WantedBy=multi-user.target
```

**Enable and start**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sibyl-mcp
sudo systemctl start sibyl-mcp
sudo systemctl status sibyl-mcp
```

### Docker Deployment

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .
RUN pip install -e ".[mcp]"

# Expose ports
EXPOSE 8000 9090 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# Run server
CMD ["sibyl-mcp", \
     "--workspace", "config/workspaces/prod.yaml", \
     "--transport", "http", \
     "--port", "8000"]
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  sibyl-mcp:
    build: .
    ports:
      - "8000:8000"      # MCP server
      - "9090:9090"      # Metrics
      - "8001:8001"      # Health checks
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql://sibyl:${DB_PASSWORD}@postgres:5432/sibyl
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: sibyl
      POSTGRES_USER: sibyl
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  postgres-data:
  redis-data:
```

### Kubernetes Deployment

See [Deployment Guide](../operations/deployment.md#kubernetes-deployment) for complete Kubernetes configuration.

## Troubleshooting

### Server Won't Start

**Check workspace validity**:
```bash
sibyl workspace validate config/workspaces/my_workspace.yaml
```

**Check MCP configuration**:
```bash
sibyl-mcp --workspace config/workspaces/my_workspace.yaml --validate
```

**Debug mode**:
```bash
export SIBYL_LOG_LEVEL=DEBUG
sibyl-mcp --workspace config/workspaces/my_workspace.yaml
```

### Claude Desktop Can't Connect

**Check paths**:
```bash
# Verify paths are absolute
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Test server independently
sibyl-mcp --workspace /absolute/path/to/workspace.yaml
```

**Check logs**:
```bash
tail -f ~/.sibyl/logs/mcp_server.log
```

**Common issues**:
1. ❌ Relative paths → Use absolute paths
2. ❌ Wrong Python environment → Use full path to `sibyl-mcp`
3. ❌ Missing environment variables → Set in `env` section
4. ❌ Wrong transport → Use `stdio` for Claude Desktop

### Tools Not Appearing

**List available tools**:
```bash
sibyl-mcp --workspace config/workspaces/my_workspace.yaml list-tools
```

**Validate tool configuration**:
```bash
sibyl workspace validate --check mcp config/workspaces/my_workspace.yaml
```

### Performance Issues

**Enable caching**:
```yaml
shops:
  infrastructure:
    config:
      caching:
        enabled: true
        backend: redis
```

**Increase workers** (HTTP mode):
```bash
sibyl-mcp \
  --workspace config/workspaces/my_workspace.yaml \
  --transport http \
  --workers 4
```

**Optimize connection pooling**:
```yaml
providers:
  vector_store:
    main:
      pool_size: 50
      max_overflow: 10
```

## Further Reading

- **[MCP Overview](overview.md)** - MCP integration overview
- **[Client Integration](client-integration.md)** - Integrate with MCP clients
- **[Tool Exposure](tool-exposure.md)** - Configure MCP tools
- **[REST API](rest-api.md)** - HTTP API reference

---

**Previous**: [MCP Overview](overview.md) | **Next**: [Client Integration](client-integration.md)

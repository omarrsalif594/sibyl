# Multi-Workspace Deployment Guide (TRACK-X3)

This guide explains how to run multiple Sibyl workspaces in parallel using Docker Compose.

## Overview

The multi-workspace setup allows you to run multiple independent Sibyl configurations (products/tenants) in separate containers. Each workspace:
- Runs in its own container with isolated resources
- Has its own configuration file, providers, and runtime
- Listens on distinct ports (no conflicts)
- Can be independently scaled and monitored

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │  MCP Local       │              │  MCP Production  │         │
│  │  (Port 8771)     │              │  (Port 8772)     │         │
│  │  example_local   │              │  prod_web_res.   │         │
│  └──────────────────┘              └──────────────────┘         │
│                                                                   │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │  HTTP Local      │              │  HTTP Production │         │
│  │  (Port 8000)     │              │  (Port 8001)     │         │
│  │  example_local   │              │  prod_web_res.   │         │
│  └──────────────────┘              └──────────────────┘         │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Shared Volumes                                          │  │
│  │  - mcp_state (DuckDB, separate files per workspace)     │  │
│  │  - mcp_logs (logs directory)                            │  │
│  │  - workspace configs (read-only mount)                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Basic Multi-Workspace Setup

```bash
# Copy and customize environment
cp .env.example .env

# Start all multi-workspace services (MCP + HTTP for local & prod)
docker-compose --profile multi-workspace up -d

# Verify services are running
docker-compose ps
```

### 2. Start Only MCP Servers

```bash
# Start only MCP servers (no HTTP)
docker-compose --profile multi-mcp up -d
```

### 3. Start Only HTTP Servers

```bash
# Start only HTTP servers (no MCP)
docker-compose --profile multi-http up -d
```

## Environment Configuration

### Use Pre-configured .env Files

```bash
# For local development only
docker-compose --env-file .env.local-workspace --profile multi-workspace up

# For production workspaces
docker-compose --env-file .env.prod-workspace --profile multi-workspace up

# For full multi-workspace with observability
docker-compose --env-file .env.multi-workspace-full \
  --profile multi-workspace \
  --profile observability up -d
```

### Key Environment Variables

```bash
# Workspace configuration files
SIBYL_WORKSPACE_LOCAL=config/workspaces/example_local.yaml
SIBYL_WORKSPACE_PROD=config/workspaces/prod_web_research.yaml

# Port mappings
MCP_LOCAL_WORKSPACE_PORT=8771      # MCP local instance
MCP_PROD_WORKSPACE_PORT=8772       # MCP production instance
HTTP_LOCAL_WORKSPACE_PORT=8000     # HTTP local instance
HTTP_PROD_WORKSPACE_PORT=8001      # HTTP production instance

# Logging
MCP_LOG_LEVEL=INFO
MCP_JSON_LOGS=true

# Resources
DUCKDB_MEMORY_LIMIT=2GB
```

## Port Reference

| Service | Workspace | Protocol | Port | Health Check |
|---------|-----------|----------|------|--------------|
| MCP Local | Local Dev | stdio | 8771 | `curl http://localhost:8771/api/health` |
| MCP Prod | Production | stdio | 8772 | `curl http://localhost:8772/api/health` |
| HTTP Local | Local Dev | HTTP | 8000 | `curl http://localhost:8000/api/health` |
| HTTP Prod | Production | HTTP | 8001 | `curl http://localhost:8001/api/health` |

## Usage Examples

### Monitor a Specific Service

```bash
# View logs for local MCP server
docker-compose logs -f mcp-local-workspace

# View logs for production HTTP server
docker-compose logs -f http-prod-workspace

# View all logs with timestamps
docker-compose logs --timestamps
```

### Health Checks

```bash
# Check all services are healthy
curl http://localhost:8771/api/health  # MCP Local
curl http://localhost:8772/api/health  # MCP Prod
curl http://localhost:8000/api/health  # HTTP Local
curl http://localhost:8001/api/health  # HTTP Prod

# All should return 200 OK with health status
```

### Execute Commands in Container

```bash
# Validate workspace in running container
docker-compose exec mcp-local-workspace \
  python -c "from sibyl.workspace import load_workspace; \
  print(load_workspace('config/workspaces/example_local.yaml').name)"

# View workspace info
docker-compose exec http-prod-workspace \
  sibyl workspace validate --file config/workspaces/prod_web_research.yaml
```

### Restart Specific Service

```bash
# Restart only the production MCP server (without affecting local)
docker-compose restart mcp-prod-workspace

# Restart all HTTP servers
docker-compose restart http-local-workspace http-prod-workspace
```

## Workspace Isolation

Each workspace is completely isolated:

### Storage Isolation
- Local: `/var/lib/mcp/state/local_state.duckdb`
- Prod: `/var/lib/mcp/state/prod_state.duckdb`

### Configuration Isolation
- Local: Uses `config/workspaces/example_local.yaml`
- Prod: Uses `config/workspaces/prod_web_research.yaml`

### Provider Isolation
Each workspace has its own provider instances:

**Local Workspace:**
- LLM: Ollama (local)
- Embeddings: Sentence Transformers (local)
- Vector Store: DuckDB (local_state.duckdb)

**Production Workspace:**
- LLM: OpenAI (cloud)
- Embeddings: OpenAI Embeddings (cloud)
- Vector Store: DuckDB (prod_state.duckdb)

## Adding More Workspaces

### Step 1: Create Workspace YAML

```bash
# Copy existing workspace as template
cp config/workspaces/prod_web_research.yaml config/workspaces/my_workspace.yaml

# Edit as needed
vim config/workspaces/my_workspace.yaml
```

### Step 2: Add to docker-compose.yml

```yaml
# Copy an existing service (e.g., mcp-prod-workspace)
mcp-my-workspace:
  build: ...
  image: sibyl-mcp-server:${VERSION:-latest}
  container_name: mcp-my-workspace
  hostname: mcp-my-workspace

  profiles:
    - multi-workspace
    - multi-mcp

  environment:
    SIBYL_WORKSPACE_FILE: ${SIBYL_WORKSPACE_MY:-config/workspaces/my_workspace.yaml}
    MCP_DUCKDB_PATH: /var/lib/mcp/state/my_state.duckdb
    # ... other config

  ports:
    - "${MCP_MY_WORKSPACE_PORT:-8773}:8770"

  # ... rest of config
```

### Step 3: Add Environment Variables

```bash
# Add to .env file
SIBYL_WORKSPACE_MY=config/workspaces/my_workspace.yaml
MCP_MY_WORKSPACE_PORT=8773
HTTP_MY_WORKSPACE_PORT=8002
```

### Step 4: Start the New Workspace

```bash
docker-compose --profile multi-workspace up -d mcp-my-workspace
```

## Observability

### Enable Metrics and Logging

```bash
# Start with observability stack
docker-compose --profile multi-workspace --profile observability up -d

# Services included:
# - Prometheus: http://localhost:9090 (metrics)
# - Grafana: http://localhost:3000 (visualization)
# - Loki: http://localhost:3100 (log aggregation)
# - Fluent Bit: (log forwarder)
```

### View Metrics

```bash
# Access Grafana
open http://localhost:3000
# Username: admin
# Password: from GRAFANA_PASSWORD in .env

# Access Prometheus
open http://localhost:9090
```

### View Logs

```bash
# Docker Compose logs
docker-compose logs -f

# Loki logs (if observability enabled)
curl http://localhost:3100/loki/api/v1/query_range \
  -G -d 'query={job="mcp"}' -d 'start=1h' -d 'end=now'
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs for errors
docker-compose logs

# Check specific service
docker-compose logs mcp-local-workspace

# Verify ports are not in use
lsof -i :8771
lsof -i :8772
lsof -i :8000
lsof -i :8001
```

### Workspace Not Loading

```bash
# Validate workspace configuration
docker-compose exec mcp-local-workspace \
  sibyl workspace validate --file config/workspaces/example_local.yaml

# Check workspace path is mounted correctly
docker-compose exec mcp-local-workspace \
  ls -la /workspace/config/workspaces/
```

### Health Check Failing

```bash
# Check container is actually running
docker-compose ps

# Check logs
docker-compose logs mcp-local-workspace

# Try manual health check
docker-compose exec mcp-local-workspace \
  curl -f http://localhost:8770/api/health
```

### High Memory Usage

```bash
# Reduce DUCKDB_MEMORY_LIMIT in .env
DUCKDB_MEMORY_LIMIT=1GB

# Restart services
docker-compose restart

# Check memory usage
docker stats mcp-local-workspace mcp-prod-workspace
```

## Performance Tuning

### Resource Allocation per Service

Edit `docker-compose.yml` `deploy.resources`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Max 2 CPU cores
      memory: 4G       # Max 4GB RAM
    reservations:
      cpus: '0.5'      # Reserve 0.5 CPU
      memory: 1G       # Reserve 1GB RAM
```

### Scaling Horizontally

For production, use Kubernetes instead:

```bash
# Create separate deployments per workspace
kubectl apply -f k8s/sibyl-local.yaml
kubectl apply -f k8s/sibyl-prod.yaml

# Scale individual workspaces
kubectl scale deployment sibyl-local --replicas=3
kubectl scale deployment sibyl-prod --replicas=5
```

## Production Deployment

### Enable Production Profile

```bash
# With observability
docker-compose --profile prod --profile observability up -d

# With TLS/HTTPS
docker-compose --profile prod --profile tls --profile observability up -d

# With tracing
docker-compose --profile prod --profile observability --profile tracing up -d
```

### Production Checklist

- [ ] Use `.env.prod-workspace` configuration
- [ ] Set API keys in environment variables (OPENAI_API_KEY, etc)
- [ ] Enable observability stack for monitoring
- [ ] Configure backup service (cron-based)
- [ ] Set read-only filesystem where possible
- [ ] Configure resource limits appropriately
- [ ] Enable TLS/HTTPS with Nginx
- [ ] Use external log aggregation (Loki)
- [ ] Monitor metrics in Grafana
- [ ] Set up alerts for failed health checks

### Backup Configuration

Backup runs daily at 2 AM:

```bash
# View backup logs
docker-compose logs backup

# Manual backup
docker-compose exec backup /bin/bash /backup_state.sh

# Restore from backup (manual process)
docker-compose exec backup \
  sqlite3 /backups/latest/sibyl_state.duckdb ".dump" | \
  docker-compose exec -T mcp-prod-workspace \
  sqlite3 /var/lib/mcp/state/prod_state.duckdb
```

## Advanced: Kubernetes Deployment

For production multi-workspace deployments, see Kubernetes manifests in the architecture documentation:

```bash
# Apply workspace configurations as ConfigMap
kubectl create configmap sibyl-workspaces \
  --from-file=config/workspaces/

# Deploy workspaces
kubectl apply -f k8s/sibyl-local-deployment.yaml
kubectl apply -f k8s/sibyl-prod-deployment.yaml

# Scale as needed
kubectl scale deployment sibyl-prod --replicas=3
```

## References

- Main documentation: `docs/architecture/multi_workspace.md`
- Workspace schema: `sibyl/workspace/schema.py`
- MCP server: `sibyl/server/mcp_server.py`
- HTTP server: `sibyl/server/http_server.py`
- Docker compose: `docker-compose.yml`

## Support

For issues or questions:

1. Check logs: `docker-compose logs -f`
2. Validate configuration: `sibyl workspace validate --file <path>`
3. Verify health: `curl http://localhost:<port>/api/health`
4. See troubleshooting section above

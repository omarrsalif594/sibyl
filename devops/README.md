# Sibyl MCP Server - DevOps Infrastructure

Production-ready Docker and DevOps infrastructure for the Sibyl MCP Server platform.

## Quick Start

### Development

```bash
# 1. Configure environment
cd devops/docker
cp .env.example .env.dev
# Edit .env.dev and add your API keys

# 2. Start development environment
cd ../scripts
./start-dev.sh

# 3. Access Sibyl
# - MCP HTTP: http://localhost:8770
# - REST API: http://localhost:8000
# - Metrics: http://localhost:9090
```

### Production

```bash
# 1. Configure environment
cd devops/docker
cp .env.example .env.prod
# Edit .env.prod for production settings

# 2. Configure API keys (IMPORTANT!)
cp .secrets/api_keys.txt.template .secrets/api_keys.txt
# Edit .secrets/api_keys.txt with real API keys

# 3. Start production environment
cd ../scripts
./start-prod.sh

# 4. Access Sibyl (via Nginx)
# - HTTP: http://localhost
# - HTTPS: https://localhost (after SSL setup)
# - Grafana: http://localhost:3000
```

## Directory Structure

```
devops/
├── README.md                    # This file
├── DEPLOYMENT.md                # Detailed deployment guide
├── OBSERVABILITY.md             # Observability stack documentation
├── TROUBLESHOOTING.md           # Common issues and solutions
│
├── docker/                      # Docker configuration
│   ├── Dockerfile               # Multi-stage production Dockerfile
│   ├── docker-compose.yml       # Comprehensive compose configuration
│   ├── .env.example             # Environment template
│   ├── .env.dev                 # Development environment
│   ├── .env.prod                # Production environment
│   └── .secrets/                # API keys (not in git)
│       └── api_keys.txt.template
│
├── config/                      # Service configurations
│   ├── nginx.conf               # Nginx reverse proxy config
│   ├── nginx/                   # Nginx additional configs
│   │   └── conf.d/
│   │       └── sibyl-http.conf  # HTTP routing configuration
│   ├── ssl/                     # SSL certificates (not in git)
│   │   └── README.md
│   └── prometheus.yml           # Prometheus metrics config
│
├── observability/               # Observability stack configurations
│   ├── prometheus/
│   │   ├── prometheus.yml       # Prometheus config
│   │   └── alerts.yml           # Alert rules
│   ├── grafana/
│   │   ├── provisioning/        # Grafana auto-provisioning
│   │   └── dashboards/          # Pre-built dashboards
│   ├── loki/
│   │   └── loki-config.yaml     # Loki log aggregation config
│   └── fluent-bit/
│       └── fluent-bit.conf      # Log forwarding config
│
└── scripts/                     # Operational scripts
    ├── start-dev.sh             # Start development environment
    ├── start-prod.sh            # Start production environment
    ├── health-check.sh          # Health check script
    ├── logs.sh                  # View logs
    ├── backup-state.sh          # Backup DuckDB state
    ├── restore-state.sh         # Restore from backup
    ├── cleanup.sh               # Cleanup Docker resources
    ├── update.sh                # Update Docker images
    └── rotate-logs.sh           # Rotate application logs
```

## Features

### 🐳 Docker Infrastructure
- **Multi-stage builds** - Optimized for size and security
- **Development & Production modes** - Separate targets with appropriate tooling
- **Health checks** - Automatic health monitoring for all services
- **Security hardening** - Non-root user, read-only filesystem support, minimal attack surface

### 🔄 Docker Compose Profiles
- `dev` - Development mode with hot-reload and debugging tools
- `prod` - Production mode with Nginx reverse proxy
- `observability` - Full observability stack (Prometheus, Grafana, Loki, Fluent Bit)
- `tracing` - Distributed tracing with Jaeger

### 📊 Observability Stack
- **Prometheus** - Metrics collection and storage
- **Grafana** - Metrics visualization and dashboards
- **Loki** - Log aggregation and querying
- **Fluent Bit** - Log forwarding from containers
- **Jaeger** - Distributed tracing (optional)

### 🔐 Security Features
- Non-root container execution
- Secret management via Docker secrets
- TLS/SSL support with Let's Encrypt ready
- Security headers (HSTS, CSP, X-Frame-Options)
- Rate limiting and DDoS protection

### 🛠️ Operational Tools
- One-command start scripts for dev/prod
- Automated backup and restore for DuckDB state
- Health check monitoring
- Log aggregation and rotation
- Resource cleanup utilities

## Architecture

### Development Mode
```
┌─────────────┐
│   Client    │
│ (Browser/   │
│   MCP CLI)  │
└─────┬───────┘
      │
      │ Direct Access
      │
┌─────▼────────────────────┐
│   Sibyl Development      │
│   - Hot reload           │
│   - Debug logging        │
│   - Direct port access   │
│   Ports: 8770, 8000      │
└──────────────────────────┘
```

### Production Mode
```
┌─────────────┐
│   Client    │
│ (Browser/   │
│   MCP CLI)  │
└─────┬───────┘
      │
      │ HTTPS/HTTP
      │
┌─────▼─────────────────┐
│   Nginx Reverse Proxy │
│   - TLS termination   │
│   - Rate limiting     │
│   - Load balancing    │
│   Port: 80, 443       │
└─────┬─────────────────┘
      │
┌─────▼────────────┬──────────────┬──────────────┐
│  Sibyl Prod      │  Prometheus  │   Grafana    │
│  - MCP HTTP      │  - Metrics   │  - Dashboards│
│  - REST API      │              │              │
│  - Metrics       │              │              │
└──────────────────┴──────────────┴──────────────┘
      │
┌─────▼──────────┐
│  Loki + Fluent │
│  - Logs        │
└────────────────┘
```

## Common Commands

### Start Services
```bash
# Development
./scripts/start-dev.sh
./scripts/start-dev.sh --observability  # With observability stack

# Production
./scripts/start-prod.sh
./scripts/start-prod.sh --tracing       # With distributed tracing
```

### View Logs
```bash
# View logs from all services
./scripts/logs.sh -f

# View logs from specific service
./scripts/logs.sh -f sibyl-dev
./scripts/logs.sh -f nginx

# View last 500 lines
./scripts/logs.sh -n 500
```

### Health Checks
```bash
# Check health of running services
./scripts/health-check.sh

# Or manually
curl http://localhost:8770/health      # MCP HTTP (dev)
curl http://localhost:8000/health      # REST API (dev)
curl http://localhost/health           # Nginx (prod)
```

### Backup & Restore
```bash
# Backup DuckDB state
./scripts/backup-state.sh

# Restore from backup
./scripts/restore-state.sh

# List backups
ls -lh ../docker/.backups/
```

### Maintenance
```bash
# Update Docker images
./scripts/update.sh
./scripts/update.sh --prod --no-cache  # Production, no cache

# Cleanup Docker resources
./scripts/cleanup.sh
./scripts/cleanup.sh --deep            # Deep clean (removes volumes)

# Rotate logs
./scripts/rotate-logs.sh
```

### Stop Services
```bash
# Stop development
cd devops/docker
docker compose --profile dev down

# Stop production
docker compose --profile prod --profile observability down

# Stop and remove volumes (WARNING: deletes data)
docker compose down -v
```

## Environment Variables

Key environment variables (see `.env.example` for full list):

### Server Configuration
- `SIBYL_SERVER_MODE` - Server mode: `stdio`, `http`, or `rest`
- `SIBYL_LOG_LEVEL` - Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- `MCP_HTTP_PORT` - MCP HTTP server port (default: 8770)
- `SIBYL_PORT` - REST API port (default: 8000)

### API Keys
- `OPENAI_API_KEY` - OpenAI API key (required for most workspaces)
- `ANTHROPIC_API_KEY` - Anthropic API key (optional)
- `SECRETS_FILE` - Path to secrets file (recommended: `./.secrets/api_keys.txt`)

### Resource Limits
- `SIBYL_CPU_LIMIT` - CPU limit (default: 2.0 for dev, 4.0 for prod)
- `SIBYL_MEMORY_LIMIT` - Memory limit (default: 4G for dev, 8G for prod)
- `DUCKDB_MEMORY_LIMIT` - DuckDB memory limit (default: 2GB)

## Next Steps

1. **First Time Setup**: Read [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions
2. **Monitoring**: See [OBSERVABILITY.md](./OBSERVABILITY.md) to set up monitoring and alerting
3. **Troubleshooting**: Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues

## Support

- GitHub Issues: https://github.com/sibyl/sibyl/issues
- Documentation: https://docs.sibyl.dev
- Community: https://discord.gg/sibyl

## License

Apache License 2.0 - See LICENSE file for details

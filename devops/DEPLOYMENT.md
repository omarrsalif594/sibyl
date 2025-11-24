# Sibyl Deployment Guide

Comprehensive guide for deploying Sibyl MCP Server in development and production environments.

## Prerequisites

- Docker Engine 20.10+ and Docker Compose V2
- 4GB+ RAM for development, 8GB+ for production
- 10GB+ disk space
- (Production) Domain name and SSL certificates

## Development Deployment

### 1. Initial Setup

```bash
# Clone repository
git clone <repository-url>
cd sibyl

# Navigate to Docker directory
cd devops/docker

# Create development environment file
cp .env.example .env.dev
```

### 2. Configure Environment

Edit `.env.dev`:

```bash
# Server Configuration
SIBYL_SERVER_MODE=http
SIBYL_LOG_LEVEL=DEBUG

# API Keys (required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Workspace
SIBYL_WORKSPACE_FILE=/app/config/workspaces/example_local.yaml
```

### 3. Start Development Environment

```bash
cd ../scripts
./start-dev.sh

# Or with observability
./start-dev.sh --observability
```

### 4. Verify Deployment

```bash
# Check health
./health-check.sh

# View logs
./logs.sh -f sibyl-dev

# Test MCP endpoint
curl http://localhost:8770/health

# Test REST API
curl http://localhost:8000/health
```

## Production Deployment

### 1. Server Preparation

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get install docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

### 2. Configure Production Environment

```bash
cd devops/docker

# Create production environment
cp .env.example .env.prod
nano .env.prod
```

Critical production settings:

```bash
# Build
BUILD_TARGET=runtime
VERSION=0.1.0

# Server
SIBYL_SERVER_MODE=http
SIBYL_LOG_LEVEL=INFO

# Security
GRAFANA_PASSWORD=STRONG_PASSWORD_HERE  # Change from default!

# Resources
SIBYL_CPU_LIMIT=4.0
SIBYL_MEMORY_LIMIT=8G
DUCKDB_MEMORY_LIMIT=4GB

# Environment
ENVIRONMENT=production
```

### 3. Configure Secrets

```bash
# Create secrets file
cp .secrets/api_keys.txt.template .secrets/api_keys.txt
chmod 600 .secrets/api_keys.txt
nano .secrets/api_keys.txt
```

Add your API keys:
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. SSL/TLS Setup (Recommended)

```bash
# Using Let's Encrypt
cd ../config/ssl

# Option 1: Certbot (easiest)
sudo certbot certonly --standalone -d sibyl.example.com
sudo cp /etc/letsencrypt/live/sibyl.example.com/fullchain.pem ./cert.pem
sudo cp /etc/letsencrypt/live/sibyl.example.com/privkey.pem ./key.pem
chmod 644 cert.pem
chmod 600 key.pem

# Option 2: Self-signed (development only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem -out cert.pem

# Update nginx.conf to enable HTTPS
nano ../nginx.conf
# Uncomment the HTTPS server block
```

### 5. Deploy Production Stack

```bash
cd ../../scripts

# Build and start production services
./start-prod.sh

# Verify deployment
./health-check.sh

# Check logs
./logs.sh -f sibyl-prod
```

### 6. Configure Firewall

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Optional: Allow direct access to observability
sudo ufw allow 3000/tcp  # Grafana
sudo ufw allow 9090/tcp  # Prometheus

# Enable firewall
sudo ufw enable
```

## Post-Deployment

### 1. Verify Services

```bash
# Check all services are healthy
docker compose ps

# Test endpoints
curl http://your-domain.com/health
curl http://your-domain.com/api/health
curl http://your-domain.com/mcp/health
```

### 2. Configure Monitoring

Access Grafana: `http://your-domain.com:3000`

- Default credentials: admin/admin (change immediately!)
- Dashboards are pre-configured
- Set up alerting (see OBSERVABILITY.md)

### 3. Set Up Backups

```bash
# Manual backup
./backup-state.sh

# Add to crontab for automated backups
crontab -e

# Add this line for daily backups at 2 AM
0 2 * * * /path/to/sibyl/devops/scripts/backup-state.sh
```

### 4. Enable Log Rotation

```bash
# Add to crontab
crontab -e

# Rotate logs weekly
0 0 * * 0 /path/to/sibyl/devops/scripts/rotate-logs.sh
```

## Scaling Considerations

### Horizontal Scaling

To scale Sibyl horizontally:

1. Set up load balancer (e.g., HAProxy, AWS ALB)
2. Deploy multiple instances
3. Use shared volume for DuckDB or migrate to external database
4. Configure session affinity if needed

### Vertical Scaling

Adjust resource limits in `.env.prod`:

```bash
# For higher loads
SIBYL_CPU_LIMIT=8.0
SIBYL_MEMORY_LIMIT=16G
DUCKDB_MEMORY_LIMIT=8GB
```

## Updating Production

```bash
cd devops/scripts

# Pull latest code
git pull

# Update images and restart
./update.sh --prod

# Or with no cache for complete rebuild
./update.sh --prod --no-cache
```

## Rollback

```bash
# Stop current version
cd devops/docker
docker compose --profile prod down

# Restore previous state
cd ../scripts
./restore-state.sh

# Checkout previous version
git checkout <previous-commit>

# Rebuild and restart
./update.sh --prod --no-cache
./start-prod.sh
```

## Security Checklist

- [ ] Changed default Grafana password
- [ ] Configured SSL/TLS certificates
- [ ] Stored API keys in secrets file (not environment variables)
- [ ] Configured firewall rules
- [ ] Enabled HSTS in nginx
- [ ] Set up automated backups
- [ ] Configured log rotation
- [ ] Reviewed nginx security headers
- [ ] Implemented rate limiting
- [ ] Restricted Prometheus metrics endpoint (if needed)

## Maintenance Schedule

| Task | Frequency | Command |
|------|-----------|---------|
| Security updates | Weekly | `sudo apt-get update && sudo apt-get upgrade` |
| Docker image updates | Monthly | `./update.sh --prod` |
| Log rotation | Weekly | `./rotate-logs.sh` |
| Backup verification | Monthly | `./restore-state.sh` (test) |
| SSL certificate renewal | Every 60 days | `certbot renew` |
| Cleanup Docker resources | Monthly | `./cleanup.sh` |

## Next Steps

- Set up monitoring alerts: [OBSERVABILITY.md](./OBSERVABILITY.md)
- Review troubleshooting guide: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- Configure workspace-specific settings: `config/workspaces/`

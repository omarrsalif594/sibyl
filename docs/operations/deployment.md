# Deployment Guide

Complete guide for deploying Sibyl to production environments.

## Overview

Sibyl can be deployed in multiple configurations:

- **Single Server** - All components on one machine
- **Distributed** - Separate API servers, vector stores, and databases
- **Containerized** - Docker/Docker Compose deployment
- **Cloud** - AWS, GCP, Azure deployments
- **Kubernetes** - Orchestrated container deployment

## Prerequisites

### System Requirements

**Minimum (Development)**:
- CPU: 2 cores
- RAM: 4GB
- Storage: 10GB SSD
- OS: Linux, macOS, or Windows (WSL)

**Recommended (Production)**:
- CPU: 8+ cores
- RAM: 16GB+ (32GB for large-scale)
- Storage: 100GB+ SSD (NVMe preferred)
- OS: Ubuntu 22.04 LTS or similar

### Software Requirements

- Python 3.11+
- Docker 20.10+ (for containerized deployment)
- PostgreSQL 15+ with pgvector (for production vector store)
- Redis (optional, for caching)
- Nginx (for reverse proxy)

## Deployment Methods

### Method 1: Single Server Deployment

Simplest deployment for small to medium workloads.

#### 1. Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv git nginx postgresql-15

# Create user
sudo useradd -m -s /bin/bash sibyl
sudo su - sibyl
```

#### 2. Install Sibyl

```bash
# Clone repository
git clone https://github.com/yourusername/sibyl.git
cd sibyl

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install Sibyl
pip install -e ".[vector,monitoring,rest]"
```

#### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

```bash
# .env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://sibyl:your_secure_password@localhost:5432/sibyl
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO
```

#### 4. Set Up Database

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE sibyl;
CREATE USER sibyl WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE sibyl TO sibyl;

# Enable pgvector
\c sibyl
CREATE EXTENSION vector;
```

#### 5. Initialize Sibyl

```bash
# Validate workspace
sibyl workspace validate config/workspaces/prod_pgvector.yaml

# Test connection
sibyl pipeline run \
  --workspace config/workspaces/prod_pgvector.yaml \
  --pipeline health_check
```

#### 6. Set Up Systemd Service

Create `/etc/systemd/system/sibyl.service`:

```ini
[Unit]
Description=Sibyl MCP Server
After=network.target postgresql.service

[Service]
Type=simple
User=sibyl
Group=sibyl
WorkingDirectory=/home/sibyl/sibyl
Environment="PATH=/home/sibyl/sibyl/.venv/bin"
EnvironmentFile=/home/sibyl/sibyl/.env
ExecStart=/home/sibyl/sibyl/.venv/bin/sibyl-mcp \
  --workspace /home/sibyl/sibyl/config/workspaces/prod_pgvector.yaml \
  --transport http \
  --port 8000

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable sibyl
sudo systemctl start sibyl

# Check status
sudo systemctl status sibyl
```

#### 7. Configure Nginx

Create `/etc/nginx/sites-available/sibyl`:

```nginx
server {
    listen 80;
    server_name sibyl.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8001/health;
        access_log off;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/sibyl /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 8. Set Up SSL/TLS

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d sibyl.example.com
```

---

### Method 2: Docker Deployment

Containerized deployment for consistency and portability.

#### 1. Create Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy application
COPY . /app

# Install Sibyl
RUN pip install --no-cache-dir -e ".[vector,monitoring,rest]"

# Expose ports
EXPOSE 8000 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# Run server
CMD ["sibyl-mcp", "--workspace", "config/workspaces/prod.yaml", "--transport", "http", "--port", "8000"]
```

#### 2. Create Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  sibyl:
    build: .
    container_name: sibyl-server
    ports:
      - "8000:8000"
      - "9090:9090"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/sibyl
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
    networks:
      - sibyl-network

  postgres:
    image: pgvector/pgvector:pg15
    container_name: sibyl-postgres
    environment:
      - POSTGRES_DB=sibyl
      - POSTGRES_USER=sibyl
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    networks:
      - sibyl-network

  redis:
    image: redis:7-alpine
    container_name: sibyl-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped
    networks:
      - sibyl-network

  nginx:
    image: nginx:alpine
    container_name: sibyl-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - sibyl
    restart: unless-stopped
    networks:
      - sibyl-network

volumes:
  postgres-data:
  redis-data:

networks:
  sibyl-network:
    driver: bridge
```

#### 3. Deploy

```bash
# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f sibyl

# Check health
curl http://localhost:8000/health

# Scale if needed
docker-compose up -d --scale sibyl=3
```

---

### Method 3: Kubernetes Deployment

For large-scale, orchestrated deployments.

#### 1. Create Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sibyl
  labels:
    app: sibyl
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sibyl
  template:
    metadata:
      labels:
        app: sibyl
    spec:
      containers:
      - name: sibyl
        image: sibyl:latest
        ports:
        - containerPort: 8000
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: sibyl-secrets
              key: openai-api-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: sibyl-secrets
              key: database-url
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 5
```

#### 2. Create Service

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: sibyl
spec:
  selector:
    app: sibyl
  ports:
  - name: http
    port: 80
    targetPort: 8000
  - name: metrics
    port: 9090
    targetPort: 9090
  type: LoadBalancer
```

#### 3. Create ConfigMap and Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: sibyl-secrets
type: Opaque
stringData:
  openai-api-key: sk-...
  anthropic-api-key: sk-ant-...
  database-url: postgresql://...
```

```bash
# Apply configuration
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Check status
kubectl get pods -l app=sibyl
kubectl logs -f deployment/sibyl
```

---

## Environment-Specific Configuration

### Development

```yaml
# config/workspaces/dev.yaml
name: development

providers:
  llm:
    primary:
      kind: openai
      model: gpt-3.5-turbo      # Cheaper for dev

  vector_store:
    main:
      kind: duckdb              # Embedded, no setup
      dsn: "duckdb://./data/dev.duckdb"

budget:
  max_cost_usd: 10.0            # Low limit

observability:
  logging:
    level: DEBUG                # Verbose logs
```

### Staging

```yaml
# config/workspaces/staging.yaml
name: staging

providers:
  llm:
    primary:
      kind: openai
      model: gpt-4

  vector_store:
    main:
      kind: pgvector
      dsn: "${STAGING_DATABASE_URL}"

budget:
  max_cost_usd: 100.0

observability:
  logging:
    level: INFO
  metrics:
    enabled: true
```

### Production

```yaml
# config/workspaces/prod.yaml
name: production

providers:
  llm:
    primary:
      kind: openai
      model: gpt-4
    fallback:
      kind: anthropic
      model: claude-3-opus-20240229

  vector_store:
    main:
      kind: pgvector
      dsn: "${DATABASE_URL}"
      pool_size: 50
      index_type: hnsw

budget:
  max_cost_usd: 1000.0
  alert_threshold: 0.8

observability:
  logging:
    level: INFO
  metrics:
    enabled: true
  tracing:
    enabled: true

security:
  pii_redaction: true
  prompt_injection_detection: true
```

---

## Post-Deployment

### 1. Verify Deployment

```bash
# Check health
curl http://your-server/health

# Test MCP tools
curl -X POST http://your-server/mcp/tools

# Run test pipeline
sibyl pipeline run \
  --workspace config/workspaces/prod.yaml \
  --pipeline health_check
```

### 2. Load Initial Data

```bash
# Index documents
sibyl pipeline run \
  --workspace config/workspaces/prod.yaml \
  --pipeline index_documents \
  --param source_path=/path/to/docs
```

### 3. Set Up Monitoring

See [Observability Guide](observability.md).

### 4. Configure Backups

```bash
# Database backups
pg_dump -h localhost -U sibyl sibyl > backup_$(date +%Y%m%d).sql

# Vector store backups
cp -r data/vectors.duckdb backups/

# Automate with cron
0 2 * * * /path/to/backup.sh
```

### 5. Set Up Alerts

Configure alerts for:
- High error rates
- Budget thresholds
- System resource usage
- API response times

---

## Scaling

### Horizontal Scaling

```bash
# Add more servers
docker-compose up -d --scale sibyl=5

# Or in Kubernetes
kubectl scale deployment sibyl --replicas=10
```

### Vertical Scaling

```yaml
# Increase resources
resources:
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

### Database Scaling

- Use read replicas for queries
- Partition large tables
- Optimize indexes
- Connection pooling

---

## Best Practices

1. **Use Environment Variables** for secrets
2. **Enable Health Checks** for all services
3. **Set Resource Limits** to prevent resource exhaustion
4. **Monitor Everything** - logs, metrics, traces
5. **Automate Backups** - daily database and vector store backups
6. **Use SSL/TLS** in production
7. **Implement Rate Limiting** to prevent abuse
8. **Version Your Deployments** - tag Docker images, use semantic versioning
9. **Test Before Production** - staging environment that mirrors production
10. **Have Rollback Plan** - ability to quickly rollback to previous version

---

## Troubleshooting

See [Troubleshooting Guide](troubleshooting.md) for common deployment issues.

## Further Reading

- **[Observability](observability.md)** - Monitoring and logging
- **[Troubleshooting](troubleshooting.md)** - Common issues
- **[Security](security.md)** - Security best practices
- **[Performance Tuning](performance-tuning.md)** - Optimization guide

---

**Previous**: [MCP Overview](../mcp/overview.md) | **Next**: [Observability](observability.md)

# Sibyl Troubleshooting Guide

Common issues and their solutions.

## Container Issues

### Container Won't Start

**Symptom**: Container exits immediately after starting

**Diagnosis**:
```bash
# Check container logs
docker compose logs sibyl-dev

# Check container status
docker compose ps

# Inspect container
docker inspect sibyl-dev
```

**Common Causes**:

1. **Missing API Keys**
   ```bash
   # Check environment
   docker compose exec sibyl-dev env | grep API_KEY

   # Solution: Add keys to .env or .secrets/api_keys.txt
   ```

2. **Port Already in Use**
   ```bash
   # Find process using port
   sudo lsof -i :8770

   # Solution: Stop conflicting process or change port in .env
   SIBYL_MCP_HTTP_PORT=8771
   ```

3. **Invalid Workspace Configuration**
   ```bash
   # Check workspace file
   docker compose exec sibyl-dev cat /app/config/workspaces/example_local.yaml

   # Solution: Fix YAML syntax errors
   ```

### Container is Unhealthy

**Symptom**: `docker compose ps` shows "unhealthy" status

**Diagnosis**:
```bash
# Check health check logs
docker inspect sibyl-dev | grep -A 10 Health

# Test health endpoint manually
curl http://localhost:8770/health
```

**Solutions**:
```bash
# 1. Restart container
docker compose restart sibyl-dev

# 2. Check application logs
./scripts/logs.sh sibyl-dev

# 3. Increase health check timeouts in docker-compose.yml
healthcheck:
  start_period: 30s  # Increase from 15s
  interval: 60s      # Increase from 30s
```

## Network Issues

### Cannot Connect to Service

**Symptom**: Connection refused or timeout errors

**Diagnosis**:
```bash
# Check if container is running
docker compose ps

# Check port mappings
docker compose port sibyl-dev 8770

# Test from within container
docker compose exec sibyl-dev curl http://localhost:8770/health

# Check networks
docker network ls
docker network inspect sibyl_private
```

**Solutions**:

1. **Verify Port Mapping**
   ```bash
   # Ensure ports are exposed in docker-compose.yml
   ports:
     - "8770:8770"
   ```

2. **Check Firewall**
   ```bash
   # Check firewall rules
   sudo ufw status

   # Allow port
   sudo ufw allow 8770/tcp
   ```

3. **Network Isolation Issue**
   ```bash
   # Add service to correct network
   networks:
     - public  # For external access
     - private # For internal services
   ```

## Performance Issues

### High Memory Usage

**Symptom**: Container using excessive memory

**Diagnosis**:
```bash
# Check memory usage
docker stats sibyl-dev

# Check DuckDB memory
docker compose exec sibyl-dev sh -c 'echo "SELECT * FROM duckdb_memory();" | duckdb /var/lib/sibyl/state/sibyl_state.duckdb'
```

**Solutions**:
```bash
# 1. Increase memory limit in .env
SIBYL_MEMORY_LIMIT=8G
DUCKDB_MEMORY_LIMIT=4GB

# 2. Restart with new limits
docker compose up -d

# 3. Check for memory leaks
docker compose logs sibyl-dev | grep -i "memory\|oom"
```

### Slow Response Times

**Diagnosis**:
```bash
# Check request latency in Prometheus
curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95, rate(sibyl_request_duration_seconds_bucket[5m]))'

# Check system resources
docker stats

# Profile application
docker compose logs sibyl-dev | grep -i "slow\|timeout"
```

**Solutions**:

1. **Increase Resources**
   ```bash
   SIBYL_CPU_LIMIT=4.0
   SIBYL_MEMORY_LIMIT=8G
   ```

2. **Optimize DuckDB**
   ```bash
   DUCKDB_MEMORY_LIMIT=4GB  # Increase from 2GB
   ```

3. **Check for Rate Limiting**
   ```bash
   # View nginx logs
   docker compose logs nginx | grep -i "limit"
   ```

## Database Issues

### DuckDB Lock Error

**Symptom**: "database is locked" errors

**Solution**:
```bash
# 1. Stop all services
docker compose down

# 2. Remove lock file
docker volume inspect sibyl_state
# Manually remove .wal or .lock files if needed

# 3. Restart
docker compose up -d
```

### State Corruption

**Symptom**: Database errors, inconsistent state

**Solution**:
```bash
# 1. Stop services
docker compose down

# 2. Restore from backup
cd devops/scripts
./restore-state.sh

# 3. Restart
./start-prod.sh
```

## SSL/TLS Issues

### Certificate Errors

**Symptom**: "certificate verify failed" or "SSL handshake failed"

**Diagnosis**:
```bash
# Test SSL certificate
openssl s_client -connect localhost:443 -servername sibyl.example.com

# Check certificate expiry
openssl x509 -in devops/config/ssl/cert.pem -noout -dates

# Verify certificate chain
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt devops/config/ssl/cert.pem
```

**Solutions**:

1. **Renew Certificate**
   ```bash
   # Let's Encrypt renewal
   sudo certbot renew

   # Copy new certificates
   sudo cp /etc/letsencrypt/live/sibyl.example.com/fullchain.pem devops/config/ssl/cert.pem
   sudo cp /etc/letsencrypt/live/sibyl.example.com/privkey.pem devops/config/ssl/key.pem

   # Reload nginx
   docker compose exec nginx nginx -s reload
   ```

2. **Fix Certificate Permissions**
   ```bash
   chmod 644 devops/config/ssl/cert.pem
   chmod 600 devops/config/ssl/key.pem
   ```

## Observability Issues

### Grafana Shows No Data

**Diagnosis**:
```bash
# Check Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# Verify metrics endpoint
curl http://localhost:9090/metrics
```

**Solution**:
```bash
# 1. Restart Prometheus
docker compose restart prometheus

# 2. Check datasource configuration in Grafana
# URL should be: http://prometheus:9090

# 3. Verify network connectivity
docker compose exec grafana curl http://prometheus:9090/api/v1/query?query=up
```

### Logs Not Appearing in Loki

**Diagnosis**:
```bash
# Check Fluent Bit is running
docker compose ps fluent-bit

# View Fluent Bit logs
docker compose logs fluent-bit

# Test Loki endpoint
curl http://localhost:3100/ready
```

**Solution**:
```bash
# Restart Fluent Bit
docker compose restart fluent-bit

# Check log volume permissions
docker volume inspect sibyl_logs
```

## Common Error Messages

### "API key not found"

**Cause**: Missing or incorrectly configured API keys

**Solution**:
```bash
# Check secrets file exists
ls -la devops/docker/.secrets/api_keys.txt

# Verify format (no quotes, no spaces around =)
cat devops/docker/.secrets/api_keys.txt

# Correct format:
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Restart services
docker compose restart
```

### "Workspace file not found"

**Cause**: Invalid workspace file path

**Solution**:
```bash
# Check workspace exists
docker compose exec sibyl-dev ls -la /app/config/workspaces/

# Verify path in .env
cat .env.dev | grep SIBYL_WORKSPACE_FILE

# Should be:
SIBYL_WORKSPACE_FILE=/app/config/workspaces/example_local.yaml
```

### "Permission denied"

**Cause**: File/directory permission issues

**Solution**:
```bash
# Fix ownership
sudo chown -R 10001:10001 /var/lib/docker/volumes/sibyl_state

# Or recreate volume
docker volume rm sibyl_state
docker compose up -d
```

## Debugging Commands

### View All Logs
```bash
# All services
./scripts/logs.sh -f -a

# Specific service
./scripts/logs.sh -f sibyl-prod
```

### Exec Into Container
```bash
# Development
docker compose exec sibyl-dev sh

# Production (limited shell)
docker compose exec sibyl-prod sh

# Run specific command
docker compose exec sibyl-dev python -m sibyl --version
```

### Check Resource Usage
```bash
# Real-time stats
docker stats

# Historical stats from Prometheus
curl 'http://localhost:9090/api/v1/query?query=process_resident_memory_bytes'
```

### Network Debugging
```bash
# List all networks
docker network ls

# Inspect network
docker network inspect sibyl_private

# Test connectivity
docker compose exec sibyl-dev ping prometheus
docker compose exec sibyl-dev curl http://prometheus:9090
```

## Getting Help

If you're still experiencing issues:

1. **Collect Debug Information**:
   ```bash
   # Save all logs
   docker compose logs > sibyl-logs.txt

   # Save configuration
   docker compose config > docker-compose-resolved.yml

   # Save system info
   docker version > debug-info.txt
   docker compose version >> debug-info.txt
   docker system df >> debug-info.txt
   ```

2. **Check GitHub Issues**: https://github.com/sibyl/sibyl/issues

3. **Community Support**: Join Discord or forums

4. **Include in Bug Report**:
   - Sibyl version
   - Docker version
   - Operating system
   - Steps to reproduce
   - Relevant logs (sibyl-logs.txt)
   - Configuration (sanitize secrets!)

## Quick Fixes

### Complete Reset

**WARNING**: This deletes all data!

```bash
# Stop and remove everything
cd devops/docker
docker compose down -v

# Remove images
docker rmi $(docker images | grep sibyl | awk '{print $3}')

# Start fresh
cd ../scripts
./start-dev.sh
```

### Rebuild Everything

```bash
cd devops/scripts
./update.sh --no-cache
./start-dev.sh
```

### Clean and Restart

```bash
cd devops/scripts
./cleanup.sh
./start-dev.sh
```

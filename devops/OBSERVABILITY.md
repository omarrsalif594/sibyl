# Sibyl Observability Guide

Complete guide to monitoring, logging, and tracing for Sibyl MCP Server.

## Overview

The observability stack provides three pillars:

1. **Metrics** - Prometheus + Grafana
2. **Logs** - Loki + Fluent Bit
3. **Traces** - Jaeger (optional)

## Quick Start

```bash
# Start with full observability stack
cd devops/scripts
./start-dev.sh --observability

# Or for production
./start-prod.sh --tracing  # Includes observability + tracing
```

## Prometheus (Metrics)

### Access
- URL: `http://localhost:9090`
- Scrape interval: 15s
- Retention: 30 days

### Key Metrics

Sibyl exposes the following metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `up` | Gauge | Service health (1=up, 0=down) |
| `sibyl_requests_total` | Counter | Total API requests |
| `sibyl_errors_total` | Counter | Total errors |
| `sibyl_request_duration_seconds` | Histogram | Request latency |
| `sibyl_duckdb_operations_total` | Counter | DuckDB operations |
| `process_resident_memory_bytes` | Gauge | Memory usage |
| `process_cpu_seconds_total` | Counter | CPU usage |

### Example Queries

```promql
# Request rate (requests per second)
rate(sibyl_requests_total[5m])

# Error rate
rate(sibyl_errors_total[5m]) / rate(sibyl_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(sibyl_request_duration_seconds_bucket[5m]))

# Memory usage in GB
process_resident_memory_bytes / 1024 / 1024 / 1024

# CPU usage percentage
rate(process_cpu_seconds_total[5m]) * 100
```

## Grafana (Dashboards)

### Access
- URL: `http://localhost:3000`
- Default credentials: `admin` / `admin`
- **Important**: Change password on first login!

### Pre-configured Dashboards

1. **Sibyl Overview** - Main application dashboard
   - Service status
   - Request rate and errors
   - Resource usage (CPU, memory)
   - DuckDB operations
   - API response times

### Creating Custom Dashboards

1. Navigate to `Create` → `Dashboard`
2. Add panel
3. Select Prometheus datasource
4. Enter PromQL query
5. Configure visualization
6. Save dashboard

### Setting Up Alerts

1. **Navigate to Alerting**
   - Grafana → Alerting → Alert rules

2. **Create Alert Rule**
   ```yaml
   Name: High Error Rate
   Query: rate(sibyl_errors_total[5m]) > 0.1
   Condition: above 0.1 for 5 minutes
   ```

3. **Configure Notification Channel**
   - Slack, Email, PagerDuty, etc.
   - Test notification

4. **Example Alert Rules**:
   - High error rate (> 10 errors/min)
   - High memory usage (> 6GB)
   - Service down (up == 0)
   - DuckDB errors (> 10/5min)

## Loki (Logs)

### Access
- URL: `http://localhost:3100`
- Retention: 30 days
- Query via Grafana

### Querying Logs in Grafana

1. Go to Explore
2. Select Loki datasource
3. Use LogQL queries:

```logql
# All logs from sibyl-prod
{container_name="sibyl-prod"}

# Error logs only
{container_name="sibyl-prod"} |= "ERROR"

# Logs with JSON parsing
{container_name="sibyl-prod"} | json | level="ERROR"

# Logs from last 5 minutes
{container_name="sibyl-prod"} [5m]

# Count errors per minute
sum by (level) (rate({container_name="sibyl-prod"} |= "ERROR" [1m]))
```

### Log Levels

Sibyl logs at different levels:
- `DEBUG` - Detailed debugging information
- `INFO` - General informational messages
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical errors

Change log level via `SIBYL_LOG_LEVEL` environment variable.

## Fluent Bit (Log Forwarding)

Fluent Bit collects logs from:
- Sibyl application logs (`/var/log/sibyl/`)
- Docker container logs

Configuration: `devops/observability/fluent-bit/fluent-bit.conf`

## Jaeger (Distributed Tracing)

### Access
- URL: `http://localhost:16686`

### Enable Tracing

```bash
# Start with tracing enabled
./start-prod.sh --tracing
```

### View Traces

1. Open Jaeger UI
2. Select service: `sibyl-mcp`
3. Click "Find Traces"
4. Click on a trace to view details

### Trace Information
- Request flow
- Service dependencies
- Latency breakdown
- Errors and exceptions

## Monitoring Best Practices

### 1. Set Up Alerts

Create alerts for critical metrics:

```yaml
# devops/observability/prometheus/alerts.yml
- alert: SibylServiceDown
  expr: up{job=~"sibyl.*"} == 0
  for: 1m

- alert: HighErrorRate
  expr: rate(sibyl_errors_total[5m]) > 0.1
  for: 5m

- alert: HighMemoryUsage
  expr: process_resident_memory_bytes / 1024 / 1024 / 1024 > 6
  for: 5m
```

### 2. Regular Reviews

- Daily: Check for errors and anomalies
- Weekly: Review resource usage trends
- Monthly: Optimize based on metrics

### 3. Log Retention

Adjust retention based on needs:

```yaml
# Prometheus (devops/observability/prometheus/prometheus.yml)
storage:
  tsdb:
    retention.time: 30d

# Loki (devops/observability/loki/loki-config.yaml)
limits_config:
  retention_period: 30d
```

## Troubleshooting Observability Stack

### Prometheus Not Scraping Metrics

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify Sibyl metrics endpoint
curl http://localhost:9090/metrics

# Check Prometheus logs
docker compose logs prometheus
```

### Grafana Not Showing Data

```bash
# Verify datasource configuration
# Grafana → Configuration → Data sources

# Test datasource connection
# Click "Test" button in datasource settings

# Check Grafana logs
docker compose logs grafana
```

### Loki Not Receiving Logs

```bash
# Check Fluent Bit status
docker compose logs fluent-bit

# Verify Loki is running
curl http://localhost:3100/ready

# Test log ingestion
curl -H "Content-Type: application/json" \
  -XPOST -s "http://localhost:3100/loki/api/v1/push" \
  --data '{"streams":[{"stream":{"job":"test"},"values":[["'$(date +%s)'000000000","test log message"]]}]}'
```

## Performance Tuning

### Prometheus

```yaml
# Reduce scrape interval for less critical services
scrape_interval: 30s

# Increase retention for important metrics
storage:
  tsdb:
    retention.time: 90d
```

### Loki

```yaml
# Adjust chunk size for better performance
chunk_store_config:
  max_look_back_period: 168h

# Increase ingestion limits
limits_config:
  ingestion_rate_mb: 10
  ingestion_burst_size_mb: 20
```

## Exporting Metrics

### Export Prometheus Data

```bash
# Query API
curl 'http://localhost:9090/api/v1/query?query=up'

# Export to file
curl 'http://localhost:9090/api/v1/query?query=up' > metrics.json
```

### Export Grafana Dashboards

```bash
# Via UI: Dashboard → Share → Export → Save to file

# Via API
curl -H "Authorization: Bearer <api-key>" \
  http://localhost:3000/api/dashboards/uid/<dashboard-uid>
```

## Next Steps

- Set up external alert destinations (Slack, PagerDuty)
- Create custom dashboards for your workspaces
- Configure log retention policies
- Set up remote storage for Prometheus (for long-term retention)

# Observability Guide

Complete guide to monitoring, logging, and observing Sibyl in production.

## Overview

Observability is critical for understanding system behavior, debugging issues, and optimizing performance. Sibyl provides comprehensive observability through:

1. **Logging** - Structured application logs
2. **Metrics** - Prometheus metrics for monitoring
3. **Tracing** - Distributed tracing with OpenTelemetry
4. **Health Checks** - System health endpoints
5. **Alerting** - Proactive issue detection

## Logging

### Configuration

```yaml
# config/workspaces/prod.yaml
observability:
  logging:
    # Log level
    level: INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # Output format
    format: json                   # json, text

    # What to log
    log_requests: true
    log_responses: false           # Don't log full responses (privacy)
    log_errors: true
    log_slow_requests: true
    slow_request_threshold: 5.0    # Log if >5 seconds

    # File output
    file:
      enabled: true
      path: /var/log/sibyl/app.log
      rotation:
        max_bytes: 10485760        # 10MB per file
        backup_count: 10           # Keep 10 files

    # Console output
    console:
      enabled: true
      colorize: true               # Color-coded logs

    # Structured fields
    extra_fields:
      service: sibyl
      environment: production
      version: "1.0.0"
      hostname: "${HOSTNAME}"

    # Component-specific levels
    components:
      rag: DEBUG                   # Verbose RAG logs
      llm: INFO                    # Info for LLM calls
      database: WARNING            # Only warnings for DB
      cache: WARNING
```

### Log Format

**JSON logs** (recommended for production):
```json
{
  "timestamp": "2024-01-01T12:00:00.123Z",
  "level": "INFO",
  "service": "sibyl",
  "environment": "production",
  "version": "1.0.0",
  "hostname": "sibyl-prod-01",
  "component": "rag",
  "event": "retrieval_complete",
  "message": "Retrieved 5 documents for query",
  "context": {
    "query": "machine learning",
    "top_k": 5,
    "duration_ms": 234,
    "user_id": "user_123",
    "request_id": "req_abc123"
  }
}
```

**Text logs** (development):
```
2024-01-01 12:00:00,123 INFO [rag] retrieval_complete: Retrieved 5 documents for query (234ms) user=user_123 request=req_abc123
```

### Log Aggregation

#### Loki (Recommended)

**docker-compose.yml**:
```yaml
services:
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml
      - loki-data:/loki

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yaml:/etc/promtail/config.yml
    depends_on:
      - loki
```

**promtail-config.yaml**:
```yaml
server:
  http_listen_port: 9080

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: sibyl
    static_configs:
      - targets:
          - localhost
        labels:
          job: sibyl
          __path__: /var/log/sibyl/*.log
```

#### ELK Stack

**Filebeat configuration**:
```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/sibyl/*.log
    json.keys_under_root: true
    json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "sibyl-logs-%{+yyyy.MM.dd}"

setup.kibana:
  host: "kibana:5601"
```

### Log Queries

**Find errors**:
```bash
# Loki (LogQL)
{service="sibyl"} |= "ERROR"

# Search last hour
{service="sibyl"} |= "ERROR" | json | timestamp > now() - 1h

# Filter by component
{service="sibyl", component="rag"} |= "ERROR"
```

**Elasticsearch**:
```json
{
  "query": {
    "bool": {
      "must": [
        {"term": {"level": "ERROR"}},
        {"range": {"timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}
```

## Metrics

### Prometheus Configuration

```yaml
# config/workspaces/prod.yaml
observability:
  metrics:
    enabled: true
    port: 9090
    path: /metrics

    # What to collect
    collect_tool_metrics: true
    collect_request_metrics: true
    collect_pipeline_metrics: true
    collect_provider_metrics: true
    collect_cache_metrics: true

    # Labels
    labels:
      service: sibyl
      environment: production
      region: us-west-2
      instance: "${HOSTNAME}"

    # Custom metrics
    custom:
      - name: query_length
        type: histogram
        description: "Query length in characters"
        buckets: [10, 50, 100, 500, 1000, 5000]

      - name: retrieval_quality
        type: gauge
        description: "Average retrieval quality score"

      - name: generation_cost
        type: counter
        description: "Total generation cost in USD"
        labels: [model, provider]
```

### Available Metrics

#### Tool Metrics

```prometheus
# Total tool calls
sibyl_mcp_tool_calls_total{tool="search_documents",status="success"} 1234

# Tool execution duration
sibyl_mcp_tool_duration_seconds{tool="search_documents"} 1.23

# Tool errors
sibyl_mcp_tool_errors_total{tool="search_documents",error_type="timeout"} 5
```

#### Pipeline Metrics

```prometheus
# Pipeline executions
sibyl_pipeline_executions_total{pipeline="qa_over_docs",status="success"} 5678

# Pipeline duration
sibyl_pipeline_duration_seconds{pipeline="qa_over_docs"} 2.34

# Step duration
sibyl_pipeline_step_duration_seconds{pipeline="qa_over_docs",step="retrieval"} 0.45
```

#### Provider Metrics

```prometheus
# LLM API calls
sibyl_llm_calls_total{provider="openai",model="gpt-4",status="success"} 890

# LLM tokens
sibyl_llm_tokens_total{provider="openai",model="gpt-4",type="prompt"} 45678
sibyl_llm_tokens_total{provider="openai",model="gpt-4",type="completion"} 23456

# LLM cost
sibyl_llm_cost_usd_total{provider="openai",model="gpt-4"} 12.34

# Vector store operations
sibyl_vector_store_operations_total{operation="search",provider="pgvector"} 2345
```

#### Cache Metrics

```prometheus
# Cache hits/misses
sibyl_cache_hits_total{cache="semantic"} 789
sibyl_cache_misses_total{cache="semantic"} 234

# Cache hit rate
sibyl_cache_hit_rate{cache="semantic"} 0.77

# Cache size
sibyl_cache_size_bytes{cache="semantic"} 524288000
```

#### System Metrics

```prometheus
# Active requests
sibyl_active_requests 42

# Request rate
sibyl_requests_per_second 15.3

# Error rate
sibyl_error_rate 0.02

# Database connections
sibyl_database_connections_active 15
sibyl_database_connections_idle 5
```

### Prometheus Scrape Config

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'sibyl'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 15s
    scrape_timeout: 10s
```

### Grafana Dashboards

#### Import Pre-built Dashboard

```bash
# Download dashboard JSON
curl -O https://raw.githubusercontent.com/yourusername/sibyl/main/dashboards/sibyl-overview.json

# Import to Grafana
# Navigate to Grafana > Dashboards > Import
# Upload sibyl-overview.json
```

#### Key Panels

**Request Rate**:
```promql
rate(sibyl_mcp_tool_calls_total[5m])
```

**Error Rate**:
```promql
rate(sibyl_mcp_tool_errors_total[5m]) /
rate(sibyl_mcp_tool_calls_total[5m])
```

**P95 Latency**:
```promql
histogram_quantile(0.95,
  rate(sibyl_mcp_tool_duration_seconds_bucket[5m])
)
```

**LLM Cost per Hour**:
```promql
rate(sibyl_llm_cost_usd_total[1h]) * 3600
```

**Cache Hit Rate**:
```promql
sibyl_cache_hits_total /
(sibyl_cache_hits_total + sibyl_cache_misses_total)
```

## Distributed Tracing

### OpenTelemetry Configuration

```yaml
observability:
  tracing:
    enabled: true
    exporter: jaeger               # jaeger, zipkin, otlp

    # Jaeger configuration
    jaeger:
      endpoint: "http://jaeger:14268/api/traces"
      service_name: sibyl

    # Sampling
    sampling:
      type: probabilistic          # always, never, probabilistic
      rate: 0.1                    # Sample 10% of requests

    # What to trace
    trace_tools: true
    trace_pipelines: true
    trace_providers: true
    trace_database: true

    # Custom instrumentation
    custom_spans:
      - name: retrieval
        technique: rag.retrieval
      - name: generation
        technique: ai_generation.generation
```

### Jaeger Deployment

```yaml
# docker-compose.yml
services:
  jaeger:
    image: jaegertracing/all-in-one:1.50
    ports:
      - "5775:5775/udp"
      - "6831:6831/udp"
      - "6832:6832/udp"
      - "5778:5778"
      - "16686:16686"       # UI
      - "14268:14268"
      - "14250:14250"
      - "9411:9411"
    environment:
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
```

**Access Jaeger UI**: `http://localhost:16686`

### Trace Example

```
Request: search_documents(query="What is Sibyl?")
├─ Span: query_processing (12ms)
│  └─ Span: query_expansion (8ms)
├─ Span: retrieval (234ms)
│  ├─ Span: embedding (45ms)
│  ├─ Span: vector_search (156ms)
│  │  └─ Span: pgvector.query (145ms)
│  └─ Span: reranking (33ms)
└─ Span: generation (1234ms)
   └─ Span: openai.complete (1225ms)

Total: 1480ms
```

## Health Checks

### Health Check Endpoints

```yaml
observability:
  health:
    enabled: true
    port: 8001
    path: /health

    # Liveness endpoint (is server running?)
    liveness:
      path: /health/live
      timeout: 5

    # Readiness endpoint (ready for traffic?)
    readiness:
      path: /health/ready
      timeout: 10

    # Checks to perform
    checks:
      - name: database
        type: database
        connection: "${DATABASE_URL}"
        timeout: 5
        critical: true           # Fail health check if this fails

      - name: vector_store
        type: vector_store
        provider: main
        timeout: 5
        critical: true

      - name: llm_provider
        type: llm
        provider: primary
        timeout: 10
        critical: false          # Don't fail health check

      - name: cache
        type: redis
        url: "${REDIS_URL}"
        timeout: 2
        critical: false
```

### Health Check Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 5,
      "details": {
        "connection": "active",
        "pool_size": 20,
        "active_connections": 5
      }
    },
    "vector_store": {
      "status": "healthy",
      "latency_ms": 12,
      "details": {
        "documents_indexed": 10000,
        "last_index_time": "2024-01-01T12:00:00Z"
      }
    },
    "llm_provider": {
      "status": "degraded",
      "latency_ms": 2500,
      "details": {
        "provider": "openai",
        "rate_limit_remaining": 10
      }
    },
    "cache": {
      "status": "healthy",
      "latency_ms": 2,
      "details": {
        "hit_rate": 0.85,
        "size_mb": 256
      }
    }
  }
}
```

### Kubernetes Integration

```yaml
# deployment.yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8001
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8001
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 10
  failureThreshold: 3
```

## Alerting

### AlertManager Configuration

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@example.com'
  smtp_auth_username: 'alerts@example.com'
  smtp_auth_password: '${SMTP_PASSWORD}'

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'team-notifications'

  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'

    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'team-notifications'
    email_configs:
      - to: 'team@example.com'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_KEY}'

  - name: 'slack'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK}'
        channel: '#alerts'
```

### Alert Rules

```yaml
# prometheus-alerts.yml
groups:
  - name: sibyl_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          rate(sibyl_mcp_tool_errors_total[5m]) /
          rate(sibyl_mcp_tool_calls_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(sibyl_mcp_tool_duration_seconds_bucket[5m])
          ) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P95 latency is {{ $value }}s"

      # Database connection issues
      - alert: DatabaseConnectionLow
        expr: sibyl_database_connections_active < 5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Low database connections"
          description: "Only {{ $value }} active connections"

      # High LLM cost
      - alert: HighLLMCost
        expr: |
          rate(sibyl_llm_cost_usd_total[1h]) * 3600 > 100
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "High LLM cost"
          description: "Cost is ${{ $value }}/hour"

      # Cache degradation
      - alert: LowCacheHitRate
        expr: sibyl_cache_hit_rate < 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value | humanizePercentage }}"

      # Service down
      - alert: ServiceDown
        expr: up{job="sibyl"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Sibyl service is down"
          description: "Service has been down for 1 minute"
```

## Performance Monitoring

### Key Performance Indicators (KPIs)

```yaml
observability:
  kpis:
    # Response time SLO
    - name: response_time_p95
      metric: sibyl_mcp_tool_duration_seconds
      threshold: 2.0
      percentile: 0.95
      window: 5m

    # Availability SLO
    - name: availability
      target: 0.999              # 99.9% uptime
      window: 30d

    # Error rate SLO
    - name: error_rate
      threshold: 0.01            # <1% errors
      window: 1h

    # LLM cost target
    - name: llm_cost_per_query
      threshold: 0.05            # <$0.05 per query
      window: 1d
```

### Custom Dashboards

**Executive Dashboard**:
- Total queries (24h, 7d, 30d)
- Success rate
- Average response time
- Total cost
- Active users

**Operations Dashboard**:
- Request rate
- Error rate
- P50/P95/P99 latency
- Cache hit rate
- Database performance
- LLM API status

**Cost Dashboard**:
- Cost per query
- Cost by model
- Cost trend
- Budget utilization
- Cost breakdown (LLM, storage, compute)

## Best Practices

1. **Use structured logging (JSON)**: Easier to parse and query
2. **Include context in logs**: request_id, user_id, query, etc.
3. **Set appropriate log levels**: DEBUG in dev, INFO in prod
4. **Rotate logs**: Prevent disk space issues
5. **Monitor key metrics**: Error rate, latency, cost
6. **Set up alerts**: Proactive issue detection
7. **Use distributed tracing**: Debug complex issues
8. **Regular health checks**: Ensure system health
9. **Dashboard for stakeholders**: Visibility into system
10. **Retain logs appropriately**: Balance cost and compliance

## Troubleshooting

### High Memory Usage

**Check metrics**:
```promql
process_resident_memory_bytes{job="sibyl"}
```

**Actions**:
1. Check cache size: `sibyl_cache_size_bytes`
2. Review connection pools
3. Look for memory leaks in logs
4. Restart service if needed

### High Latency

**Trace slow requests**:
```bash
# Find slow traces in Jaeger
# Filter by duration > 5s
```

**Check metrics**:
```promql
histogram_quantile(0.95,
  rate(sibyl_pipeline_step_duration_seconds_bucket[5m])
)
```

**Actions**:
1. Identify slow step in trace
2. Check provider latency
3. Review database query performance
4. Optimize retrieval parameters

### Missing Logs

**Check configuration**:
```yaml
observability:
  logging:
    enabled: true
    file:
      enabled: true
      path: /var/log/sibyl/app.log
```

**Verify permissions**:
```bash
ls -l /var/log/sibyl/
```

**Check log aggregator**:
```bash
# Loki
curl http://localhost:3100/ready

# Check Promtail
curl http://localhost:9080/metrics
```

## Further Reading

- **[Deployment Guide](deployment.md)** - Production deployment
- **[Troubleshooting](troubleshooting.md)** - Common issues
- **[Performance Tuning](performance-tuning.md)** - Optimization
- **[Security Guide](security.md)** - Security best practices

---

**Previous**: [REST API](../mcp/rest-api.md) | **Next**: [Troubleshooting](troubleshooting.md)

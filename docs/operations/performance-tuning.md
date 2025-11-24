# Performance Tuning Guide

Complete guide to optimizing Sibyl for maximum performance and efficiency.

## Overview

This guide covers performance optimization across all system components:

1. **RAG Pipeline Optimization** - Improve retrieval and generation
2. **Database Optimization** - Optimize vector store queries
3. **Caching Strategies** - Reduce redundant computation
4. **Resource Management** - CPU, memory, and network optimization
5. **Scaling Strategies** - Horizontal and vertical scaling
6. **Cost Optimization** - Reduce operational costs

## Performance Metrics

### Key Performance Indicators

```yaml
observability:
  kpis:
    # Latency targets
    - name: p50_latency
      metric: sibyl_mcp_tool_duration_seconds
      target: 1.0                  # 1 second median
      percentile: 0.50

    - name: p95_latency
      metric: sibyl_mcp_tool_duration_seconds
      target: 3.0                  # 3 seconds P95
      percentile: 0.95

    - name: p99_latency
      metric: sibyl_mcp_tool_duration_seconds
      target: 5.0                  # 5 seconds P99
      percentile: 0.99

    # Throughput targets
    - name: requests_per_second
      metric: rate(sibyl_mcp_tool_calls_total[1m])
      target: 100

    # Resource utilization
    - name: cpu_usage
      target: 70                   # Target 70% utilization

    - name: memory_usage
      target: 80                   # Target 80% utilization

    # Cost efficiency
    - name: cost_per_query
      target: 0.05                 # $0.05 per query
```

### Measure Current Performance

```bash
# Latency distribution
curl http://localhost:9090/metrics | grep duration_seconds

# Request rate
curl http://localhost:9090/metrics | grep requests_total

# Cache hit rate
curl http://localhost:9090/metrics | grep cache_hits

# Resource usage
docker stats sibyl
```

## RAG Pipeline Optimization

### Chunking Optimization

**Problem**: Large chunks increase latency and cost

**Solution**:
```yaml
# Before (slow)
steps:
  - use: rag.chunking
    config:
      chunk_size: 2048             # Too large
      chunk_overlap: 512

# After (optimized)
steps:
  - use: rag.chunking
    config:
      chunk_size: 512              # Optimal for most cases
      chunk_overlap: 50            # Just enough overlap
      batch_size: 100              # Process in batches
```

**Impact**:
- Latency: -40%
- Memory: -60%
- Quality: Minimal impact

### Embedding Optimization

**Problem**: Embedding generation is slow

**Solutions**:

**1. Use faster models**:
```yaml
# Before (slow but accurate)
providers:
  embedding:
    default:
      kind: sentence-transformer
      model: all-mpnet-base-v2     # 768 dim, slower
      device: cpu

# After (faster)
providers:
  embedding:
    default:
      kind: sentence-transformer
      model: all-MiniLM-L6-v2      # 384 dim, 2x faster
      device: cuda                 # Use GPU if available
```

**2. Batch processing**:
```yaml
steps:
  - use: rag.embedding
    config:
      batch_size: 64               # Process 64 at once
      max_concurrent: 4            # Parallel batches
```

**3. Cache embeddings**:
```yaml
shops:
  infrastructure:
    config:
      caching:
        enabled: true
        cache_embeddings: true
        ttl: 86400                 # 24 hours
```

**Impact**:
- Throughput: +100% (batching)
- Latency: -50% (faster model)
- Cache hit: 70-90% (caching)

### Retrieval Optimization

**Problem**: Vector search is slow

**Solutions**:

**1. Optimize index**:
```yaml
# pgvector - use HNSW for speed
providers:
  vector_store:
    main:
      kind: pgvector
      index_type: hnsw             # Faster than ivfflat

      # HNSW parameters
      hnsw_ef_construction: 200    # Build quality
      hnsw_ef_search: 100          # Search quality (lower = faster)
      hnsw_m: 16                   # Connections per layer
```

**2. Reduce top_k**:
```yaml
# Before
steps:
  - use: rag.retrieval
    config:
      top_k: 20                    # Retrieve 20 documents

# After
steps:
  - use: rag.retrieval
    config:
      top_k: 5                     # Retrieve only 5
      similarity_threshold: 0.7    # Filter low quality
```

**3. Use approximate search**:
```yaml
providers:
  vector_store:
    main:
      kind: faiss
      index_type: IVF256,Flat      # Approximate search
      nprobe: 10                   # Search 10 clusters
```

**Impact**:
- HNSW vs IVFFlat: 3-10x faster
- top_k 5 vs 20: 4x faster
- Quality trade-off: <5%

### Generation Optimization

**Problem**: LLM generation is slow and expensive

**Solutions**:

**1. Use faster models**:
```yaml
# Before (slow, expensive)
providers:
  llm:
    primary:
      kind: openai
      model: gpt-4                 # Slow, $0.03/1k tokens

# After (faster, cheaper)
providers:
  llm:
    primary:
      kind: openai
      model: gpt-3.5-turbo         # 10x faster, $0.002/1k tokens
```

**2. Reduce max_tokens**:
```yaml
steps:
  - use: ai_generation.generation
    config:
      max_tokens: 500              # Limit response length
      stop_sequences: ["\n\n"]    # Stop early if possible
```

**3. Use streaming**:
```yaml
steps:
  - use: ai_generation.generation
    config:
      subtechnique: streaming      # Stream response
      chunk_size: 10               # Send 10 tokens at a time
```

**Impact**:
- Model switch: 10x faster, 15x cheaper
- Token limit: -50% latency
- Streaming: Better perceived performance

### Reranking Optimization

**Problem**: Reranking adds significant latency

**Solutions**:

**1. Skip for simple queries**:
```yaml
pipelines:
  adaptive_search:
    steps:
      - use: rag.retrieval

      # Only rerank if retrieval quality is low
      - use: rag.reranking
        condition: ${retrieval.avg_score} < 0.8
```

**2. Use faster reranker**:
```yaml
# Before (slow)
steps:
  - use: rag.reranking
    config:
      subtechnique: llm            # Very slow

# After (faster)
steps:
  - use: rag.reranking
    config:
      subtechnique: cross_encoder  # 10x faster
      model: cross-encoder/ms-marco-MiniLM-L-6-v2  # Fast model
```

**3. Reduce candidates**:
```yaml
steps:
  - use: rag.retrieval
    config:
      top_k: 20

  - use: rag.reranking
    config:
      top_k: 5                     # Rerank only top 5
```

**Impact**:
- Skip reranking: -30% latency
- Cross-encoder vs LLM: 10x faster
- Fewer candidates: -50% reranking time

## Database Optimization

### Connection Pooling

**Problem**: Connection overhead

**Solution**:
```yaml
providers:
  vector_store:
    main:
      kind: pgvector
      dsn: "${DATABASE_URL}"

      # Optimize pool
      pool_size: 50                # Max connections
      max_overflow: 20             # Extra connections
      pool_timeout: 30             # Wait for connection
      pool_recycle: 3600           # Recycle after 1 hour
      pool_pre_ping: true          # Verify connection
```

### Query Optimization

**PostgreSQL optimization**:
```sql
-- Analyze tables regularly
ANALYZE documents;

-- Vacuum to reclaim space
VACUUM ANALYZE documents;

-- Create appropriate indexes
CREATE INDEX idx_metadata_created ON documents ((metadata->>'created_at'));

-- Use EXPLAIN to optimize queries
EXPLAIN ANALYZE
SELECT * FROM documents
WHERE embedding <=> '[...]'::vector
ORDER BY embedding <=> '[...]'::vector
LIMIT 10;
```

**Index tuning**:
```sql
-- HNSW index (faster search)
CREATE INDEX ON documents
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 200);

-- Set search parameters
SET hnsw.ef_search = 100;  -- Lower = faster, less accurate
```

### Database Hardware

**Recommendations**:
- **CPU**: 4+ cores for concurrent queries
- **RAM**: 16GB+ for index caching
- **Storage**: NVMe SSD for fast I/O
- **Network**: 10Gbps for large vector transfers

**PostgreSQL configuration**:
```ini
# /etc/postgresql/15/main/postgresql.conf

# Memory
shared_buffers = 4GB           # 25% of total RAM
effective_cache_size = 12GB    # 75% of total RAM
work_mem = 64MB                # Per operation
maintenance_work_mem = 1GB     # For VACUUM, CREATE INDEX

# Connections
max_connections = 200

# Query planner
random_page_cost = 1.1         # SSD (lower than default 4.0)
effective_io_concurrency = 200 # SSD

# Autovacuum
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 10s
```

## Caching Strategies

### Semantic Caching

**Configuration**:
```yaml
shops:
  infrastructure:
    config:
      caching:
        enabled: true
        backend: redis

        # Semantic cache
        semantic:
          enabled: true
          similarity_threshold: 0.95  # 95% similar = cache hit
          embedding_model: all-MiniLM-L6-v2
          max_entries: 10000
          ttl: 3600

        # Cache what's expensive
        cache_embeddings: true
        cache_retrievals: true
        cache_generations: true
```

**Impact**:
- Cache hit rate: 60-80%
- Latency reduction: -90% on cache hit
- Cost reduction: -80% for cached queries

### Multi-Level Caching

```yaml
shops:
  infrastructure:
    config:
      caching:
        # L1: Memory cache (fastest)
        memory:
          enabled: true
          max_size: 1000
          ttl: 300                     # 5 minutes

        # L2: Redis cache (fast)
        redis:
          enabled: true
          url: "${REDIS_URL}"
          ttl: 3600                    # 1 hour

        # L3: Disk cache (large, persistent)
        disk:
          enabled: true
          path: /var/cache/sibyl
          max_size_gb: 10
          ttl: 86400                   # 24 hours
```

### Cache Warming

**Pre-populate cache with common queries**:
```yaml
pipelines:
  warm_cache:
    steps:
      - use: infrastructure.cache_warming
        config:
          queries:
            - "What is machine learning?"
            - "How does RAG work?"
            - "Explain neural networks"
          # ... top 100 queries
```

```bash
# Run cache warming on startup
sibyl pipeline run \
  --workspace config/workspaces/prod.yaml \
  --pipeline warm_cache
```

## Resource Management

### CPU Optimization

**1. Use async/await**:
```python
# Async execution allows CPU to handle other tasks
async def process_batch(documents):
    tasks = [embed_document(doc) for doc in documents]
    return await asyncio.gather(*tasks)
```

**2. Multiprocessing for CPU-bound tasks**:
```yaml
steps:
  - use: rag.embedding
    config:
      workers: 4                   # Use 4 processes
      batch_size: 32
```

**3. CPU affinity (production)**:
```bash
# Pin to specific CPUs
taskset -c 0-3 sibyl-mcp --workspace config/workspaces/prod.yaml
```

### Memory Optimization

**1. Limit batch sizes**:
```yaml
steps:
  - use: rag.chunking
    config:
      batch_size: 100              # Don't load everything at once

  - use: rag.embedding
    config:
      batch_size: 32
      clear_cache_after_batch: true
```

**2. Stream large results**:
```yaml
steps:
  - use: data.load_documents
    config:
      streaming: true              # Don't load all into memory
      chunk_size: 1000
```

**3. Garbage collection tuning**:
```python
# Python garbage collection tuning
import gc

# Reduce GC frequency for performance
gc.set_threshold(1000, 15, 15)  # Default: 700, 10, 10
```

### Network Optimization

**1. Connection pooling**:
```yaml
providers:
  llm:
    primary:
      kind: openai
      max_connections: 100         # Connection pool
      keep_alive: true
```

**2. Compression**:
```yaml
mcp:
  transport: http
  compression:
    enabled: true
    algorithm: gzip
    min_size: 1024                 # Compress if >1KB
```

**3. CDN for static assets** (if applicable):
```yaml
mcp:
  cdn:
    enabled: true
    provider: cloudflare
    cache_static: true
```

## Scaling Strategies

### Horizontal Scaling

**Load balancing**:
```yaml
# docker-compose.yml
services:
  sibyl:
    image: sibyl:latest
    deploy:
      replicas: 5                  # Run 5 instances
      resources:
        limits:
          cpus: '2'
          memory: 4G

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - sibyl
```

**Nginx load balancer**:
```nginx
upstream sibyl_backend {
    least_conn;                    # Route to least busy
    server sibyl-1:8000;
    server sibyl-2:8000;
    server sibyl-3:8000;
    server sibyl-4:8000;
    server sibyl-5:8000;
}

server {
    listen 80;

    location / {
        proxy_pass http://sibyl_backend;
        proxy_next_upstream error timeout;
        proxy_connect_timeout 5s;
    }
}
```

**Kubernetes scaling**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sibyl-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sibyl
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Vertical Scaling

**Increase resources**:
```yaml
# docker-compose.yml
services:
  sibyl:
    deploy:
      resources:
        limits:
          cpus: '8'                # Increase from 2
          memory: 16G              # Increase from 4G
```

**Kubernetes**:
```yaml
resources:
  requests:
    memory: "8Gi"
    cpu: "4000m"
  limits:
    memory: "16Gi"
    cpu: "8000m"
```

### Database Scaling

**Read replicas**:
```yaml
providers:
  vector_store:
    # Write to primary
    primary:
      kind: pgvector
      dsn: "postgresql://primary:5432/sibyl"

    # Read from replicas
    replicas:
      - dsn: "postgresql://replica-1:5432/sibyl"
      - dsn: "postgresql://replica-2:5432/sibyl"
      - dsn: "postgresql://replica-3:5432/sibyl"

    # Load balancing
    read_strategy: round_robin     # or random, least_loaded
```

**Partitioning**:
```sql
-- Partition by date
CREATE TABLE documents (
    id UUID,
    created_at TIMESTAMP,
    embedding vector(384),
    content TEXT
) PARTITION BY RANGE (created_at);

CREATE TABLE documents_2024_01 PARTITION OF documents
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE documents_2024_02 PARTITION OF documents
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
```

## Cost Optimization

### LLM Cost Reduction

**1. Use cheaper models**:
```yaml
providers:
  llm:
    # Use GPT-3.5 for simple queries
    simple:
      kind: openai
      model: gpt-3.5-turbo         # $0.002/1k vs $0.03/1k

    # Use GPT-4 only when needed
    complex:
      kind: openai
      model: gpt-4

# Route based on complexity
pipelines:
  adaptive_qa:
    steps:
      - use: infrastructure.query_classifier
        config:
          complexity_threshold: 0.7

      - use: ai_generation.generation
        config:
          provider: |
            {% if complexity < 0.7 %}simple{% else %}complex{% endif %}
```

**2. Reduce tokens**:
```yaml
steps:
  - use: ai_generation.generation
    config:
      max_tokens: 500              # Limit to 500
      stop_sequences: ["\n\n"]    # Stop early
```

**3. Enable caching**:
```yaml
shops:
  infrastructure:
    config:
      caching:
        enabled: true
        cache_generations: true
        ttl: 3600
```

**Impact**:
- Model switching: -90% cost
- Token reduction: -50% cost
- Caching (70% hit rate): -70% cost
- **Combined**: -97% cost

### Infrastructure Cost Reduction

**1. Right-size resources**:
```bash
# Monitor actual usage
kubectl top nodes
kubectl top pods

# Reduce to actual needs
resources:
  requests:
    memory: "4Gi"    # Was 8Gi, only using 3Gi
    cpu: "2000m"     # Was 4000m, only using 1500m
```

**2. Use spot/preemptible instances**:
```yaml
# Kubernetes node pool
nodeSelector:
  cloud.google.com/gke-preemptible: "true"
  # 70% cheaper than regular instances
```

**3. Auto-scaling**:
```yaml
# Scale down during off-hours
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 1     # Scale down to 1 at night
  maxReplicas: 20    # Scale up during peak
```

## Performance Benchmarking

### Load Testing

```bash
# Install k6
brew install k6

# Load test script
cat > load-test.js << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 10 },   // Ramp up to 10 users
    { duration: '3m', target: 10 },   // Stay at 10 users
    { duration: '1m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '1m', target: 0 },    // Ramp down to 0
  ],
};

export default function () {
  const url = 'http://localhost:8000/mcp/tools/search_documents';
  const payload = JSON.stringify({
    query: 'What is machine learning?',
  });
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': __ENV.API_KEY,
    },
  };

  const res = http.post(url, payload, params);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 2s': (r) => r.timings.duration < 2000,
  });

  sleep(1);
}
EOF

# Run test
k6 run load-test.js
```

### Profiling

**Python profiling**:
```python
# Profile pipeline execution
import cProfile
import pstats

def profile_pipeline():
    profiler = cProfile.Profile()
    profiler.enable()

    # Run pipeline
    result = await pipeline.execute(input_data, config)

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 slowest functions
```

**Memory profiling**:
```python
from memory_profiler import profile

@profile
def process_documents(documents):
    # Your code here
    pass
```

## Performance Checklist

- [ ] Chunk size optimized (512 tokens recommended)
- [ ] Embedding batch size configured (32-64)
- [ ] Vector index optimized (HNSW for speed)
- [ ] Top_k reduced to minimum needed (5-10)
- [ ] LLM model appropriate for complexity
- [ ] Max_tokens limited to necessary length
- [ ] Caching enabled (Redis recommended)
- [ ] Connection pooling configured
- [ ] Database indexes created
- [ ] Async operations used where possible
- [ ] Resource limits set appropriately
- [ ] Horizontal scaling configured
- [ ] Load balancing enabled
- [ ] Monitoring and alerting set up
- [ ] Cost tracking enabled

## Further Reading

- **[Observability Guide](observability.md)** - Performance monitoring
- **[Deployment Guide](deployment.md)** - Scalable deployment
- **[Troubleshooting](troubleshooting.md)** - Performance issues
- **[RAG Pipeline Guide](../techniques/rag-pipeline.md)** - RAG optimization

---

**Previous**: [Security Guide](security.md) | **Next**: [Examples Overview](../examples/overview.md)

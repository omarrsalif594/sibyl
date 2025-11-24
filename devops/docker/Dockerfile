# =============================================================================
# Sibyl MCP Server - Production Dockerfile
# =============================================================================
# Multi-stage build with security hardening:
# - Non-root user with fixed UID/GID
# - Read-only root filesystem support
# - Minimal attack surface (distroless-style)
# - SBOM generation support
# - Health checks for all server modes
# - Proper signal handling
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=dev

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app user with fixed UID/GID (for consistent volume ownership)
RUN groupadd -g 10001 appuser && \
    useradd -m -u 10001 -g appuser appuser

# Set working directory
WORKDIR /build

# Copy dependency files first (layer caching)
COPY requirements.txt ./
COPY pyproject.toml ./
COPY README.md ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Install REST API dependencies (optional)
COPY rest_api_requirements.txt ./
RUN pip install --no-cache-dir -r rest_api_requirements.txt || true

# Copy application code
COPY --chown=appuser:appuser . .

# Install the application
RUN pip install --no-cache-dir -e .

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Build arguments (repeated for this stage)
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=dev

# Metadata labels (OCI standard)
LABEL org.opencontainers.image.title="Sibyl MCP Server" \
      org.opencontainers.image.description="Production-grade Sibyl AI Assistant Platform with MCP protocol support" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="Sibyl Project" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.authors="Sibyl Team" \
      maintainer="team@sibyl.dev"

# Runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    # Server mode (stdio|http|rest)
    SIBYL_SERVER_MODE=http \
    # MCP HTTP Server defaults
    MCP_HTTP_HOST=0.0.0.0 \
    MCP_HTTP_PORT=8770 \
    # REST API Server defaults
    SIBYL_HOST=0.0.0.0 \
    SIBYL_PORT=8000 \
    # Common settings
    SIBYL_LOG_LEVEL=INFO \
    SIBYL_METRICS_PORT=9090 \
    SIBYL_ENABLE_METRICS=true \
    # DuckDB defaults
    DUCKDB_MEMORY_LIMIT=2GB \
    MCP_DUCKDB_PATH=/var/lib/sibyl/state/sibyl_state.duckdb \
    # Workspace configuration
    SIBYL_WORKSPACE_FILE=/etc/sibyl/workspaces/default.yaml \
    # Observability defaults
    SIBYL_LOG_FILE=/var/log/sibyl/sibyl.log \
    SIBYL_ENABLE_HTTP_SERVER=true

# Install runtime dependencies only (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Required for health checks
    curl \
    # Required for Git operations in Sibyl
    git \
    ca-certificates \
    # Required for graceful shutdown
    tini \
    && rm -rf /var/lib/apt/lists/*

# Create app user with same UID/GID as builder
RUN groupadd -g 10001 appuser && \
    useradd -m -u 10001 -g appuser -s /sbin/nologin appuser

# Create required directories with proper ownership
RUN mkdir -p /var/lib/sibyl/state \
             /var/log/sibyl \
             /var/cache/sibyl \
             /tmp/sibyl \
             /etc/sibyl/workspaces && \
    chown -R appuser:appuser /var/lib/sibyl \
                             /var/log/sibyl \
                             /var/cache/sibyl \
                             /tmp/sibyl \
                             /etc/sibyl

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set working directory
WORKDIR /app

# Copy application code with proper ownership
COPY --from=builder --chown=appuser:appuser /build/sibyl ./sibyl
COPY --from=builder --chown=appuser:appuser /build/config ./config
COPY --from=builder --chown=appuser:appuser /build/pyproject.toml ./
COPY --from=builder --chown=appuser:appuser /build/README.md ./

# Copy health check script
COPY --chown=appuser:appuser devops/scripts/health-check.sh /usr/local/bin/health-check.sh
RUN chmod +x /usr/local/bin/health-check.sh || true

# Switch to non-root user
USER appuser:appuser

# Expose ports
EXPOSE 8770 8000 9090

# Health check - smart detection of server mode
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD /usr/local/bin/health-check.sh || \
        curl -f http://localhost:${MCP_HTTP_PORT:-8770}/health 2>/dev/null || \
        curl -f http://localhost:${SIBYL_PORT:-8000}/health 2>/dev/null || \
        curl -f http://localhost:${SIBYL_METRICS_PORT:-9090}/metrics 2>/dev/null || \
        exit 1

# Volume mount points (documented, not created as VOLUME to allow read-only)
# /var/lib/sibyl/state - DuckDB state database
# /var/log/sibyl - Application logs
# /var/cache/sibyl - DuckDB cache
# /etc/sibyl/workspaces - Workspace YAML configurations
# /run/secrets - Docker secrets (API keys)

# Use tini for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command - start MCP HTTP server
# Override with environment variable SIBYL_SERVER_MODE or docker command
CMD ["sh", "-c", "\
    case \"${SIBYL_SERVER_MODE}\" in \
        stdio) \
            echo 'Starting Sibyl MCP Server in stdio mode...'; \
            exec python -m sibyl.server.mcp_server;; \
        http) \
            echo 'Starting Sibyl MCP HTTP Server on port ${MCP_HTTP_PORT}...'; \
            exec python -m sibyl.server.http_server;; \
        rest) \
            echo 'Starting Sibyl REST API Server on port ${SIBYL_PORT}...'; \
            exec python -m sibyl.server.rest_api;; \
        *) \
            echo 'Invalid SIBYL_SERVER_MODE: ${SIBYL_SERVER_MODE}'; \
            echo 'Valid modes: stdio, http, rest'; \
            exit 1;; \
    esac"]

# -----------------------------------------------------------------------------
# Stage 3: Development (with additional tools)
# -----------------------------------------------------------------------------
FROM runtime AS development

# Switch back to root for package installation
USER root

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    nano \
    less \
    procps \
    net-tools \
    iputils-ping \
    htop \
    strace \
    lsof \
    tcpdump \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Python development dependencies
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt 2>/dev/null || \
    pip install --no-cache-dir \
        pytest \
        pytest-asyncio \
        pytest-cov \
        pytest-timeout \
        mypy \
        ruff \
        black \
        ipython \
        ipdb \
        pytest-xdist 2>/dev/null || true

# Install pre-commit for local development
RUN pip install --no-cache-dir pre-commit || true

# Switch back to appuser
USER appuser:appuser

# Development overrides
ENV SIBYL_LOG_LEVEL=DEBUG \
    SIBYL_ENABLE_METRICS=true \
    PYTHONPATH=/app:$PYTHONPATH

# Development mode uses file-based logging with more verbosity
CMD ["sh", "-c", "\
    echo 'Starting Sibyl in DEVELOPMENT mode...'; \
    echo 'Server mode: ${SIBYL_SERVER_MODE}'; \
    echo 'Workspace: ${SIBYL_WORKSPACE_FILE}'; \
    case \"${SIBYL_SERVER_MODE}\" in \
        stdio) \
            exec python -m sibyl.server.mcp_server;; \
        http) \
            exec python -m sibyl.server.http_server;; \
        rest) \
            exec uvicorn sibyl.server.rest_api:app --host ${SIBYL_HOST} --port ${SIBYL_PORT} --reload;; \
        *) \
            exec python -m sibyl.server.http_server;; \
    esac"]

# Note: In development, mount source code as volume:
# docker run -v $(pwd):/app --target development ...

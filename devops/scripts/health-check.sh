#!/usr/bin/env bash
# =============================================================================
# Health Check Script for Sibyl Services
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Detect server mode from environment
SERVER_MODE="${SIBYL_SERVER_MODE:-http}"
MCP_HTTP_PORT="${MCP_HTTP_PORT:-8770}"
SIBYL_PORT="${SIBYL_PORT:-8000}"
SIBYL_METRICS_PORT="${SIBYL_METRICS_PORT:-9090}"

# Function to check HTTP endpoint
check_http() {
    local url=$1
    local name=$2

    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name is healthy"
        return 0
    else
        echo -e "${RED}✗${NC} $name is not responding"
        return 1
    fi
}

# Function to check Docker service health
check_docker_health() {
    local service=$1
    local name=$2

    if docker compose ps "$service" 2>/dev/null | grep -q "healthy"; then
        echo -e "${GREEN}✓${NC} $name is healthy (Docker)"
        return 0
    elif docker compose ps "$service" 2>/dev/null | grep -q "Up"; then
        echo -e "${YELLOW}⚠${NC} $name is running but health status unknown"
        return 0
    else
        echo -e "${RED}✗${NC} $name is not running"
        return 1
    fi
}

echo "Sibyl Health Check"
echo "=================="
echo ""

# Check based on server mode
case "$SERVER_MODE" in
    http)
        check_http "http://localhost:$MCP_HTTP_PORT/health" "MCP HTTP Server" || exit 1
        check_http "http://localhost:$SIBYL_METRICS_PORT/metrics" "Prometheus Metrics" || true
        ;;
    rest)
        check_http "http://localhost:$SIBYL_PORT/health" "REST API Server" || exit 1
        check_http "http://localhost:$SIBYL_METRICS_PORT/metrics" "Prometheus Metrics" || true
        ;;
    stdio)
        echo -e "${YELLOW}ℹ${NC} Server mode is 'stdio' - HTTP health checks not available"
        echo -e "${YELLOW}ℹ${NC} Check Docker container health instead"
        ;;
    *)
        # Try all endpoints
        check_http "http://localhost:$MCP_HTTP_PORT/health" "MCP HTTP Server" || \
        check_http "http://localhost:$SIBYL_PORT/health" "REST API Server" || \
        check_http "http://localhost:$SIBYL_METRICS_PORT/metrics" "Prometheus Metrics" || \
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Health check passed!${NC}"
exit 0

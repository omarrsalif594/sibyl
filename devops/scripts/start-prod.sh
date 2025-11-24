#!/usr/bin/env bash
# =============================================================================
# Start Sibyl Production Environment
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$SCRIPT_DIR/../docker"

echo -e "${GREEN}Starting Sibyl Production Environment...${NC}"

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check if docker compose is available
if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not available${NC}"
    exit 1
fi

# Navigate to docker directory
cd "$DOCKER_DIR"

# Check if .env.prod exists
if [ ! -f ".env.prod" ]; then
    echo -e "${RED}Error: .env.prod not found!${NC}"
    echo -e "${YELLOW}Please create .env.prod from .env.prod.example and configure it for production.${NC}"
    exit 1
fi

# Check if API keys are configured
if [ ! -f ".secrets/api_keys.txt" ]; then
    echo -e "${RED}Error: .secrets/api_keys.txt not found!${NC}"
    echo -e "${YELLOW}Please create API keys file from .secrets/api_keys.txt.template${NC}"
    exit 1
fi

# Load production environment
export $(cat .env.prod | grep -v '^#' | xargs)

# Parse command line arguments
WITH_OBSERVABILITY=true  # Observability is recommended for production
WITH_TRACING=false
SKIP_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-observability)
            WITH_OBSERVABILITY=false
            shift
            ;;
        --tracing|-t)
            WITH_TRACING=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-observability    Disable observability stack (not recommended)"
            echo "  -t, --tracing         Enable distributed tracing (Jaeger)"
            echo "  --skip-build          Skip building Docker images"
            echo "  -h, --help            Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Build profiles string
PROFILES="--profile prod"
if [ "$WITH_OBSERVABILITY" = true ]; then
    PROFILES="$PROFILES --profile observability"
fi
if [ "$WITH_TRACING" = true ]; then
    PROFILES="$PROFILES --profile tracing"
fi

# Production checks
echo -e "${YELLOW}Pre-flight checks...${NC}"

# Check Grafana password
if grep -q "GRAFANA_PASSWORD=admin" .env.prod; then
    echo -e "${YELLOW}Warning: Grafana password is still set to default 'admin'${NC}"
    echo -e "${YELLOW}Please change it in .env.prod for production!${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Build images (unless skipped)
if [ "$SKIP_BUILD" = false ]; then
    echo -e "${GREEN}Building production Docker images...${NC}"
    docker compose $PROFILES build --no-cache
fi

# Start services in detached mode
echo -e "${GREEN}Starting production services...${NC}"
docker compose $PROFILES up -d

# Wait for services to be healthy
echo -e "${GREEN}Waiting for services to be healthy...${NC}"
sleep 5

# Check health
if docker compose ps | grep -q "unhealthy"; then
    echo -e "${RED}Warning: Some services are unhealthy!${NC}"
    docker compose ps
else
    echo -e "${GREEN}All services are healthy!${NC}"
fi

echo ""
echo -e "${GREEN}Production deployment complete!${NC}"
echo ""
echo "Access Sibyl (via Nginx):"
echo "  - HTTP:        http://localhost"
echo "  - MCP API:     http://localhost/mcp/"
echo "  - REST API:    http://localhost/api/"
echo "  - Health:      http://localhost/health"

if [ "$WITH_OBSERVABILITY" = true ]; then
    echo ""
    echo "Observability Stack:"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Grafana:    http://localhost:3000 (admin/***)"
    echo "  - Loki:       http://localhost:3100"
fi

if [ "$WITH_TRACING" = true ]; then
    echo ""
    echo "Distributed Tracing:"
    echo "  - Jaeger UI:  http://localhost:16686"
fi

echo ""
echo "Management commands:"
echo "  View logs:    docker compose $PROFILES logs -f"
echo "  Stop:         docker compose --profile prod down"
echo "  Restart:      docker compose $PROFILES restart"
echo "  Health:       $SCRIPT_DIR/health-check.sh"
echo ""
echo -e "${YELLOW}Tip: Monitor logs with: ./logs.sh${NC}"

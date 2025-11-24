#!/usr/bin/env bash
# =============================================================================
# Start Sibyl Development Environment
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

echo -e "${GREEN}Starting Sibyl Development Environment...${NC}"

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

# Check if .env.dev exists, otherwise use .env.dev.example
if [ ! -f ".env.dev" ]; then
    if [ -f ".env.dev.example" ]; then
        echo -e "${YELLOW}Warning: .env.dev not found. Creating from .env.dev.example...${NC}"
        cp .env.dev.example .env.dev
        echo -e "${YELLOW}Please edit .env.dev and add your API keys!${NC}"
    else
        echo -e "${RED}Error: Neither .env.dev nor .env.dev.example found${NC}"
        exit 1
    fi
fi

# Load development environment
export $(cat .env.dev | grep -v '^#' | xargs)

# Parse command line arguments
WITH_OBSERVABILITY=false
DETACHED=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --observability|-o)
            WITH_OBSERVABILITY=true
            shift
            ;;
        --detach|-d)
            DETACHED=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -o, --observability    Start with observability stack (Prometheus, Grafana, Loki)"
            echo "  -d, --detach          Run in detached mode (background)"
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
PROFILES="--profile dev"
if [ "$WITH_OBSERVABILITY" = true ]; then
    PROFILES="$PROFILES --profile observability"
    echo -e "${GREEN}Starting with observability stack...${NC}"
fi

# Build compose command
COMPOSE_CMD="docker compose $PROFILES up"
if [ "$DETACHED" = true ]; then
    COMPOSE_CMD="$COMPOSE_CMD -d"
fi

# Build images first
echo -e "${GREEN}Building Docker images...${NC}"
docker compose $PROFILES build

# Start services
echo -e "${GREEN}Starting services...${NC}"
$COMPOSE_CMD

# If running in detached mode, show status
if [ "$DETACHED" = true ]; then
    echo ""
    echo -e "${GREEN}Services started successfully!${NC}"
    echo ""
    echo "Access Sibyl:"
    echo "  - MCP HTTP: http://localhost:8770"
    echo "  - REST API: http://localhost:8000"
    echo "  - Metrics:  http://localhost:9090"

    if [ "$WITH_OBSERVABILITY" = true ]; then
        echo ""
        echo "Observability Stack:"
        echo "  - Prometheus: http://localhost:9091"
        echo "  - Grafana:    http://localhost:3001 (admin/admin)"
        echo "  - Loki:       http://localhost:3101"
    fi

    echo ""
    echo "View logs:"
    echo "  docker compose logs -f"
    echo ""
    echo "Stop services:"
    echo "  docker compose --profile dev down"
fi

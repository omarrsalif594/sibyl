#!/usr/bin/env bash
# =============================================================================
# Update Sibyl Docker Images
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$SCRIPT_DIR/../docker"

echo -e "${GREEN}Sibyl Docker Update${NC}"
echo "==================="
echo ""

# Parse arguments
MODE="dev"
NO_CACHE=false
RESTART=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --prod)
            MODE="prod"
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --no-restart)
            RESTART=false
            shift
            ;;
        --help|-h)
            cat << EOF
Usage: $0 [OPTIONS]

Update Sibyl Docker images and restart services.

OPTIONS:
    --prod              Update production environment (default: dev)
    --no-cache          Build images without cache
    --no-restart        Don't restart services after update
    -h, --help          Show this help message

EXAMPLES:
    # Update development environment
    $0

    # Update production environment
    $0 --prod

    # Force rebuild without cache
    $0 --no-cache

EOF
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

cd "$DOCKER_DIR"

# Determine which profile to use
if [ "$MODE" = "prod" ]; then
    PROFILE="--profile prod --profile observability"
    ENV_FILE=".env.prod"
else
    PROFILE="--profile dev"
    ENV_FILE=".env.dev"
fi

echo -e "${GREEN}Mode: $MODE${NC}"
echo -e "${GREEN}Profile: $PROFILE${NC}"
echo ""

# Load environment
if [ -f "$ENV_FILE" ]; then
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
fi

# Pull latest base images
echo -e "${GREEN}Step 1: Pulling latest base images...${NC}"
docker compose $PROFILE pull || true

# Build application images
echo ""
echo -e "${GREEN}Step 2: Building application images...${NC}"
BUILD_CMD="docker compose $PROFILE build"
if [ "$NO_CACHE" = true ]; then
    BUILD_CMD="$BUILD_CMD --no-cache"
fi

if ! $BUILD_CMD; then
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi

# Restart services if requested
if [ "$RESTART" = true ]; then
    echo ""
    echo -e "${GREEN}Step 3: Restarting services...${NC}"

    # Check if services are running
    if docker compose ps | grep -q "Up"; then
        echo "  Stopping current services..."
        docker compose $PROFILE down

        echo "  Starting updated services..."
        docker compose $PROFILE up -d

        # Wait for services to be healthy
        echo "  Waiting for services to be healthy..."
        sleep 5

        # Check health
        if docker compose ps | grep -q "unhealthy"; then
            echo -e "${YELLOW}Warning: Some services are unhealthy${NC}"
            docker compose ps
        else
            echo -e "${GREEN}All services are healthy!${NC}"
        fi
    else
        echo "  No running services to restart"
        echo -e "${YELLOW}Tip: Start services with: ./start-$MODE.sh${NC}"
    fi
fi

# Show image sizes
echo ""
echo -e "${GREEN}Updated Images:${NC}"
docker images | grep -E "sibyl|REPOSITORY" || true

echo ""
echo -e "${GREEN}Update completed!${NC}"

if [ "$MODE" = "prod" ]; then
    echo ""
    echo -e "${YELLOW}Production environment updated.${NC}"
    echo -e "${YELLOW}Please verify functionality before serving traffic.${NC}"
fi

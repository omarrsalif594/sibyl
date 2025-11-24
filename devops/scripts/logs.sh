#!/usr/bin/env bash
# =============================================================================
# View Sibyl Logs
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

# Default options
SERVICE=""
FOLLOW=false
TAIL_LINES=100
ALL_SERVICES=false

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS] [SERVICE]

View logs from Sibyl Docker services.

OPTIONS:
    -f, --follow            Follow log output (like tail -f)
    -n, --tail LINES        Number of lines to show (default: 100)
    -a, --all               Show logs from all services
    -h, --help              Show this help message

SERVICES:
    sibyl-dev               Development Sibyl server
    sibyl-prod              Production Sibyl server
    nginx                   Nginx reverse proxy
    prometheus              Prometheus metrics
    grafana                 Grafana dashboards
    loki                    Loki log aggregation
    fluent-bit              Fluent Bit log forwarder
    jaeger                  Jaeger tracing
    backup                  Backup service

EXAMPLES:
    # View last 100 lines from sibyl-prod
    $0 sibyl-prod

    # Follow logs from sibyl-dev
    $0 -f sibyl-dev

    # Show last 500 lines from all services
    $0 -a -n 500

    # Follow all logs
    $0 -f -a

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -n|--tail)
            TAIL_LINES="$2"
            shift 2
            ;;
        -a|--all)
            ALL_SERVICES=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
        *)
            SERVICE="$1"
            shift
            ;;
    esac
done

# Navigate to docker directory
cd "$DOCKER_DIR"

# Build compose command
COMPOSE_CMD="docker compose logs"

if [ "$FOLLOW" = true ]; then
    COMPOSE_CMD="$COMPOSE_CMD -f"
fi

COMPOSE_CMD="$COMPOSE_CMD --tail=$TAIL_LINES"

if [ "$ALL_SERVICES" = true ]; then
    echo -e "${GREEN}Showing logs from all services...${NC}"
    echo ""
    $COMPOSE_CMD
elif [ -n "$SERVICE" ]; then
    # Check if service exists
    if ! docker compose ps "$SERVICE" > /dev/null 2>&1; then
        echo -e "${RED}Error: Service '$SERVICE' not found${NC}"
        echo ""
        echo "Available services:"
        docker compose ps --services
        exit 1
    fi

    echo -e "${GREEN}Showing logs from $SERVICE...${NC}"
    echo ""
    $COMPOSE_CMD "$SERVICE"
else
    echo -e "${YELLOW}No service specified. Showing logs from all running services.${NC}"
    echo -e "${YELLOW}Tip: Use -h to see available options.${NC}"
    echo ""
    $COMPOSE_CMD
fi

#!/usr/bin/env bash
# =============================================================================
# Cleanup Docker Resources for Sibyl
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

echo -e "${GREEN}Sibyl Docker Cleanup${NC}"
echo "===================="
echo ""

# Parse arguments
DEEP_CLEAN=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --deep)
            DEEP_CLEAN=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            cat << EOF
Usage: $0 [OPTIONS]

Cleanup Docker resources for Sibyl.

OPTIONS:
    --deep              Deep clean (remove volumes and all unused resources)
    --dry-run           Show what would be removed without actually removing
    -h, --help          Show this help message

EXAMPLES:
    # Standard cleanup (remove stopped containers, dangling images)
    $0

    # Deep clean (WARNING: removes volumes and all unused resources)
    $0 --deep

    # Dry run to see what would be removed
    $0 --dry-run

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

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN MODE - Nothing will be removed${NC}"
    echo ""
fi

# Stop running containers
echo -e "${GREEN}Step 1: Stopping Sibyl containers...${NC}"
if [ "$DRY_RUN" = false ]; then
    docker compose down || true
else
    echo "  Would stop: docker compose down"
fi

# Remove stopped containers
echo ""
echo -e "${GREEN}Step 2: Removing stopped containers...${NC}"
STOPPED_CONTAINERS=$(docker ps -a -q -f "name=sibyl" 2>/dev/null || true)
if [ -n "$STOPPED_CONTAINERS" ]; then
    if [ "$DRY_RUN" = false ]; then
        docker rm $STOPPED_CONTAINERS
        echo "  Removed $(echo $STOPPED_CONTAINERS | wc -w) containers"
    else
        echo "  Would remove $(echo $STOPPED_CONTAINERS | wc -w) containers"
    fi
else
    echo "  No stopped containers to remove"
fi

# Remove dangling images
echo ""
echo -e "${GREEN}Step 3: Removing dangling images...${NC}"
DANGLING_IMAGES=$(docker images -f "dangling=true" -q 2>/dev/null || true)
if [ -n "$DANGLING_IMAGES" ]; then
    if [ "$DRY_RUN" = false ]; then
        docker rmi $DANGLING_IMAGES
        echo "  Removed $(echo $DANGLING_IMAGES | wc -w) images"
    else
        echo "  Would remove $(echo $DANGLING_IMAGES | wc -w) images"
    fi
else
    echo "  No dangling images to remove"
fi

# Remove unused volumes (only in deep clean mode)
if [ "$DEEP_CLEAN" = true ]; then
    echo ""
    echo -e "${YELLOW}Step 4: Removing unused volumes (DEEP CLEAN)...${NC}"
    echo -e "${RED}WARNING: This will remove all unused Docker volumes!${NC}"

    if [ "$DRY_RUN" = false ]; then
        read -p "Are you sure? (yes/no): " CONFIRM
        if [ "$CONFIRM" = "yes" ]; then
            docker volume prune -f
        else
            echo "  Skipped volume cleanup"
        fi
    else
        UNUSED_VOLUMES=$(docker volume ls -qf dangling=true 2>/dev/null || true)
        if [ -n "$UNUSED_VOLUMES" ]; then
            echo "  Would remove $(echo $UNUSED_VOLUMES | wc -w) volumes"
        else
            echo "  No unused volumes to remove"
        fi
    fi
fi

# Remove build cache (only in deep clean mode)
if [ "$DEEP_CLEAN" = true ]; then
    echo ""
    echo -e "${YELLOW}Step 5: Removing build cache (DEEP CLEAN)...${NC}"
    if [ "$DRY_RUN" = false ]; then
        docker builder prune -f
    else
        echo "  Would remove Docker build cache"
    fi
fi

# System prune (only in deep clean mode)
if [ "$DEEP_CLEAN" = true ]; then
    echo ""
    echo -e "${YELLOW}Step 6: System prune (DEEP CLEAN)...${NC}"
    if [ "$DRY_RUN" = false ]; then
        docker system prune -f
    else
        echo "  Would run docker system prune"
    fi
fi

# Show disk space
echo ""
echo -e "${GREEN}Docker Disk Usage:${NC}"
docker system df

echo ""
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}Dry run completed. No changes were made.${NC}"
else
    echo -e "${GREEN}Cleanup completed!${NC}"
fi

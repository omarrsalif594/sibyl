#!/usr/bin/env bash
# =============================================================================
# Rotate Sibyl Application Logs
# =============================================================================
# Note: Docker already handles container log rotation via logging driver config.
# This script rotates application logs stored in volumes.
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
MAX_SIZE_MB="${MAX_SIZE_MB:-100}"
MAX_AGE_DAYS="${MAX_AGE_DAYS:-30}"
COMPRESS_OLD_LOGS=true

echo -e "${GREEN}Sibyl Log Rotation${NC}"
echo "=================="
echo ""

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$SCRIPT_DIR/../docker"

cd "$DOCKER_DIR"

# Function to rotate logs in a volume
rotate_volume_logs() {
    local VOLUME_NAME=$1
    local LOG_DIR=$2

    echo -e "${GREEN}Checking logs in volume: $VOLUME_NAME${NC}"

    # Use a temporary container to access the volume
    docker run --rm \
        -v "$VOLUME_NAME:$LOG_DIR:rw" \
        alpine:latest \
        sh -c "
            cd $LOG_DIR || exit 0
            ROTATED=0

            # Find and rotate large log files
            find . -type f -name '*.log' | while read -r logfile; do
                SIZE_MB=\$(du -m \"\$logfile\" | cut -f1)

                if [ \"\$SIZE_MB\" -gt $MAX_SIZE_MB ]; then
                    echo \"  Rotating: \$logfile (\${SIZE_MB}MB)\"
                    TIMESTAMP=\$(date +%Y%m%d_%H%M%S)
                    mv \"\$logfile\" \"\${logfile}.\${TIMESTAMP}\"

                    if [ \"$COMPRESS_OLD_LOGS\" = true ]; then
                        gzip \"\${logfile}.\${TIMESTAMP}\"
                    fi

                    # Create new empty log file
                    touch \"\$logfile\"
                    ROTATED=\$((ROTATED + 1))
                fi
            done

            # Remove old compressed logs
            find . -type f \( -name '*.log.*.gz' -o -name '*.log.[0-9]*' \) -mtime +$MAX_AGE_DAYS -delete

            # Count remaining logs
            LOG_COUNT=\$(find . -type f -name '*.log*' | wc -l)
            TOTAL_SIZE=\$(du -sh . | cut -f1)

            echo \"  Logs: \$LOG_COUNT files, \$TOTAL_SIZE total\"
        " 2>/dev/null || echo "  No logs found"
}

# Rotate logs in sibyl_logs volume
rotate_volume_logs "sibyl_logs" "/var/log/sibyl"

# Clean up Docker container logs (if they get too large)
echo ""
echo -e "${GREEN}Checking Docker container logs...${NC}"
LARGE_CONTAINERS=$(docker ps -a --format '{{.Names}}' | grep sibyl || true)

if [ -n "$LARGE_CONTAINERS" ]; then
    for CONTAINER in $LARGE_CONTAINERS; do
        # Get log file size (if accessible)
        LOG_FILE=$(docker inspect --format='{{.LogPath}}' "$CONTAINER" 2>/dev/null || echo "")

        if [ -n "$LOG_FILE" ] && [ -f "$LOG_FILE" ]; then
            SIZE_MB=$(du -m "$LOG_FILE" | cut -f1)

            if [ "$SIZE_MB" -gt "$MAX_SIZE_MB" ]; then
                echo -e "${YELLOW}  Warning: $CONTAINER logs are ${SIZE_MB}MB${NC}"
                echo "    Log file: $LOG_FILE"
                echo "    Consider restarting container or adjusting log rotation settings"
            fi
        fi
    done
else
    echo "  No Sibyl containers found"
fi

echo ""
echo -e "${GREEN}Log rotation completed!${NC}"
echo ""
echo "Configuration:"
echo "  Max log size: ${MAX_SIZE_MB}MB"
echo "  Max age: ${MAX_AGE_DAYS} days"
echo "  Compression: $COMPRESS_OLD_LOGS"
echo ""
echo -e "${YELLOW}Tip: Docker log rotation is configured in docker-compose.yml${NC}"

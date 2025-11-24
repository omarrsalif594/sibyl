#!/usr/bin/env bash
# =============================================================================
# Backup Sibyl DuckDB State
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
SOURCE_DIR="${SOURCE_DIR:-/source/state}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-30}"

echo -e "${GREEN}Sibyl State Backup${NC}"
echo "=================="
echo ""

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}Error: Source directory $SOURCE_DIR not found!${NC}"
    exit 1
fi

# Find all .duckdb files
DUCKDB_FILES=$(find "$SOURCE_DIR" -name "*.duckdb" 2>/dev/null || true)

if [ -z "$DUCKDB_FILES" ]; then
    echo -e "${YELLOW}Warning: No DuckDB files found in $SOURCE_DIR${NC}"
    exit 0
fi

# Backup each database
for DB_FILE in $DUCKDB_FILES; do
    DB_NAME=$(basename "$DB_FILE")
    BACKUP_FILE="$BACKUP_DIR/${DB_NAME%.duckdb}_${TIMESTAMP}.duckdb"

    echo -e "${GREEN}Backing up:${NC} $DB_NAME"

    # Copy the database file
    if cp "$DB_FILE" "$BACKUP_FILE"; then
        # Compress the backup
        gzip "$BACKUP_FILE"
        BACKUP_SIZE=$(du -h "$BACKUP_FILE.gz" | cut -f1)
        echo -e "${GREEN}✓${NC} Backup created: ${BACKUP_FILE}.gz (${BACKUP_SIZE})"
    else
        echo -e "${RED}✗${NC} Failed to backup $DB_NAME"
    fi
done

# Clean up old backups (older than RETENTION_DAYS)
echo ""
echo -e "${YELLOW}Cleaning up backups older than $RETENTION_DAYS days...${NC}"
OLD_BACKUPS=$(find "$BACKUP_DIR" -name "*.duckdb.gz" -mtime +$RETENTION_DAYS 2>/dev/null || true)

if [ -n "$OLD_BACKUPS" ]; then
    echo "$OLD_BACKUPS" | while read -r OLD_BACKUP; do
        echo -e "${YELLOW}Removing:${NC} $(basename "$OLD_BACKUP")"
        rm -f "$OLD_BACKUP"
    done
else
    echo -e "${GREEN}No old backups to clean up${NC}"
fi

# Show backup summary
echo ""
echo -e "${GREEN}Backup Summary:${NC}"
echo "---------------"
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "*.duckdb.gz" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "Total backups: $BACKUP_COUNT"
echo "Total size: $TOTAL_SIZE"
echo "Location: $BACKUP_DIR"

echo ""
echo -e "${GREEN}Backup completed successfully!${NC}"

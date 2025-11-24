#!/usr/bin/env bash
# =============================================================================
# Restore Sibyl DuckDB State from Backup
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
TARGET_DIR="${TARGET_DIR:-/var/lib/sibyl/state}"

echo -e "${GREEN}Sibyl State Restore${NC}"
echo "==================="
echo ""

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}Error: Backup directory $BACKUP_DIR not found!${NC}"
    exit 1
fi

# List available backups
echo "Available backups:"
echo "------------------"
BACKUPS=$(find "$BACKUP_DIR" -name "*.duckdb.gz" -type f | sort -r)

if [ -z "$BACKUPS" ]; then
    echo -e "${RED}No backups found in $BACKUP_DIR${NC}"
    exit 1
fi

# Display backups with numbers
i=1
declare -a BACKUP_ARRAY
while IFS= read -r backup; do
    BACKUP_ARRAY[$i]="$backup"
    BACKUP_NAME=$(basename "$backup")
    BACKUP_DATE=$(stat -c %y "$backup" 2>/dev/null | cut -d' ' -f1 || stat -f %Sm -t "%Y-%m-%d" "$backup")
    BACKUP_SIZE=$(du -h "$backup" | cut -f1)
    printf "%2d) %s (%s, %s)\n" $i "$BACKUP_NAME" "$BACKUP_DATE" "$BACKUP_SIZE"
    ((i++))
done <<< "$BACKUPS"

# Prompt for selection
echo ""
read -p "Select backup to restore (1-$((i-1))) or 'q' to quit: " SELECTION

if [ "$SELECTION" = "q" ] || [ "$SELECTION" = "Q" ]; then
    echo "Restore cancelled"
    exit 0
fi

# Validate selection
if ! [[ "$SELECTION" =~ ^[0-9]+$ ]] || [ "$SELECTION" -lt 1 ] || [ "$SELECTION" -ge $i ]; then
    echo -e "${RED}Invalid selection${NC}"
    exit 1
fi

SELECTED_BACKUP="${BACKUP_ARRAY[$SELECTION]}"
echo ""
echo -e "${YELLOW}Selected backup:${NC} $(basename "$SELECTED_BACKUP")"

# Confirm restore
echo -e "${RED}WARNING: This will overwrite the current database!${NC}"
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Extract and restore
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo ""
echo -e "${GREEN}Extracting backup...${NC}"
if ! gunzip -c "$SELECTED_BACKUP" > "$TEMP_DIR/restore.duckdb"; then
    echo -e "${RED}Failed to extract backup${NC}"
    exit 1
fi

# Determine target filename
BACKUP_BASENAME=$(basename "$SELECTED_BACKUP" .gz)
TARGET_FILE="$TARGET_DIR/${BACKUP_BASENAME%_*}.duckdb"

# Backup current database (if exists)
if [ -f "$TARGET_FILE" ]; then
    CURRENT_BACKUP="$TARGET_FILE.before_restore_$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}Backing up current database to:${NC} $(basename "$CURRENT_BACKUP")"
    cp "$TARGET_FILE" "$CURRENT_BACKUP"
fi

# Restore database
echo -e "${GREEN}Restoring database...${NC}"
if mv "$TEMP_DIR/restore.duckdb" "$TARGET_FILE"; then
    echo -e "${GREEN}✓${NC} Database restored successfully!"
    echo ""
    echo "Restored to: $TARGET_FILE"
    echo ""
    echo -e "${YELLOW}Note: You may need to restart Sibyl services for changes to take effect${NC}"
else
    echo -e "${RED}✗${NC} Failed to restore database"
    exit 1
fi

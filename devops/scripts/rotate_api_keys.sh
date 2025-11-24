#!/usr/bin/env bash
# =============================================================================
# API Key Rotation Script with Grace Period
# =============================================================================
# Rotates API keys with a grace period where both old and new keys are valid.
# This prevents downtime during key rotation.
#
# Rotation Process:
# 1. Generate new API key
# 2. Add new key to secrets (old + new both valid)
# 3. Grace period: Update clients to use new key
# 4. Remove old key after grace period
#
# Usage:
#   ./scripts/rotate_api_keys.sh [OPTIONS]
#
# Options:
#   --keys-file FILE    API keys file (default: /run/secrets/MCP_API_KEYS)
#   --grace-hours N     Grace period in hours (default: 24)
#   --add-key KEY       Add a specific key
#   --remove-old        Remove expired keys
#   --list              List current keys with ages
#   --dry-run           Show what would be done
#
# Examples:
#   ./scripts/rotate_api_keys.sh                    # Generate and add new key
#   ./scripts/rotate_api_keys.sh --grace-hours 48   # 48-hour grace period
#   ./scripts/rotate_api_keys.sh --list             # List keys with ages
#   ./scripts/rotate_api_keys.sh --remove-old       # Remove expired keys
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
KEYS_FILE="${MCP_API_KEYS_FILE:-/run/secrets/MCP_API_KEYS}"
GRACE_HOURS="${KEY_ROTATION_GRACE_HOURS:-24}"
DRY_RUN=false
ADD_KEY=""
REMOVE_OLD=false
LIST_KEYS=false

# Metadata file tracks key creation times
METADATA_FILE="${KEYS_FILE}.metadata"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

check_permissions() {
    if [ ! -w "$(dirname "$KEYS_FILE")" ]; then
        log_error "No write permission to $(dirname "$KEYS_FILE")"
        log_error "This script must be run with appropriate permissions"
        exit 1
    fi
}

generate_key() {
    # Generate 32-byte random key, base64 encoded
    openssl rand -base64 32 | tr -d '\n'
}

add_key_to_file() {
    local new_key="$1"
    local timestamp=$(date +%s)

    if [ "$DRY_RUN" = true ]; then
        log_debug "[DRY RUN] Would add key: ${new_key:0:8}... (created: $(date -d @$timestamp 2>/dev/null || date -r $timestamp 2>/dev/null))"
        return
    fi

    # Add key to keys file
    if [ -f "$KEYS_FILE" ]; then
        # Append to existing file
        echo "$new_key" >> "$KEYS_FILE"
    else
        # Create new file
        echo "$new_key" > "$KEYS_FILE"
        chmod 600 "$KEYS_FILE"
    fi

    # Update metadata
    if [ -f "$METADATA_FILE" ]; then
        echo "${new_key}:${timestamp}" >> "$METADATA_FILE"
    else
        echo "${new_key}:${timestamp}" > "$METADATA_FILE"
        chmod 600 "$METADATA_FILE"
    fi

    log_info "✓ Key added: ${new_key:0:8}... (created: $(date -d @$timestamp 2>/dev/null || date -r $timestamp 2>/dev/null))"
}

list_keys_with_ages() {
    if [ ! -f "$KEYS_FILE" ]; then
        log_warn "No keys file found: $KEYS_FILE"
        return
    fi

    log_info "Current API Keys:"
    log_info "================================================================================"
    printf "%-12s %-20s %-15s %s\n" "KEY PREFIX" "CREATED" "AGE" "STATUS"
    log_info "================================================================================"

    local now=$(date +%s)
    local grace_seconds=$((GRACE_HOURS * 3600))

    # Read keys
    while IFS= read -r key; do
        [ -z "$key" ] && continue

        local key_prefix="${key:0:8}..."
        local created_time="unknown"
        local age_str="unknown"
        local status="ACTIVE"

        # Try to find metadata
        if [ -f "$METADATA_FILE" ]; then
            local metadata=$(grep "^$key:" "$METADATA_FILE" || echo "")
            if [ -n "$metadata" ]; then
                local timestamp=$(echo "$metadata" | cut -d':' -f2)
                created_time=$(date -d @$timestamp 2>/dev/null || date -r $timestamp 2>/dev/null || echo "unknown")

                # Calculate age
                local age_seconds=$((now - timestamp))
                local age_hours=$((age_seconds / 3600))
                local age_days=$((age_hours / 24))

                if [ $age_days -gt 0 ]; then
                    age_str="${age_days}d ${age_hours}h"
                else
                    age_str="${age_hours}h"
                fi

                # Determine status
                if [ $age_seconds -gt $grace_seconds ]; then
                    status="EXPIRED (can be removed)"
                fi
            fi
        fi

        printf "%-12s %-20s %-15s %s\n" "$key_prefix" "$created_time" "$age_str" "$status"
    done < "$KEYS_FILE"

    log_info "================================================================================"
    log_info "Grace period: $GRACE_HOURS hours"
}

remove_expired_keys() {
    if [ ! -f "$KEYS_FILE" ] || [ ! -f "$METADATA_FILE" ]; then
        log_warn "No keys or metadata file found"
        return
    fi

    local now=$(date +%s)
    local grace_seconds=$((GRACE_HOURS * 3600))
    local removed_count=0

    log_info "Removing keys older than $GRACE_HOURS hours..."

    # Create temporary files
    local temp_keys=$(mktemp)
    local temp_metadata=$(mktemp)

    # Filter keys
    while IFS= read -r key; do
        [ -z "$key" ] && continue

        local should_keep=true

        # Check metadata
        if [ -f "$METADATA_FILE" ]; then
            local metadata=$(grep "^$key:" "$METADATA_FILE" || echo "")
            if [ -n "$metadata" ]; then
                local timestamp=$(echo "$metadata" | cut -d':' -f2)
                local age_seconds=$((now - timestamp))

                if [ $age_seconds -gt $grace_seconds ]; then
                    should_keep=false
                    ((removed_count++))

                    if [ "$DRY_RUN" = true ]; then
                        log_debug "[DRY RUN] Would remove: ${key:0:8}... (age: $((age_seconds / 3600))h)"
                    else
                        log_info "Removed expired key: ${key:0:8}... (age: $((age_seconds / 3600))h)"
                    fi
                fi
            fi
        fi

        # Keep key if not expired
        if [ "$should_keep" = true ]; then
            echo "$key" >> "$temp_keys"

            if [ -f "$METADATA_FILE" ]; then
                local metadata=$(grep "^$key:" "$METADATA_FILE" || echo "")
                [ -n "$metadata" ] && echo "$metadata" >> "$temp_metadata"
            fi
        fi
    done < "$KEYS_FILE"

    if [ $removed_count -eq 0 ]; then
        log_info "No expired keys to remove"
        rm -f "$temp_keys" "$temp_metadata"
        return
    fi

    if [ "$DRY_RUN" = false ]; then
        # Replace files
        mv "$temp_keys" "$KEYS_FILE"
        [ -f "$temp_metadata" ] && mv "$temp_metadata" "$METADATA_FILE"

        chmod 600 "$KEYS_FILE" "$METADATA_FILE" 2>/dev/null || true

        log_info "✓ Removed $removed_count expired key(s)"
    else
        rm -f "$temp_keys" "$temp_metadata"
        log_debug "[DRY RUN] Would remove $removed_count key(s)"
    fi
}

# -----------------------------------------------------------------------------
# Parse arguments
# -----------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case $1 in
        --keys-file)
            KEYS_FILE="$2"
            METADATA_FILE="${KEYS_FILE}.metadata"
            shift 2
            ;;
        --grace-hours)
            GRACE_HOURS="$2"
            shift 2
            ;;
        --add-key)
            ADD_KEY="$2"
            shift 2
            ;;
        --remove-old)
            REMOVE_OLD=true
            shift
            ;;
        --list)
            LIST_KEYS=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
log_info "==================================================================="
log_info "API Key Rotation Script"
log_info "==================================================================="
log_info "  Keys File: $KEYS_FILE"
log_info "  Grace Period: $GRACE_HOURS hours"
if [ "$DRY_RUN" = true ]; then
    log_warn "  DRY RUN MODE: No changes will be made"
fi
log_info "==================================================================="

# Check permissions
check_permissions

# Handle list command
if [ "$LIST_KEYS" = true ]; then
    list_keys_with_ages
    exit 0
fi

# Handle remove old keys
if [ "$REMOVE_OLD" = true ]; then
    remove_expired_keys
    exit 0
fi

# Handle add specific key
if [ -n "$ADD_KEY" ]; then
    log_info "Adding provided key..."
    add_key_to_file "$ADD_KEY"
    exit 0
fi

# Generate and add new key
log_info "Generating new API key..."
NEW_KEY=$(generate_key)

log_info "New key generated: ${NEW_KEY:0:8}..."
log_info ""
log_info "⚠️  IMPORTANT: Save this key securely!"
log_info "   Key: $NEW_KEY"
log_info ""

add_key_to_file "$NEW_KEY"

log_info "==================================================================="
log_info "✅ Key rotation initiated"
log_info ""
log_info "Next steps:"
log_info "  1. Update clients to use the new key: ${NEW_KEY:0:8}..."
log_info "  2. Test that clients can connect with the new key"
log_info "  3. Wait $GRACE_HOURS hours (grace period)"
log_info "  4. Remove old keys: ./scripts/rotate_api_keys.sh --remove-old"
log_info ""
log_info "During the grace period, both old and new keys are valid."
log_info "==================================================================="

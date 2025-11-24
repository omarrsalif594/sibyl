#!/bin/bash
# =============================================================================
# Import Smoke Test Runner
# =============================================================================
# Runs the import smoke test to verify all modules can be imported.
# Use this before AND after the reorganization to ensure no breakage.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================================================="
echo "MCP Server - Import Smoke Test"
echo "============================================================================="
echo ""

cd "$PROJECT_ROOT"

# Check if pytest is available
if command -v pytest &> /dev/null; then
    echo "🧪 Running import smoke test via pytest..."
    echo ""
    pytest tests/import_smoke_test.py -v --tb=short
    EXIT_CODE=$?
else
    echo "🐍 pytest not found, running test directly with Python..."
    echo ""
    python tests/import_smoke_test.py
    EXIT_CODE=$?
fi

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "============================================================================="
    echo "✅ Import Smoke Test PASSED"
    echo "============================================================================="
    echo ""
    echo "All modules imported successfully. Safe to proceed with migration."
else
    echo "============================================================================="
    echo "❌ Import Smoke Test FAILED"
    echo "============================================================================="
    echo ""
    echo "Fix import errors before proceeding with migration."
    echo ""
    echo "Common issues:"
    echo "  - Missing dependencies (check requirements.txt)"
    echo "  - Circular import dependencies"
    echo "  - Syntax errors in Python files"
    echo "  - Missing __init__.py files"
fi

echo ""
exit $EXIT_CODE

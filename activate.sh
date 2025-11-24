#!/bin/bash
# =============================================================================
# activate.sh - Quick Virtual Environment Activation
# =============================================================================
# Convenience script to activate the UV-managed virtual environment.
# =============================================================================

if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found."
    echo "Run ./setup.sh first to create the environment."
    exit 1
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "✅ Virtual environment activated!"
echo ""
echo "Python: $(python --version)"
echo "Location: $(which python)"
echo ""
echo "To deactivate: deactivate"

#!/bin/bash
# =============================================================================
# setup.sh - One-Command MCP Server Setup
# =============================================================================
# Sets up MCP server development environment with UV and pyenv.
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}❌ Error: $1${NC}" >&2
    exit 1
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# =============================================================================
# 1. Check Prerequisites
# =============================================================================
info "Checking prerequisites..."

# Check for pyenv
if ! command -v pyenv &> /dev/null; then
    error "pyenv not found. Install with: curl https://pyenv.run | bash"
fi
success "pyenv installed"

# Check for uv
if ! command -v uv &> /dev/null; then
    error "uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi
success "uv installed"

# =============================================================================
# 2. Setup Python Version
# =============================================================================
info "Setting up Python 3.11.0..."

# Install Python 3.11.0 if not already installed
if ! pyenv versions | grep -q "3.11.0"; then
    info "Installing Python 3.11.0 via pyenv..."
    pyenv install 3.11.0
fi

# Set local Python version
pyenv local 3.11.0
success "Python 3.11.0 configured"

# Verify Python version
python_version=$(python --version | cut -d' ' -f2)
if [[ ! "$python_version" =~ ^3\.11\.0 ]]; then
    error "Python version mismatch. Expected 3.11.0, got $python_version"
fi

# =============================================================================
# 3. Create Virtual Environment with UV
# =============================================================================
info "Creating virtual environment with UV..."

# Remove existing venv if present
if [ -d ".venv" ]; then
    info "Removing existing .venv..."
    rm -rf .venv
fi

# Create venv
uv venv --python 3.11.0
success "Virtual environment created"

# =============================================================================
# 4. Install Dependencies
# =============================================================================
info "Installing dependencies with UV..."

# Activate venv
source .venv/bin/activate

# Install all dependencies including optional extras
uv sync --all-extras
success "Dependencies installed"

# =============================================================================
# 5. Install Pre-commit Hooks (if available)
# =============================================================================
if [ -f ".pre-commit-config.yaml" ]; then
    info "Installing pre-commit hooks..."
    uv run pre-commit install
    success "Pre-commit hooks installed"
else
    info "No pre-commit config found, skipping hooks setup"
fi

# =============================================================================
# 6. Validate Installation
# =============================================================================
info "Validating installation..."

if [ -f "scripts/validate_install.py" ]; then
    uv run python scripts/validate_install.py
else
    error "validate_install.py not found. Cannot validate installation."
fi

# =============================================================================
# 7. Summary
# =============================================================================
echo ""
echo "=========================================="
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To run tests:"
echo "  uv run pytest"
echo ""
echo "To run the MCP server:"
echo "  uv run mcp-server"
echo ""
echo "To install in editable mode:"
echo "  uv pip install -e ."
echo ""
echo "=========================================="

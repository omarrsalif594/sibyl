#!/bin/bash
#
# Test Runner Script - Run all tests for MCP server
#
# Usage:
#   ./scripts/run_tests.sh              # Run all tests
#   ./scripts/run_tests.sh unit         # Run only unit tests
#   ./scripts/run_tests.sh integration  # Run only integration tests
#   ./scripts/run_tests.sh regression   # Run only regression tests
#   ./scripts/run_tests.sh fast         # Run only fast tests
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}MCP Server Test Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Ensure project root is on PYTHONPATH
export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${PROJECT_ROOT}"

# Change to project root
cd "$PROJECT_ROOT"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo ""
    echo "Install test dependencies:"
    echo "  pip install -r tests/requirements.txt"
    echo ""
    exit 1
fi

# Parse command line arguments
TEST_CATEGORY="${1:-all}"

echo -e "${YELLOW}Test category:${NC} $TEST_CATEGORY"
echo ""

# Run tests based on category
case "$TEST_CATEGORY" in
    all)
        echo -e "${GREEN}Running all tests...${NC}"
        pytest tests/ -v
        ;;
    unit)
        echo -e "${GREEN}Running unit tests...${NC}"
        pytest tests/unit/ -v -m unit
        ;;
    integration)
        echo -e "${GREEN}Running integration tests...${NC}"
        pytest tests/integration/ -v -m integration
        ;;
    regression)
        echo -e "${GREEN}Running regression tests...${NC}"
        pytest tests/regression/ -v -m regression
        ;;
    fast)
        echo -e "${GREEN}Running fast tests only...${NC}"
        pytest tests/ -v -m fast
        ;;
    contract)
        echo -e "${GREEN}Running contract tests...${NC}"
        pytest tests/unit/test_tool_contracts.py -v
        ;;
    coverage)
        echo -e "${GREEN}Running tests with coverage report...${NC}"
        pytest tests/ -v --cov --cov-report=html --cov-report=term
        echo ""
        echo -e "${YELLOW}Coverage report generated in: htmlcov/index.html${NC}"
        ;;
    *)
        echo -e "${RED}Unknown test category: $TEST_CATEGORY${NC}"
        echo ""
        echo "Available categories:"
        echo "  all         - Run all tests"
        echo "  unit        - Run unit tests"
        echo "  integration - Run integration tests"
        echo "  regression  - Run regression tests"
        echo "  fast        - Run fast tests only"
        echo "  contract    - Run contract tests only"
        echo "  coverage    - Run tests with coverage"
        exit 1
        ;;
esac

TEST_EXIT_CODE=$?

echo ""
echo -e "${BLUE}========================================${NC}"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Tests passed!${NC}"
else
    echo -e "${RED}✗ Tests failed!${NC}"
fi

echo -e "${BLUE}========================================${NC}"
echo ""

exit $TEST_EXIT_CODE

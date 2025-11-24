#!/bin/bash
# Example shell script for calling Sibyl pipelines via HTTP API using curl
#
# This demonstrates how to use the HTTP API to execute pipelines using curl.
#
# Usage:
#   ./call_pipeline.sh
#
# Note:
#   Make sure the HTTP server is running:
#   sibyl http serve --workspace config/workspaces/example.yaml --port 8000

set -e  # Exit on error

API_BASE_URL="http://localhost:8000"

echo "============================================================"
echo "Sibyl HTTP API Examples with curl"
echo "============================================================"
echo ""

# Check workspace health
echo "1. Checking Workspace Health"
echo "----------------------------"
curl -s -X GET "${API_BASE_URL}/health/workspace" | json_pp
echo ""

# List available pipelines
echo "2. Listing Available Pipelines"
echo "-------------------------------"
curl -s -X GET "${API_BASE_URL}/pipelines" | json_pp
echo ""

# Get info about a specific pipeline
echo "3. Getting Pipeline Info: web_research"
echo "---------------------------------------"
curl -s -X GET "${API_BASE_URL}/pipelines/web_research" | json_pp || echo "Pipeline not found"
echo ""

# Execute web_research pipeline
echo "4. Executing Pipeline: web_research"
echo "------------------------------------"
curl -s -X POST "${API_BASE_URL}/pipelines/web_research" \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "query": "What is artificial intelligence?",
      "top_k": 5
    }
  }' | json_pp || echo "Pipeline execution failed"
echo ""

# Execute summarize_url pipeline
echo "5. Executing Pipeline: summarize_url"
echo "-------------------------------------"
curl -s -X POST "${API_BASE_URL}/pipelines/summarize_url" \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
      "max_length": 200
    }
  }' | json_pp || echo "Pipeline execution failed"
echo ""

# Example with invalid parameters (should return 400)
echo "6. Testing Validation: Invalid Parameters"
echo "------------------------------------------"
curl -s -X POST "${API_BASE_URL}/pipelines/web_research" \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "invalid_param": "test"
    }
  }' | json_pp
echo ""

# Example with non-existent pipeline (should return 404)
echo "7. Testing Error Handling: Non-existent Pipeline"
echo "-------------------------------------------------"
curl -s -X POST "${API_BASE_URL}/pipelines/nonexistent_pipeline" \
  -H "Content-Type: application/json" \
  -d '{
    "params": {}
  }' | json_pp
echo ""

echo "============================================================"
echo "All examples completed!"
echo "============================================================"

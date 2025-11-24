# Sibyl HTTP API Client Examples

This directory contains examples demonstrating how to call Sibyl pipelines via the HTTP API.

## Prerequisites

1. **Start the HTTP server**:
   ```bash
   sibyl http serve --workspace config/workspaces/example.yaml --port 8000
   ```

2. **For Python example**: Install requests library:
   ```bash
   pip install requests
   ```

3. **For Shell example**: Ensure `curl` and `json_pp` (or `jq`) are installed:
   ```bash
   # Most systems have curl pre-installed
   # json_pp comes with Perl (usually pre-installed on Unix systems)
   # Alternative: install jq
   brew install jq  # macOS
   apt-get install jq  # Debian/Ubuntu
   ```

## Available Examples

### 1. Python Example (`call_pipeline.py`)

Comprehensive Python example using the `requests` library.

**Usage**:
```bash
python call_pipeline.py
```

**Features**:
- Health check
- List pipelines
- Get pipeline info
- Execute pipelines with parameters
- Error handling
- Timeout handling

**Example**:
```python
import requests

# Execute pipeline
response = requests.post(
    "http://localhost:8000/pipelines/web_research",
    json={
        "params": {
            "query": "What is AI?",
            "top_k": 5
        }
    }
)

result = response.json()
print(result)
```

### 2. Shell Script Example (`call_pipeline.sh`)

Shell script example using `curl` for API calls.

**Usage**:
```bash
chmod +x call_pipeline.sh
./call_pipeline.sh
```

**Features**:
- All API endpoints demonstrated
- JSON formatting with `json_pp`
- Error handling examples

**Example**:
```bash
# Execute pipeline
curl -X POST "http://localhost:8000/pipelines/web_research" \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "query": "What is AI?",
      "top_k": 5
    }
  }'
```

## API Endpoints

### Health Check
```bash
GET /health/workspace
```

### List Pipelines
```bash
GET /pipelines
```

### Get Pipeline Info
```bash
GET /pipelines/{pipeline_name}
```

### Execute Pipeline
```bash
POST /pipelines/{pipeline_name}
Content-Type: application/json

{
  "params": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

## Response Format

### Success Response
```json
{
  "ok": true,
  "status": "success",
  "trace_id": "abc-123",
  "pipeline_name": "web_research",
  "duration_ms": 1234.5,
  "start_time": "2025-11-20T10:00:00Z",
  "end_time": "2025-11-20T10:00:01Z",
  "data": {
    "last_result": "Pipeline output here..."
  }
}
```

### Error Response
```json
{
  "ok": false,
  "status": "error",
  "trace_id": "abc-123",
  "pipeline_name": "web_research",
  "duration_ms": 100.0,
  "error": {
    "type": "ValidationError",
    "message": "Invalid input parameters",
    "details": {}
  }
}
```

## HTTP Status Codes

- **200 OK**: Pipeline executed successfully
- **400 Bad Request**: Invalid input parameters
- **404 Not Found**: Pipeline not found
- **500 Internal Server Error**: Pipeline execution error
- **503 Service Unavailable**: Workspace not initialized
- **504 Gateway Timeout**: Pipeline execution timeout

## Troubleshooting

### Connection Refused
```
Error: Could not connect to Sibyl HTTP API
```
**Solution**: Make sure the HTTP server is running:
```bash
sibyl http serve --workspace config/workspaces/example.yaml
```

### Timeout Errors
```
Error: Request timed out
```
**Solution**: Increase the timeout or check pipeline configuration:
```python
response = requests.post(url, json=data, timeout=120)  # 2 minutes
```

### Validation Errors
```
HTTP 400: Validation Error
```
**Solution**: Check the pipeline's input schema and ensure all required parameters are provided with correct types.

## Additional Resources

- [HTTP API Documentation](../../docs/api/http_api.md)
- [Pipeline Configuration Guide](../../docs/pipelines.md)
- [Workspace Configuration](../../docs/workspace.md)

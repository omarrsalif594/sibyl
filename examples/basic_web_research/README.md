# Basic Web Research Example

This example demonstrates how to use Sibyl programmatically to execute a research pipeline.

## What This Example Does

This example shows:
1. Loading a workspace configuration
2. Building providers from the workspace
3. Creating a workspace runtime
4. Running a pipeline programmatically
5. Handling results (success and error cases)
6. Accessing trace IDs for debugging

## Prerequisites

- Python 3.11 or later
- Sibyl installed (`pip install sibyl-mcp` or from source)
- A valid workspace configuration

## Files

- `run_example.py` - Main example script
- `example_workspace.yaml` - Simple workspace configuration for the example
- `README.md` - This file

## Setup

1. Ensure Sibyl is installed:

```bash
pip install sibyl-mcp
# or if running from source:
pip install -e /path/to/sibyl
```

2. (Optional) Set up API keys if using cloud providers:

```bash
export OPENAI_API_KEY=your-api-key
export ANTHROPIC_API_KEY=your-api-key
```

For this example, we use local providers so no API keys are needed.

## Running the Example

### Method 1: Using the provided workspace

```bash
cd examples/basic_web_research
python run_example.py
```

### Method 2: Using a custom workspace

```bash
python run_example.py --workspace /path/to/your/workspace.yaml --pipeline your_pipeline
```

### Method 3: With additional parameters

```bash
python run_example.py --param query="What is machine learning?" --param top_k=10
```

## Expected Output

When you run the example successfully, you should see output like:

```
=======================================================================
Sibyl Basic Web Research Example
=======================================================================

Loading workspace from: example_workspace.yaml

Building providers...
  Built 3 provider instances

Initializing workspace runtime...
  Runtime initialized with 1 shops

Running pipeline: simple_search
  Parameters: {'query': 'What is Sibyl AI orchestration?'}

-----------------------------------------------------------------------
Pipeline Execution
-----------------------------------------------------------------------

✓ Pipeline completed successfully!

  Trace ID: abc-123-def-456
  Duration: 234.56ms

Results:
  [Search results would appear here...]

Additional Context:
  {
    "pipeline_name": "simple_search",
    "pipeline_shop": "rag",
    ...
  }

=======================================================================
Example completed successfully!
=======================================================================
```

If there's an error, you'll see:

```
✗ Pipeline execution failed!

  Error: Pipeline step 'rag.retriever' failed: ...
  Type: step_error
  Trace ID: abc-123-def-456
  Duration: 123.45ms

Error Details:
  {
    "step": "rag.retriever",
    "message": "..."
  }
```

## Understanding the Code

### 1. Load Workspace

```python
from sibyl.config.workspace_loader import load_workspace

workspace = load_workspace("example_workspace.yaml")
```

This loads and validates the workspace configuration.

### 2. Build Providers

```python
from sibyl.framework.providers import build_providers

providers = build_providers(workspace)
```

This creates provider instances (LLM, embeddings, vector store) from the workspace config.

### 3. Create Runtime

```python
from sibyl.framework.runtime import WorkspaceRuntime

runtime = WorkspaceRuntime(workspace, providers)
```

The runtime orchestrates pipeline execution across shops.

### 4. Run Pipeline

```python
result = await runtime.run_pipeline_v2(
    "simple_search",
    query="What is Sibyl?"
)
```

Execute a pipeline with parameters. Returns a `PipelineResult`.

### 5. Handle Results

```python
if result.ok:
    print(f"Success! Trace ID: {result.trace_id}")
    print(f"Results: {result.data}")
else:
    print(f"Error: {result.error.message}")
    print(f"Trace ID: {result.trace_id}")
```

All results include a trace ID for debugging and observability.

## Customization

### Using Your Own Workspace

Replace `example_workspace.yaml` with your own:

```python
workspace = load_workspace("/path/to/your/workspace.yaml")
```

### Running Different Pipelines

Change the pipeline name:

```python
result = await runtime.run_pipeline_v2(
    "your_pipeline_name",
    param1="value1",
    param2="value2"
)
```

### Adding Error Handling

```python
try:
    result = await runtime.run_pipeline_v2("simple_search", query="test")

    if result.ok:
        # Success path
        process_results(result.data)
    else:
        # Error path
        logger.error(f"Pipeline failed: {result.error.message}")
        send_alert(result.trace_id)

except Exception as e:
    # Unexpected error
    logger.exception("Unexpected error during pipeline execution")
```

### Integrating into an Application

```python
class ResearchService:
    def __init__(self, workspace_path: str):
        workspace = load_workspace(workspace_path)
        providers = build_providers(workspace)
        self.runtime = WorkspaceRuntime(workspace, providers)

    async def search(self, query: str) -> dict:
        result = await self.runtime.run_pipeline_v2(
            "simple_search",
            query=query
        )

        if result.ok:
            return {
                "success": True,
                "data": result.data,
                "trace_id": result.trace_id
            }
        else:
            return {
                "success": False,
                "error": result.error.message,
                "trace_id": result.trace_id
            }

# Use in application
service = ResearchService("config/workspaces/production.yaml")
results = await service.search("machine learning")
```

## Troubleshooting

### Workspace validation fails

```
WorkspaceLoadError: Workspace validation failed
```

**Solution**: Validate your workspace first:
```bash
python -m sibyl.cli workspace validate --file your_workspace.yaml
```

### Provider build fails

```
ERROR - Failed to build provider: Provider type 'unknown' not found
```

**Solution**: Check that provider types in your workspace are supported. See `sibyl/framework/providers/factories.py`.

### Pipeline not found

```
PipelineExecutionError: Pipeline 'unknown_pipeline' not found
```

**Solution**: List available pipelines:
```bash
python -m sibyl.cli pipeline list --workspace your_workspace.yaml
```

### Technique not found

```
TechniqueResolutionError: Technique 'unknown' not found in shop 'rag'
```

**Solution**: Check your shop configuration in the workspace YAML. Ensure technique mappings are correct.

## Next Steps

- Explore other workspace templates in `config/workspaces/`
- Read the [Architecture Overview](../../docs/architecture/overview.md)
- Check out [Getting Started Guide](../../docs/getting_started.md)
- Build custom techniques for your domain
- Deploy with the MCP server for AI assistant integration

## Resources

- [Sibyl Documentation](../../docs/)
- [Workspace Schema](../../sibyl/config/workspace_schema.py)
- [Provider Implementations](../../sibyl/framework/providers/)
- [Technique Implementations](../../sibyl/techniques/)

## License

Apache License 2.0 - See LICENSE file in repository root

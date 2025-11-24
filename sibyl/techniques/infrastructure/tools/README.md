# Tools Infrastructure (Internal)

**⚠️ This is an internal infrastructure library, not a full technique family.**

## Overview

The tools infrastructure provides the foundation for tool execution and management in Sibyl. It defines tool interfaces, execution contexts, and the tool executor that handles tool invocation with proper error handling and observability.

## Components

### Tool Interface (`tool_interface.py`)
- **Tool**: Base protocol for tool implementations
- **ToolMetadata**: Descriptive metadata for tools (name, description, parameters)
- **ToolContext**: Execution context passed to tools
- **ToolExecutionResult**: Standardized result wrapper with success/error handling

### Tool Executor (`tool_executor.py`)
- **ToolExecutor**: Executes tools with proper lifecycle management
- Handles tool validation and parameter checking
- Provides error handling and retry logic
- Integrates with observability and metrics systems

## Usage

```python
from sibyl.techniques.infrastructure.tools import (
    Tool,
    ToolMetadata,
    ToolContext,
    ToolExecutor,
    ToolExecutionResult
)

# Define a custom tool
class MyTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="my_tool",
            description="Does something useful",
            parameters={"input": str}
        )

    def execute(self, context: ToolContext) -> ToolExecutionResult:
        result = do_work(context.parameters["input"])
        return ToolExecutionResult(success=True, data=result)

# Execute a tool
executor = ToolExecutor()
context = ToolContext(parameters={"input": "data"})
result = executor.execute(MyTool(), context)
```

## Tool Interface Protocol

All tools must implement:

```python
@property
def metadata(self) -> ToolMetadata:
    """Return tool metadata"""
    ...

def execute(self, context: ToolContext) -> ToolExecutionResult:
    """Execute the tool with the given context"""
    ...
```

## Tool Execution Result

The `ToolExecutionResult` provides standardized output:

```python
ToolExecutionResult(
    success: bool,          # Execution succeeded
    data: Any,             # Result data if successful
    error: Optional[str],  # Error message if failed
    metadata: Dict         # Additional execution metadata
)
```

## Extension Points

Users can extend the tools infrastructure by:

1. Implementing custom tools following the `Tool` protocol
2. Creating custom tool executors with specialized behavior
3. Adding custom tool discovery and registration mechanisms
4. Implementing tool composition and chaining strategies

## Not a Technique

Unlike other directories in `infrastructure/`, the `tools/` library:
- Does NOT follow the technique template structure
- Does NOT have subtechniques or implementations hierarchy
- IS a utility library for internal framework use
- Provides core tool execution capabilities used by agent systems

## Related

- See agent implementations that use tools for task execution
- See `sibyl/core/contracts/tools.py` for tool protocol definitions
- See MCP (Model Context Protocol) integration for external tool providers

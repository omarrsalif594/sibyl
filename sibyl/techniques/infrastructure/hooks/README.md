# Hooks Infrastructure (Internal)

**⚠️ This is an internal infrastructure library, not a full technique family.**

## Overview

The hooks infrastructure provides a flexible event system for intercepting and extending behavior throughout the Sibyl framework. It includes built-in hooks, a registry system, and decorators for easy integration.

## Components

### Built-in Hooks (`builtin.py`)
- **MetricsHook**: Collects operation metrics and performance data
- **CacheHook**: Provides caching capabilities with configurable strategies
- **OperationMetrics**: Tracks timing, counts, and resource usage

### Hook Registry (`registry.py`)
- **HookRegistry**: Central registry for managing hooks
- **get_hook_registry()**: Global accessor for the singleton registry
- **reset_hook_registry()**: Reset registry state (primarily for testing)

### Decorators (`decorator.py`)
- **@with_hooks**: Apply hooks to functions or methods
- **@with_hooks_and_session**: Apply hooks with session context

## Usage

```python
from sibyl.techniques.infrastructure.hooks import (
    HookRegistry,
    MetricsHook,
    with_hooks
)

# Register a hook
registry = HookRegistry()
registry.register(MetricsHook())

# Apply hooks via decorator
@with_hooks
def my_operation(data):
    return process(data)
```

## Extension Points

Users can extend the hooks system by:

1. Implementing custom hooks following the hook protocol
2. Registering custom hooks with the global registry
3. Using decorators to apply hooks to their own functions

## Not a Technique

Unlike other directories in `infrastructure/`, the `hooks/` library:
- Does NOT follow the technique template structure
- Does NOT have subtechniques or implementations hierarchy
- IS a utility library for internal framework use
- CAN be extended by users but is primarily for framework infrastructure

## Related

- See `sibyl/core/contracts/hooks.py` for hook protocol definitions
- See other technique families for examples of hook usage

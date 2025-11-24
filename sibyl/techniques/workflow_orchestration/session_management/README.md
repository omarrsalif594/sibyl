# SessionManagement Technique

Session lifecycle and context management with configurable rotation strategies,
circuit breaker protection, and context preservation.

## Overview

The SessionManagement technique provides a comprehensive framework for managing
long-running conversational sessions with multiple pluggable strategies for:

1. **Rotation Strategies**: When to rotate/refresh sessions
2. **Rotation-Based Management**: Integrated rotation + circuit breaker
3. **Context Preservation**: What to keep across rotations
4. **Summarization**: How to compress context

All hardcoded constants have been externalized to configuration files with
environment variable override support.

## Subtechniques

### rotation_strategy
Session rotation strategies based on different triggers.

**Default Implementations:**
- `token_based` - Token Based implementation (configurable thresholds)
- `time_based` - Time Based implementation (duration-based)
- `message_count` - Message Count implementation (message-based)

**Provider Implementations:**
- To be added via MCP servers

### rotation_based
Integrated session rotation with circuit breaker and operation draining.

**Default Implementations:**
- `rotation_manager` - Full rotation lifecycle management with:
  - Token-based rotation triggers (early warning + force rotation)
  - Circuit breaker for graceful degradation on failures
  - Operation draining to ensure clean boundaries
  - Generation counters for atomic session swaps
  - Environment variable override support

**Configuration Sources:**
- `sibyl/core/config/core_defaults.yaml::session.rotation`
- `sibyl/core/config/core_defaults.yaml::session.circuit_breaker`

**Eliminates Hardcoded Values From:**
- `sibyl/core/session/rotation_manager.py`:
  - operation_poll_ms: 100ms (line 413)
  - early_rotation_threshold: 60% (lines 217-218)
  - force_rotation_threshold: 70% (line 268)
  - rotation_timeout_seconds: 30s (line 337)
- `sibyl/core/session/circuit_breaker.py`:
  - failure_threshold: 3 (line 105)
  - recovery_timeout_seconds: 30s (line 106)
  - half_open_max_calls: 1 (line 107)

**Environment Variable Overrides:**
- `SIBYL_SESSION_ROTATION_OPERATION_POLL_MS`
- `SIBYL_SESSION_ROTATION_EARLY_ROTATION_THRESHOLD`
- `SIBYL_SESSION_ROTATION_FORCE_ROTATION_THRESHOLD`
- `SIBYL_SESSION_CIRCUIT_BREAKER_FAILURE_THRESHOLD`
- `SIBYL_SESSION_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS`

**Provider Implementations:**
- To be added via MCP servers

### context_preservation
Context preservation methods

**Default Implementations:**
- `sliding_window` - Sliding Window implementation
- `importance_based` - Importance Based implementation
- `full_history` - Full History implementation

**Provider Implementations:**
- To be added via MCP servers

### summarization
Session summarization techniques

**Default Implementations:**
- `extractive` - Extractive implementation
- `abstractive` - Abstractive implementation
- `no_summarize` - No Summarize implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

### Basic Usage

```python
from sibyl.techniques.session_management import SessionManagementTechnique

technique = SessionManagementTechnique()

# Check if rotation is needed (rotation_based)
result = technique.execute(
    input_data={
        "tokens_used": 140000,
        "tokens_budget": 200000,
        "session_id": "sess_abc123",
        "rotation_in_progress": False,
        "circuit_state": "closed",
        "generation": 1
    },
    subtechnique="rotation_manager",
    category="rotation_based"
)

# Result contains:
# - status: RotationStatus (CONTINUE, SHOULD_SUMMARIZE, SHOULD_ROTATE, etc.)
# - reason: Human-readable explanation
# - utilization_pct: Current utilization percentage
# - should_rotate: Boolean flag
# - should_summarize: Boolean flag
# - circuit_state: Circuit breaker state
# - metadata: Additional context (thresholds, config, etc.)
```

### Environment Variable Overrides

```bash
# Override rotation thresholds at runtime
export SIBYL_SESSION_ROTATION_EARLY_ROTATION_THRESHOLD=0.55
export SIBYL_SESSION_ROTATION_FORCE_ROTATION_THRESHOLD=0.75

# Override circuit breaker settings
export SIBYL_SESSION_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
export SIBYL_SESSION_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS=60

# Run your application
python your_app.py
```

### Configuration Cascade

Configuration is merged from multiple sources (highest priority first):

1. Environment variables (e.g., `SIBYL_SESSION_ROTATION_*`)
2. Runtime config overrides passed to `execute()`
3. Subtechnique config (`subtechniques/rotation_based/default/config.yaml`)
4. Technique config (`config.yaml`)
5. Global config (`sibyl/core/config/core_defaults.yaml`)

### Example Response

```python
RotationCheckResult(
    status=RotationStatus.SHOULD_ROTATE,
    reason="Token usage 72.5% exceeds force rotation threshold 70.0%",
    utilization_pct=72.5,
    tokens_used=145000,
    tokens_budget=200000,
    circuit_state=CircuitState.CLOSED,
    should_rotate=True,
    should_summarize=False,
    metadata={
        "session_id": "sess_abc123",
        "generation": 1,
        "early_rotation_threshold_pct": 60.0,
        "force_rotation_threshold_pct": 70.0,
        "operation_poll_ms": 100,
        "rotation_timeout_seconds": 30,
        "failure_threshold": 3,
        "recovery_timeout_seconds": 30
    }
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.

## Migration from Hardcoded Values

If you were previously using `SessionRotationManager` or `CircuitBreaker`
directly with hardcoded values, you can now:

1. Update `sibyl/core/config/core_defaults.yaml` with your preferred defaults
2. Use environment variables for runtime overrides
3. Pass configuration through the technique interface

Example migration:

```python
# Before (hardcoded)
manager = SessionRotationManager(
    early_threshold=0.60,  # Hardcoded
    force_threshold=0.70,  # Hardcoded
)

# After (configurable)
technique = SessionManagementTechnique()
result = technique.execute(
    input_data=session_data,
    subtechnique="rotation_manager",
    category="rotation_based",
    config={
        "rotation": {
            "early_rotation_threshold": 0.60,
            "force_rotation_threshold": 0.70
        }
    }
)
```

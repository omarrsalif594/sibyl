# Rate Limiting Technique

Provides configurable rate limiting with multiple algorithms to control API request rates.

## Overview

The rate limiting technique eliminates hardcoded values from `sibyl/core/security/rate_limiter.py:40-41` by loading configuration from the core configuration system. It supports multiple rate limiting algorithms and provides flexible configuration through environment variables and YAML files.

## Features

- **Configurable Rate Limits**: Load limits from core configuration
- **Multiple Algorithms**: Sliding window, fixed window, token bucket
- **Per-IP and Per-Endpoint**: Track limits separately or combined
- **Environment Overrides**: Override any parameter via environment variables
- **Automatic Cleanup**: Memory-efficient tracking with automatic cleanup

## Configuration

### Core Configuration (core_defaults.yaml)

```yaml
security:
  rate_limiter:
    default_rpm: 100                # Default requests per minute
    window_seconds: 60              # Rate limit window duration
    cleanup_interval_seconds: 300   # Cleanup interval for rate limit state
    exempt_ips:
      - "localhost"
      - "127.0.0.1"
      - "::1"
```

### Environment Variables

Override configuration via environment variables:

```bash
# Override default requests per minute
export SIBYL_SECURITY_RATE_LIMITER_DEFAULT_RPM=200

# Override window duration
export SIBYL_SECURITY_RATE_LIMITER_WINDOW_SECONDS=120

# Override cleanup interval
export SIBYL_SECURITY_RATE_LIMITER_CLEANUP_INTERVAL_SECONDS=600
```

## Usage

### Basic Usage

```python
from sibyl.techniques.rate_limiting import RateLimitingTechnique

# Initialize technique (loads from core config)
technique = RateLimitingTechnique()

# Check rate limit
result = technique.execute(
    subtechnique="sliding_window",
    client_ip="192.168.1.100",
    endpoint="/api/query"
)

if result["allowed"]:
    print(f"Request allowed. Remaining: {result['remaining']}")
else:
    print(f"Rate limit exceeded. Reset at: {result['reset_at']}")
```

### With Custom Configuration

```python
# Custom configuration
custom_config = {
    "default_rpm": 200,
    "window_seconds": 120,
    "exempt_ips": ["10.0.0.1"]
}

technique = RateLimitingTechnique(config=custom_config)
```

### Get Configuration

```python
# Get current configuration
config = technique.get_configuration()
print(f"Rate limit: {config['default_rpm']} requests per minute")
print(f"Window: {config['window_seconds']} seconds")
```

## Subtechniques

### 1. Sliding Window (Default)

Token bucket with sliding window algorithm. Provides smooth rate limiting by tracking requests in a time window.

**Algorithm**: Maintains a deque of request timestamps and removes expired requests before checking the limit.

**Pros**:
- Smooth rate limiting
- No sudden bursts at window boundaries
- Memory efficient

**Cons**:
- Slightly more complex than fixed window
- Requires timestamp tracking

### 2. Fixed Window

Fixed window rate limiting (not yet implemented).

**Algorithm**: Counts requests in fixed time windows (e.g., 00:00-00:59, 01:00-01:59).

**Pros**:
- Simple implementation
- Easy to understand
- Low memory usage

**Cons**:
- Allows bursts at window boundaries
- Can exceed 2x limit at boundaries

### 3. Token Bucket

Classic token bucket algorithm (not yet implemented).

**Algorithm**: Tokens are added to a bucket at a constant rate. Each request consumes a token.

**Pros**:
- Allows controlled bursts
- Industry standard
- Predictable behavior

**Cons**:
- More complex state management
- Requires token refill logic

## Architecture

```
sibyl/techniques/rate_limiting/
├── config.yaml                   # Technique configuration
├── technique.py                  # Main technique class
├── __init__.py                   # Exports
├── README.md                     # Documentation
└── subtechniques/
    ├── sliding_window/
    │   └── default/
    │       ├── config.yaml       # Subtechnique config
    │       └── implementation.py # Algorithm implementation
    ├── fixed_window/             # Coming soon
    └── token_bucket/             # Coming soon
```

## Integration with Existing Code

The rate limiting technique is designed to work with the existing `RateLimiter` class:

```python
from sibyl.core.security.rate_limiter import RateLimiter
from sibyl.techniques.rate_limiting import RateLimitingTechnique

# Get configuration from technique
technique = RateLimitingTechnique()
config = technique.get_configuration()

# Create rate limiter with configuration
limiter = RateLimiter(
    default_limit=config["default_rpm"],
    window_seconds=config["window_seconds"],
    exempt_ips=set(config["exempt_ips"])
)
```

## Validation

The technique validates all configuration parameters:

- `default_rpm`: Must be between 1 and 10,000
- `window_seconds`: Must be between 1 and 3,600 (1 hour)
- `cleanup_interval_seconds`: Must be between 60 and 86,400 (1 day)
- `exempt_ips`: Must be a list of strings

Invalid configuration will raise a `ValueError` with a descriptive message.

## Eliminated Hardcoded Values

This technique eliminates the following hardcoded values from `sibyl/core/security/rate_limiter.py`:

| Line | Original Value | New Source |
|------|----------------|------------|
| 40 | `default_limit: int = 100` | `security.rate_limiter.default_rpm` |
| 41 | `window_seconds: int = 60` | `security.rate_limiter.window_seconds` |
| 58 | `exempt_ips = {"127.0.0.1", "localhost", "::1"}` | `security.rate_limiter.exempt_ips` |
| 72 | `_cleanup_interval = 300` | `security.rate_limiter.cleanup_interval_seconds` |

Total: **4 hardcoded values eliminated**

## Testing

```python
import pytest
from sibyl.techniques.rate_limiting import RateLimitingTechnique

def test_rate_limiting_initialization():
    technique = RateLimitingTechnique()
    assert technique.technique_id == "rate_limiting"
    assert technique.default_rpm == 100
    assert technique.window_seconds == 60

def test_rate_limiting_with_exempt_ip():
    technique = RateLimitingTechnique()
    result = technique.execute(
        subtechnique="sliding_window",
        client_ip="localhost",
        endpoint="/api/test"
    )
    assert result["allowed"] is True
    assert result["reason"] == "exempt_ip"

def test_rate_limiting_enforcement():
    from sibyl.techniques.rate_limiting.subtechniques.sliding_window.default.implementation import reset_state
    reset_state()

    technique = RateLimitingTechnique()
    client_ip = "192.168.1.100"

    # Make requests up to the limit
    for i in range(technique.default_rpm):
        result = technique.execute(
            subtechnique="sliding_window",
            client_ip=client_ip,
            endpoint="/api/test"
        )
        assert result["allowed"] is True

    # Next request should be blocked
    result = technique.execute(
        subtechnique="sliding_window",
        client_ip=client_ip,
        endpoint="/api/test"
    )
    assert result["allowed"] is False
    assert result["reason"] == "rate_limit_exceeded"
```

## Performance Considerations

- **Memory Usage**: O(n) where n is the number of requests in the window
- **Time Complexity**: O(1) for rate limit check (amortized)
- **Cleanup**: Automatic cleanup every `cleanup_interval_seconds`
- **Scalability**: For distributed systems, use Redis or similar for shared state

## Future Enhancements

1. **Fixed Window Implementation**: Complete the fixed window subtechnique
2. **Token Bucket Implementation**: Complete the token bucket subtechnique
3. **Redis Backend**: Add distributed rate limiting support
4. **Per-User Limits**: Support user-specific rate limits
5. **Dynamic Limits**: Adjust limits based on system load
6. **Rate Limit Headers**: Return standard rate limit HTTP headers

## References

- [Rate Limiting Patterns](https://www.nginx.com/blog/rate-limiting-nginx/)
- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [Sliding Window Algorithm](https://hechao.li/2018/06/25/Rate-Limiter-Part1/)

# Security Validation Technique

Provides configurable security validation for input sanitization and secret detection.

## Overview

The security validation technique eliminates hardcoded values from `sibyl/core/security/validators/input.py` and `sibyl/core/security/secrets.py` by loading configuration from the core configuration system. It supports multiple validation subtechniques and provides flexible configuration through environment variables and YAML files.

## Features

- **Input Validation**: Sanitize and validate user inputs to prevent injection attacks
- **Secret Detection**: Detect API keys, tokens, and credentials in text
- **Configurable Parameters**: Load all parameters from core configuration
- **Environment Overrides**: Override any parameter via environment variables
- **Multiple Detectors**: Support for AWS, GitHub, and generic secret patterns

## Configuration

### Core Configuration (core_defaults.yaml)

```yaml
security:
  # Secret detection
  secrets:
    min_entropy: 3.0                # Minimum entropy for secret detection
    min_length: 16                  # Minimum length for secret candidates
    enabled_detectors:              # Active secret detectors
      - "aws"
      - "github"
      - "generic_api_key"

  # Input validation
  input_validation:
    max_size_kb: 1024               # Maximum input size (KB)

  # Shape validation
  shape_validation:
    max_retry_attempts: 3           # Max retries for shape violations
```

### Environment Variables

Override configuration via environment variables:

```bash
# Override secret detection parameters
export SIBYL_SECURITY_SECRETS_MIN_ENTROPY=4.0
export SIBYL_SECURITY_SECRETS_MIN_LENGTH=20

# Override input validation
export SIBYL_SECURITY_INPUT_VALIDATION_MAX_SIZE_KB=2048

# Override shape validation
export SIBYL_SECURITY_SHAPE_VALIDATION_MAX_RETRY_ATTEMPTS=5
```

## Usage

### Input Validation

```python
from sibyl.techniques.security_validation import SecurityValidationTechnique

# Initialize technique (loads from core config)
technique = SecurityValidationTechnique()

# Validate input
result = technique.execute(
    subtechnique="input_validation",
    text="SELECT * FROM users",
    validation_type="general"
)

if result["valid"]:
    print(f"Input is valid: {result['sanitized']}")
else:
    print(f"Validation failed: {result['issues']}")
```

### Secret Detection

```python
from sibyl.techniques.security_validation import SecurityValidationTechnique

technique = SecurityValidationTechnique()

# Detect secrets in text
text = "My API key is AKIAIOSFODNN7EXAMPLE"
result = technique.execute(
    subtechnique="secret_detection",
    text=text
)

if result["has_secrets"]:
    print(f"Found {result['count']} secrets:")
    for finding in result["findings"]:
        print(f"  - {finding['pattern']}: {finding['text']}")
else:
    print("No secrets detected")
```

### Get Configuration

```python
# Get current configuration
config = technique.get_configuration()
print(f"Min entropy: {config['min_entropy']}")
print(f"Min length: {config['min_length']}")
print(f"Max input length: {config['max_input_length']} KB")
print(f"Enabled detectors: {config['enabled_detectors']}")
```

## Subtechniques

### 1. Input Validation (Default)

Validates and sanitizes user inputs to prevent injection attacks.

**Checks**:
- Length limits
- Path traversal patterns
- SQL keyword detection
- Control character removal
- Model name validation

**Example**:
```python
result = technique.execute(
    subtechnique="input_validation",
    text="../../../etc/passwd",
    validation_type="general"
)
# Result: {"valid": False, "issues": [{"type": "path_traversal", ...}]}
```

### 2. Secret Detection

Detects secrets in text using pattern matching and entropy analysis.

**Supported Patterns**:
- AWS access keys and secret keys
- GitHub tokens and OAuth tokens
- Google Cloud API keys
- Anthropic API keys
- OpenAI API keys
- Generic API keys (with entropy filtering)

**Example**:
```python
result = technique.execute(
    subtechnique="secret_detection",
    text="ghp_1234567890abcdefghijklmnopqrstuvwxyz"
)
# Result: {"has_secrets": True, "findings": [...]}
```

### 3. Shape Validation

Validates output shape conformance (not yet implemented).

## Architecture

```
sibyl/techniques/security_validation/
├── config.yaml                   # Technique configuration
├── technique.py                  # Main technique class
├── __init__.py                   # Exports
├── README.md                     # Documentation
└── subtechniques/
    ├── __init__.py
    └── input_validation/
        └── default/
            ├── config.yaml       # Subtechnique config
            ├── implementation.py # Validation logic
            └── __init__.py
```

## Validation

The technique validates all configuration parameters:

- `min_entropy`: Must be between 0.0 and 10.0
- `min_length`: Must be between 1 and 1,000
- `max_input_length`: Must be between 1 and 102,400 KB (100 MB)
- `max_retry_attempts`: Must be between 1 and 10
- `enabled_detectors`: Must be a list

Invalid configuration will raise a `ValueError` with a descriptive message.

## Eliminated Hardcoded Values

This technique eliminates the following hardcoded values:

### From security/validators/input.py:

| Line | Original Value | New Source |
|------|----------------|------------|
| 166 | `max_length: int = 10000` | `security.input_validation.max_size_kb * 1024` |
| 37 | Model name max length: 200 | Configurable via max_input_length |

### From security/secrets.py:

| Concept | Original Behavior | New Source |
|---------|-------------------|------------|
| Entropy threshold | Implicit in patterns | `security.secrets.min_entropy` |
| Length threshold | Pattern-dependent | `security.secrets.min_length` |
| Detector selection | All patterns active | `security.secrets.enabled_detectors` |

Total: **5+ hardcoded values eliminated**

## Testing

```python
import pytest
from sibyl.techniques.security_validation import SecurityValidationTechnique

def test_initialization():
    technique = SecurityValidationTechnique()
    assert technique.technique_id == "security_validation"
    assert technique.min_entropy == 3.0
    assert technique.min_length == 16

def test_input_validation_sql_injection():
    technique = SecurityValidationTechnique()
    result = technique.execute(
        subtechnique="input_validation",
        text="DROP TABLE users",
        validation_type="general"
    )
    assert not result["valid"]
    assert any(issue["type"] == "sql_keyword" for issue in result["issues"])

def test_input_validation_path_traversal():
    technique = SecurityValidationTechnique()
    result = technique.execute(
        subtechnique="input_validation",
        text="../../../etc/passwd",
        validation_type="general"
    )
    assert not result["valid"]
    assert any(issue["type"] == "path_traversal" for issue in result["issues"])

def test_secret_detection_aws():
    technique = SecurityValidationTechnique()
    result = technique.execute(
        subtechnique="secret_detection",
        text="AKIAIOSFODNN7EXAMPLE"
    )
    assert result["has_secrets"]
    assert result["count"] >= 1
    assert any(f["pattern"] == "aws_access_key" for f in result["findings"])

def test_secret_detection_github():
    technique = SecurityValidationTechnique()
    result = technique.execute(
        subtechnique="secret_detection",
        text="ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    )
    assert result["has_secrets"]
    assert any(f["pattern"] == "github_token" for f in result["findings"])

def test_config_validation_min_entropy():
    with pytest.raises(ValueError, match="min_entropy"):
        SecurityValidationTechnique(config={"min_entropy": -1.0})

def test_config_validation_max_input_length():
    with pytest.raises(ValueError, match="max_input_length"):
        SecurityValidationTechnique(config={"max_input_length": 200000})
```

## Performance Considerations

- **Input Validation**: O(n) where n is input length
- **Secret Detection**: O(n*m) where m is number of patterns
- **Memory Usage**: Minimal, patterns compiled once
- **Scalability**: Stateless, can be used in distributed systems

## Integration Example

```python
from sibyl.techniques.security_validation import SecurityValidationTechnique
from sibyl.core.security.validators.input import sanitize_string_input

# Get configuration from technique
technique = SecurityValidationTechnique()
config = technique.get_configuration()

# Use configuration in existing validation
max_chars = config["max_input_length"] * 1024
sanitized = sanitize_string_input(
    text="user input",
    max_length=max_chars
)
```

## References

- [OWASP Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [Secret Detection Best Practices](https://github.com/zricethezav/gitleaks)
- [Shannon Entropy](https://en.wikipedia.org/wiki/Entropy_(information_theory))

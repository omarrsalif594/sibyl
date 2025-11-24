# Security Technique

Security and compliance controls

## Subtechniques

### content_filtering
Content filtering methods

**Default Implementations:**
- `keyword_filter` - Keyword Filter implementation
- `pattern_filter` - Pattern Filter implementation

**Provider Implementations:**
- To be added via MCP servers

### pii_redaction
PII redaction strategies

**Default Implementations:**
- `regex_redaction` - Regex Redaction implementation
- `spacy` - Spacy implementation
- `presidio` - Presidio implementation

**Provider Implementations:**
- To be added via MCP servers

### access_control
Access control mechanisms

**Default Implementations:**
- `rbac` - Rbac implementation
- `abac` - Abac implementation

**Provider Implementations:**
- To be added via MCP servers

### prompt_injection_detection
Prompt injection detection

**Default Implementations:**
- `pattern_based` - Pattern Based implementation
- `ml_based` - Ml Based implementation

**Provider Implementations:**
- To be added via MCP servers

### audit_logging
Audit logging backends

**Default Implementations:**
- `file_log` - File Log implementation
- `db_log` - Db Log implementation

**Provider Implementations:**
- To be added via MCP servers

## Configuration

See `config.yaml` for technique-level settings and each subtechnique's `config.yaml` for options.

## Usage

```python
from sibyl.techniques.security import SecurityTechnique

technique = SecurityTechnique()
result = technique.execute(
    input_data=data,
    subtechnique="{subtechnique_name}",
    implementation="{impl_name}"
)
```

## Custom Implementations

See `subtechniques/{subtechnique}/custom/README.md` for adding custom implementations.

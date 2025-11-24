# Security Guide

Complete guide to securing Sibyl in production environments.

## Overview

Security is critical for production deployments. This guide covers:

1. **Authentication & Authorization** - Control access
2. **Data Protection** - Protect sensitive data
3. **Network Security** - Secure communications
4. **Input Validation** - Prevent attacks
5. **Secrets Management** - Handle credentials safely
6. **Compliance** - Meet regulatory requirements

## Authentication

### API Key Authentication

**Configuration**:
```yaml
mcp:
  authentication:
    type: api_key
    header: X-API-Key              # Header name
    keys:
      - "${API_KEY_ADMIN}"         # Admin key
      - "${API_KEY_USER}"          # User key
      - "${API_KEY_READONLY}"      # Read-only key

    # Key metadata
    key_metadata:
      "${API_KEY_ADMIN}":
        name: "Admin Key"
        permissions: ["*"]
        rate_limit: 1000
      "${API_KEY_USER}":
        name: "User Key"
        permissions: ["search_*", "read_*"]
        rate_limit: 100
      "${API_KEY_READONLY}":
        name: "Read-Only Key"
        permissions: ["search_documents"]
        rate_limit: 60
```

**Generate secure API keys**:
```python
import secrets
import hashlib

# Generate API key
api_key = secrets.token_urlsafe(32)
print(f"API Key: {api_key}")

# Store hashed version
hashed = hashlib.sha256(api_key.encode()).hexdigest()
print(f"Hashed: {hashed}")
```

**Best practices**:
- Use cryptographically random keys (32+ bytes)
- Store hashed versions, not plaintext
- Rotate keys regularly (every 90 days)
- Revoke compromised keys immediately
- Use different keys per environment (dev, staging, prod)

### JWT Authentication

**Configuration**:
```yaml
mcp:
  authentication:
    type: jwt
    secret: "${JWT_SECRET}"        # 256-bit secret
    algorithm: HS256               # or RS256 for asymmetric

    # Token validation
    verify_signature: true
    verify_expiration: true
    verify_audience: true
    verify_issuer: true

    # Claims
    required_claims:
      - sub                        # Subject (user ID)
      - exp                        # Expiration
      - iat                        # Issued at

    audience: "sibyl-api"
    issuer: "your-auth-service"
    expiration: 3600               # 1 hour

    # Optional: public key for RS256
    # public_key_file: /path/to/public.pem
```

**Generate JWT tokens**:
```python
import jwt
import datetime

def generate_token(user_id: str, secret: str) -> str:
    """Generate JWT token."""
    payload = {
        'sub': user_id,
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        'aud': 'sibyl-api',
        'iss': 'your-auth-service',
        'permissions': ['search_documents', 'index_documents']
    }
    return jwt.encode(payload, secret, algorithm='HS256')

token = generate_token('user_123', 'your-secret-key')
```

**Usage**:
```bash
curl -X POST http://localhost:8000/mcp/tools/search_documents \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

### OAuth2 / OpenID Connect

**Configuration**:
```yaml
mcp:
  authentication:
    type: oauth2
    provider: auth0                # auth0, google, github, custom

    # OAuth2 settings
    client_id: "${OAUTH_CLIENT_ID}"
    client_secret: "${OAUTH_CLIENT_SECRET}"
    authorization_endpoint: "https://your-domain.auth0.com/authorize"
    token_endpoint: "https://your-domain.auth0.com/oauth/token"
    userinfo_endpoint: "https://your-domain.auth0.com/userinfo"

    # Scopes
    scopes:
      - openid
      - email
      - profile

    # Redirect URI
    redirect_uri: "http://localhost:8000/oauth/callback"
```

### Mutual TLS (mTLS)

**Configuration**:
```yaml
mcp:
  transport: http
  tls:
    enabled: true

    # Server certificate
    cert_file: /etc/sibyl/certs/server-cert.pem
    key_file: /etc/sibyl/certs/server-key.pem

    # Client authentication
    client_auth: required          # required, optional, none
    ca_cert_file: /etc/sibyl/certs/ca-cert.pem

    # TLS version
    min_version: TLS1.2
    max_version: TLS1.3

    # Cipher suites (recommended)
    ciphers:
      - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
      - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
```

**Generate certificates**:
```bash
# Generate CA key and certificate
openssl req -x509 -newkey rsa:4096 -days 365 -nodes \
  -keyout ca-key.pem -out ca-cert.pem \
  -subj "/CN=Sibyl CA"

# Generate server key and certificate
openssl req -newkey rsa:4096 -nodes \
  -keyout server-key.pem -out server-req.pem \
  -subj "/CN=sibyl.example.com"

openssl x509 -req -in server-req.pem -days 365 \
  -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial \
  -out server-cert.pem

# Generate client certificate
openssl req -newkey rsa:4096 -nodes \
  -keyout client-key.pem -out client-req.pem \
  -subj "/CN=client"

openssl x509 -req -in client-req.pem -days 365 \
  -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial \
  -out client-cert.pem
```

## Authorization

### Role-Based Access Control (RBAC)

**Configuration**:
```yaml
mcp:
  authorization:
    enabled: true
    type: rbac

    # Define roles
    roles:
      admin:
        description: "Full system access"
        permissions:
          - "*"                    # All permissions

      developer:
        description: "Developer access"
        permissions:
          - "search_*"
          - "index_*"
          - "read_*"

      analyst:
        description: "Read-only analyst"
        permissions:
          - "search_documents"
          - "get_statistics"

      guest:
        description: "Limited guest access"
        permissions:
          - "search_documents"

    # Map users to roles
    user_roles:
      user_admin_123: admin
      user_dev_456: developer
      user_analyst_789: analyst

    # Map API keys to roles
    api_key_roles:
      "${API_KEY_ADMIN}": admin
      "${API_KEY_DEV}": developer
      "${API_KEY_ANALYST}": analyst
```

**Tool-level permissions**:
```yaml
mcp:
  tools:
    # Public tool
    - name: search_documents
      pipeline: search_pipeline
      permissions:
        required_roles: []         # Anyone can use

    # Restricted tool
    - name: index_documents
      pipeline: index_pipeline
      permissions:
        required_roles: [admin, developer]

    # Admin-only tool
    - name: delete_all_documents
      pipeline: delete_pipeline
      permissions:
        required_roles: [admin]
        confirmation_required: true
```

### Attribute-Based Access Control (ABAC)

**Configuration**:
```yaml
mcp:
  authorization:
    type: abac

    # Define policies
    policies:
      - name: allow_own_documents
        effect: allow
        conditions:
          - resource.owner_id == user.id

      - name: allow_department_access
        effect: allow
        conditions:
          - resource.department == user.department

      - name: deny_sensitive_data
        effect: deny
        conditions:
          - resource.classification == "confidential"
          - user.clearance_level < 3

      - name: allow_business_hours
        effect: allow
        conditions:
          - time.hour >= 9
          - time.hour <= 17
          - time.weekday < 5          # Monday-Friday
```

## Data Protection

### PII Redaction

**Configuration**:
```yaml
shops:
  infrastructure:
    config:
      security:
        pii_redaction:
          enabled: true

          # What to redact
          patterns:
            - email
            - phone
            - ssn
            - credit_card
            - ip_address
            - street_address

          # Named entity recognition
          ner_enabled: true
          ner_entities:
            - PERSON
            - LOCATION
            - ORGANIZATION

          # Replacement strategy
          replacement: "[REDACTED]"   # or hash, mask, tokenize

          # Custom patterns
          custom_patterns:
            - name: employee_id
              regex: "EMP-\\d{6}"
              replacement: "[EMP_ID]"

            - name: api_key
              regex: "sk-[a-zA-Z0-9]{48}"
              replacement: "[API_KEY]"
```

**Usage in pipeline**:
```yaml
pipelines:
  secure_search:
    steps:
      # Redact PII from input
      - use: infrastructure.security
        config:
          subtechnique: pii_redaction

      - use: rag.retrieval
      - use: ai_generation.generation

      # Redact PII from output
      - use: infrastructure.security
        config:
          subtechnique: pii_redaction
```

### Data Encryption

**Encryption at rest**:
```yaml
providers:
  vector_store:
    main:
      kind: pgvector
      dsn: "${DATABASE_URL}"

      # Database-level encryption
      # Use encrypted PostgreSQL tablespace
      encryption:
        enabled: true
        algorithm: AES-256-GCM
        key_file: /etc/sibyl/keys/db-encryption-key

  # Encrypted backups
  backup:
    encryption:
      enabled: true
      algorithm: AES-256-GCM
      key_file: /etc/sibyl/keys/backup-key
```

**Encryption in transit**:
```yaml
mcp:
  transport: http
  tls:
    enabled: true
    min_version: TLS1.2
    cert_file: /etc/sibyl/certs/cert.pem
    key_file: /etc/sibyl/certs/key.pem
```

**Database encryption** (PostgreSQL):
```sql
-- Enable pgcrypto extension
CREATE EXTENSION pgcrypto;

-- Create encrypted column
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    content BYTEA,  -- Store encrypted content
    metadata JSONB
);

-- Encrypt data
INSERT INTO documents (id, content)
VALUES (
    gen_random_uuid(),
    pgp_sym_encrypt('sensitive content', 'encryption-key')
);

-- Decrypt data
SELECT pgp_sym_decrypt(content, 'encryption-key') FROM documents;
```

### Secure Logging

**Configuration**:
```yaml
observability:
  logging:
    level: INFO

    # PII redaction in logs
    redact_pii: true
    redact_patterns:
      - email
      - phone
      - api_key
      - password

    # Don't log sensitive fields
    exclude_fields:
      - password
      - api_key
      - token
      - secret

    # Mask sensitive data
    mask_fields:
      - credit_card
      - ssn
    mask_char: "*"
    mask_length: 4              # Show last 4 digits
```

## Network Security

### Firewall Rules

```bash
# Allow only necessary ports
# HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# MCP server
sudo ufw allow 8000/tcp

# Metrics (internal only)
sudo ufw allow from 10.0.0.0/8 to any port 9090

# Health checks (internal only)
sudo ufw allow from 10.0.0.0/8 to any port 8001

# Deny everything else
sudo ufw default deny incoming
sudo ufw enable
```

### Network Policies (Kubernetes)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sibyl-network-policy
spec:
  podSelector:
    matchLabels:
      app: sibyl
  policyTypes:
    - Ingress
    - Egress

  ingress:
    # Allow traffic from ingress controller
    - from:
      - namespaceSelector:
          matchLabels:
            name: ingress-nginx
      ports:
      - protocol: TCP
        port: 8000

    # Allow metrics scraping from Prometheus
    - from:
      - namespaceSelector:
          matchLabels:
            name: monitoring
      ports:
      - protocol: TCP
        port: 9090

  egress:
    # Allow DNS
    - to:
      - namespaceSelector: {}
      ports:
      - protocol: UDP
        port: 53

    # Allow PostgreSQL
    - to:
      - podSelector:
          matchLabels:
            app: postgres
      ports:
      - protocol: TCP
        port: 5432

    # Allow external APIs (OpenAI, etc.)
    - to:
      - podSelector: {}
      ports:
      - protocol: TCP
        port: 443
```

### Reverse Proxy (Nginx)

```nginx
# /etc/nginx/sites-available/sibyl
server {
    listen 443 ssl http2;
    server_name sibyl.example.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/sibyl.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sibyl.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Proxy to Sibyl
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Request size limit
        client_max_body_size 10M;
    }

    # Block sensitive endpoints
    location ~ ^/(admin|internal) {
        deny all;
    }

    # Health check (no auth required)
    location /health {
        proxy_pass http://localhost:8001/health;
        access_log off;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name sibyl.example.com;
    return 301 https://$server_name$request_uri;
}
```

## Input Validation

### Prompt Injection Detection

**Configuration**:
```yaml
shops:
  infrastructure:
    config:
      security:
        prompt_injection_detection:
          enabled: true
          threshold: 0.8           # Confidence threshold
          block_on_detection: true # Block or just warn

          # Detection methods
          methods:
            - pattern_based         # Known attack patterns
            - model_based           # ML classifier
            - heuristic            # Suspicious keywords

          # Custom patterns
          custom_patterns:
            - "ignore previous instructions"
            - "you are now"
            - "disregard"
            - "system prompt"
```

**Usage**:
```yaml
pipelines:
  secure_qa:
    steps:
      # Detect injection attempts
      - use: infrastructure.security
        config:
          subtechnique: injection_detection

      # Only proceed if safe
      - use: rag.retrieval
        condition: ${security.is_safe}
```

### Input Sanitization

**Configuration**:
```yaml
shops:
  infrastructure:
    config:
      security:
        input_sanitization:
          enabled: true

          # Remove dangerous content
          remove_html: true
          remove_scripts: true
          remove_sql: true

          # Length limits
          max_query_length: 5000
          max_document_size: 10485760  # 10MB

          # Character filtering
          allowed_chars: alphanumeric_punctuation
          normalize_unicode: true
```

### Parameter Validation

```yaml
mcp:
  tools:
    - name: search_documents
      parameters:
        query:
          type: string
          required: true
          minLength: 1
          maxLength: 1000
          pattern: "^[a-zA-Z0-9 .,?!-]+$"  # Safe characters only

        top_k:
          type: integer
          minimum: 1
          maximum: 20              # Prevent resource abuse

      # Additional validation
      validation:
        - name: no_sql_injection
          type: pattern
          pattern: "(?i)(select|insert|update|delete|drop)"
          action: reject

        - name: no_path_traversal
          type: pattern
          pattern: "\\.\\."
          action: reject
```

## Secrets Management

### Environment Variables

**Best practices**:
```bash
# ✅ Good - use environment variables
export OPENAI_API_KEY=sk-...
export DATABASE_URL=postgresql://...

# ❌ Bad - hardcode in code or config
api_key: "sk-..."  # Never do this!
```

### Secrets Manager (AWS, GCP, Azure)

**AWS Secrets Manager**:
```python
import boto3
import json

def get_secret(secret_name: str) -> dict:
    """Retrieve secret from AWS Secrets Manager."""
    client = boto3.client('secretsmanager', region_name='us-west-2')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usage
secrets = get_secret('sibyl/prod/api-keys')
os.environ['OPENAI_API_KEY'] = secrets['openai_api_key']
```

**Configuration**:
```yaml
providers:
  llm:
    primary:
      kind: openai
      api_key: "${OPENAI_API_KEY}"  # Loaded from secrets manager
```

### HashiCorp Vault

**Configuration**:
```python
import hvac

# Initialize Vault client
client = hvac.Client(
    url='http://vault:8200',
    token=os.getenv('VAULT_TOKEN')
)

# Read secret
secret = client.secrets.kv.v2.read_secret_version(
    path='sibyl/api-keys'
)

# Use secret
os.environ['OPENAI_API_KEY'] = secret['data']['data']['openai_api_key']
```

### Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: sibyl-secrets
type: Opaque
stringData:
  openai-api-key: sk-...
  database-url: postgresql://...

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sibyl
spec:
  template:
    spec:
      containers:
      - name: sibyl
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: sibyl-secrets
              key: openai-api-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: sibyl-secrets
              key: database-url
```

## Compliance

### GDPR Compliance

**Data subject rights**:
```yaml
# Right to erasure (delete user data)
pipelines:
  delete_user_data:
    parameters:
      user_id: string
    steps:
      - use: data.delete_user_documents
        config:
          user_id: ${user_id}

      - use: data.delete_user_logs
        config:
          user_id: ${user_id}
          retention_days: 0

# Right to data portability (export user data)
pipelines:
  export_user_data:
    parameters:
      user_id: string
    steps:
      - use: data.export_user_data
        config:
          user_id: ${user_id}
          format: json
```

**Data minimization**:
```yaml
observability:
  logging:
    # Only log necessary data
    exclude_fields:
      - email
      - name
      - address
      - phone

    # Anonymize user IDs
    anonymize_user_ids: true
```

**Consent management**:
```yaml
mcp:
  tools:
    - name: search_documents
      consent_required: true
      consent_types:
        - data_processing
        - analytics
```

### HIPAA Compliance

**Audit logging**:
```yaml
observability:
  audit_logging:
    enabled: true
    log_all_access: true
    log_modifications: true
    log_authentication: true

    # Immutable audit log
    storage: write_once_read_many
    retention_years: 6

    # Include required fields
    fields:
      - timestamp
      - user_id
      - action
      - resource
      - result
      - ip_address
```

**Encryption**:
```yaml
# All data must be encrypted
providers:
  vector_store:
    main:
      encryption:
        enabled: true
        algorithm: AES-256-GCM

mcp:
  transport: http
  tls:
    enabled: true
    min_version: TLS1.2
```

## Security Checklist

### Production Deployment

- [ ] All secrets in environment variables or secrets manager
- [ ] TLS/SSL enabled for all communication
- [ ] Authentication enabled (API key, JWT, or OAuth2)
- [ ] Authorization configured (RBAC or ABAC)
- [ ] PII redaction enabled
- [ ] Input validation and sanitization enabled
- [ ] Prompt injection detection enabled
- [ ] Rate limiting configured
- [ ] Firewall rules configured
- [ ] Security headers set (Nginx/reverse proxy)
- [ ] Audit logging enabled
- [ ] Regular security updates applied
- [ ] Secrets rotated regularly
- [ ] Backups encrypted
- [ ] Vulnerability scanning enabled
- [ ] Incident response plan documented

### Code Security

- [ ] No hardcoded secrets
- [ ] Input validation on all user input
- [ ] Output encoding to prevent XSS
- [ ] Parameterized queries (prevent SQL injection)
- [ ] CSRF protection enabled
- [ ] Secure session management
- [ ] Principle of least privilege
- [ ] Error messages don't leak sensitive info
- [ ] Dependencies regularly updated
- [ ] Code reviewed for security issues

## Security Incident Response

### Detection

```yaml
observability:
  alerting:
    security_alerts:
      - name: multiple_failed_auth
        condition: failed_auth_count > 10 in 5m
        severity: high

      - name: unusual_access_pattern
        condition: requests_from_ip > 1000 in 1m
        severity: medium

      - name: data_exfiltration
        condition: data_export_size > 1GB
        severity: critical
```

### Response Plan

1. **Detect**: Alert triggered
2. **Contain**: Block attacker, revoke compromised credentials
3. **Investigate**: Check logs, identify scope
4. **Remediate**: Fix vulnerability, restore from backup if needed
5. **Recover**: Resume normal operations
6. **Review**: Post-mortem, update security measures

## Further Reading

- **[Deployment Guide](deployment.md)** - Secure deployment
- **[Observability](observability.md)** - Security monitoring
- **[Troubleshooting](troubleshooting.md)** - Security issues
- **[OWASP Top 10](https://owasp.org/www-project-top-ten/)** - Web security

---

**Previous**: [Troubleshooting](troubleshooting.md) | **Next**: [Performance Tuning](performance-tuning.md)

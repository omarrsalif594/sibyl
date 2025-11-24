# Security Policy

Sibyl is currently in an early `0.1.x` phase. This project has **not** gone through a formal security review, and you should not treat it as a security product.

This document explains how to report vulnerabilities and gives some practical guidance for running Sibyl in a safer way, but it is **not** a guarantee of security.

---

## Supported Versions

Currently supported versions of Sibyl for security fixes:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | ✅ Yes (current)   |

Older versions are not actively supported. If you find an issue in an older version, please check whether it reproduces on the latest `0.1.x` release.

---

## Reporting a Vulnerability

We prefer that potential security issues are reported privately.

### Please Avoid Public Issues

Please **do not** report security vulnerabilities through:

- Public GitHub issues  
- Public GitHub discussions  
- Public pull requests  

Those channels are more appropriate for feature requests and non-sensitive bugs.

### How to Report

For now, the primary channel for reporting vulnerabilities is:

- **GitHub Security Advisories**  
  Use the “Report a vulnerability” button on the repository’s **Security** tab.

If you cannot use this mechanism (for example, you do not have a GitHub account), we recognize this is not ideal. In that case:

- Please avoid posting exploit details publicly.
- If you must open a public issue, keep the description high-level (no PoC or sensitive details) and indicate that you are trying to report a potential security problem so maintainers can follow up.

### What to Include

To help us understand and fix the issue, please include where possible:

- Type of vulnerability (e.g. XSS, SSRF, RCE, privilege escalation)
- Steps to reproduce (as specific as you can make them)
- Affected code paths (file names, line ranges, or URLs)
- The version / commit hash you tested against
- Environment details (framework, OS, container image, etc.)
- Any proof-of-concept or exploit code (shared through the private advisory)

### Response Expectations

Sibyl is an early-stage open-source project. There is no dedicated security team or guaranteed SLA.

We will **aim** to:

- Acknowledge your report within a reasonable time (for example, a few days).
- Investigate the issue and keep you updated through the GitHub advisory.
- Fix or mitigate serious problems as we are able.

We cannot promise specific timelines, but we will do our best to respond responsibly.

---

## Security Posture & Limitations

A few important points up front:

- Sibyl is in an early `0.1.x` phase and has **not** been independently audited.
- There are security-related mechanisms in the codebase (e.g. some input validation, rate limiting hooks, restricted unpickling), but they should be treated as **helpful guardrails**, not as a complete security solution.
- You remain responsible for:
  - How and where Sibyl is deployed  
  - Network protections (firewalls, reverse proxies, TLS, etc.)  
  - Secrets management  
  - Compliance with any regulatory or contractual requirements

If you plan to expose Sibyl to untrusted users or the public internet, plan as you would for any other new, un-audited service.

---

## Operational Security Best Practices

The items below are suggestions for running Sibyl more safely. Some are features or scripts in the repo; others are general operational practices.

### 1. Environment Configuration

- Disable debug mode in production:

  ```bash
  export SIBYL_DEBUG=false
  ```

- Use a state / database path outside of `/tmp` or other world-writable directories, for example:

  ```bash
  export SIBYL_DB_PATH=/var/lib/sibyl/state/sibyl_state.duckdb
  chmod 600 /var/lib/sibyl/state/sibyl_state.duckdb
  ```

- Run Sibyl as a non-root user where possible.

### 2. Secrets Management

- Do not commit secrets or `.env` files containing secrets to version control.
- Prefer a secrets manager (AWS Secrets Manager, GCP Secret Manager, Vault, etc.) for production.
- If you use environment variables for secrets, ensure they are:
  - Not written to logs or crash reports.
  - Not stored in files that are committed.
- If you use scripts such as `devops/scripts/rotate_api_keys.sh`, treat them as a starting point and review them for your own environment and practices.

### 3. Authentication & Authorization

If you expose an HTTP API or MCP server:

- Require some form of authentication (for example, API keys) for non-trivial operations.
- Use strong, randomly generated keys.
- Apply the principle of least privilege with any external integrations (databases, cloud services, etc.).
- Monitor for repeated failed authentication attempts.

### 4. Network Security

- Place Sibyl behind a reverse proxy with TLS termination (Nginx, Traefik, cloud load balancer, etc.).
- Restrict inbound network access to Sibyl (firewall rules, security groups, etc.).
- Avoid binding directly to all interfaces (`0.0.0.0`) unless it is behind proper network protections.

### 5. Database & State Security

- Keep state and database files (e.g., DuckDB files) in a directory with restricted permissions.
- Consider encrypting the volume if you store sensitive data.
- Have a backup and restore procedure that you test periodically.

### 6. Configuration Validation

If you use `devops/config/validate_env.py` (or similar scripts in the repo):

- Run them as part of your deployment process for sanity checks.
- Ensure they are up to date with the actual configuration options used in your environment.
- Treat these scripts as helpers, not as formal security audits.

### 7. Monitoring & Logging

- Ship logs to a central logging system.
- Set up alerts for error spikes, repeated authentication failures, or unusual traffic patterns.
- Avoid logging secrets, raw credentials, or highly sensitive data.
- Implement log rotation and retention policies appropriate for your system.

### 8. Dependency & Code Scanning

- Keep dependencies reasonably up to date.
- If you use tools like `bandit`, `safety`, `pip-audit`, or similar, we recommend integrating them into your CI for basic checks, for example:

  ```bash
  bandit -r sibyl/ || true
  safety check || true
  ```

  (Adjust commands and failure policies to your tolerance and tooling.)

---

## Security-Related Mechanisms in Sibyl

This section briefly describes security-related mechanisms present in the codebase at the time of writing. They have not been formally audited and are not a guarantee of safety.

Depending on your version and configuration, you may have access to:

### Authentication

- API key checks for protected endpoints (e.g., via HTTP headers).
- Basic logging of authentication attempts where logging is enabled.

### Rate Limiting

- Hooks or middleware to enforce per-endpoint / per-client rate limits, depending on how you wire the runtime and server together.
- You'll still need to choose limits appropriate for your deployment.

### Input Validation & Guardrails

- Some validation around SQL-related operations (e.g., table name checks) in certain techniques.
- Configurable techniques for prompt sanitization, PII redaction, or similar, where implemented.
- These mechanisms can reduce risk but should not be treated as a complete defense against injection or misuse.

### Deserialization Safeguards

- A more restricted approach to loading pickled data (for things like graphs), intended to reduce the risk of arbitrary code execution.
- You should still avoid loading untrusted pickle data wherever possible.

### HTTP Layers (CORS / Headers)

If you use the provided HTTP server setup and middleware:

- There may be support for setting security-related headers (CORS, CSP, X-Frame-Options, etc.).
- You are responsible for reviewing and tuning these header settings for your own deployment and threat model.

---

## Known Security Considerations

Some areas that deserve extra care:

### Pickle and Other Serialization Formats

- Treat pickle and similar formats as untrusted unless you control the source.
- Even with restrictions, it is safer not to expose generic pickle upload endpoints to untrusted users.

### Templates (e.g., Jinja2)

- Avoid using untrusted templates or mixing HTML output with disabled escaping.
- Consider explicit escaping if you render user-generated content.

### Local Models and External Resources

- Loading models or code from external sources at runtime carries risk.
- Pin model versions and review what you are running in production.

### API Keys and Secrets in Logs

- Ensure your logging configuration does not accidentally log headers, environment variables, or other secrets.
- Be cautious with verbose debug logs in production; they can leak information.

### Compliance

Sibyl itself is not certified against any particular security standard (such as SOC 2 or ISO 27001).

If you need to meet regulatory or certification requirements:

- Treat Sibyl as one component in a larger system.
- Design controls around deployment, access, monitoring, and data retention to match your obligations.
- Document how Sibyl fits into your architecture and what data it processes.

---

## Security Updates

For now, security-related changes will be surfaced primarily through:

- GitHub releases and release notes
- GitHub security advisories (if published for a specific issue)

If you rely on Sibyl in a serious environment, consider:

- Watching the repository on GitHub.
- Reviewing release notes before upgrading.

---

## Contact

At this stage, we do not operate a dedicated security email address or support channel.

For security-related communication:

- Please use GitHub Security Advisories where possible.
- Avoid posting exploit details or sensitive information in public channels.

We appreciate responsible disclosure and will do our best to handle reports carefully, within the limits of a small open-source project.

---

**Last Updated**: 2025-11-24
**Security Policy Version**: 0.1
**Applies to Sibyl Versions**: 0.1.x

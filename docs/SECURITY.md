# ThreadCrumb Security Guide

Comprehensive security features for protecting sensitive data.

## Table of Contents

- [Overview](#overview)
- [PII Detection and Redaction](#pii-detection-and-redaction)
- [Data Encryption](#data-encryption)
- [Audit Logging](#audit-logging)
- [Best Practices](#best-practices)
- [Compliance](#compliance)

## Overview

ThreadCrumb provides enterprise-grade security features to protect sensitive information in your Slack exports.

### Security Features

- **PII Detection**: Automatically identify sensitive personal information
- **Content Redaction**: Remove or mask PII from exports
- **Encryption at Rest**: Encrypt cached data with AES-128
- **Audit Logging**: Track all operations for compliance
- **Secure Credentials**: Safe storage of API keys and tokens

### Installation

```bash
pip install threadcrumb[security]
```

## PII Detection and Redaction

Automatically detect and handle personally identifiable information (PII) in your Slack messages.

### Supported PII Types

ThreadCrumb detects the following types of sensitive information:

| Type | Example | Pattern |
|------|---------|---------|
| **Email** | user@company.com | RFC 5322 compliant |
| **Phone** | (555) 123-4567 | US/International formats |
| **SSN** | 123-45-6789 | Social Security Numbers |
| **Credit Card** | 4532-1234-5678-9010 | Visa, MC, Amex, Discover |
| **IP Address** | 192.168.1.1 | IPv4 addresses |
| **API Key** | api_key=abc123... | Generic API keys |
| **AWS Key** | AKIAIOSFODNN7EXAMPLE | AWS access keys |
| **GitHub Token** | ghp_xxx... | GitHub personal tokens |
| **Password** | password=secret123 | Password fields |
| **URL** | https://example.com | HTTP/HTTPS URLs |
| **Date of Birth** | 01/15/1990 | MM/DD/YYYY format |

### Basic Usage

```bash
# Detect and redact PII
threadcrumb generate --redact-pii

# Interactive mode with PII detection
threadcrumb generate --interactive --redact-pii
```

### Redaction Strategies

Configure how PII is redacted:

#### 1. Placeholder (Default)

Replaces PII with type-specific placeholders.

**Example:**
```
Before: Contact me at john.doe@company.com or (555) 123-4567
After:  Contact me at [EMAIL] or [PHONE]
```

**Use when**: Maximum privacy, format doesn't matter

#### 2. Masking

Preserves first and last characters for readability.

**Example:**
```
Before: john.doe@company.com
After:  j*************m
```

**Use when**: Need to preserve some context

#### 3. Hashing

Replaces with consistent hash values.

**Example:**
```
Before: john.doe@company.com
After:  [EMAIL:a1b2c3d4]
```

**Use when**: Need to match same values across documents

#### 4. Removal

Completely removes PII.

**Example:**
```
Before: Contact me at john.doe@company.com
After:  Contact me at
```

**Use when**: Maximum data minimization

### Configuration

```yaml
security:
  enable_pii_detection: true
  redact_pii: true
  redaction_strategy: "placeholder"  # placeholder, mask, hash, remove
  pii_types:
    - email
    - phone
    - ssn
    - credit_card
    - api_key
```

### Programmatic Usage

```python
from threadcrumb.security import PIIDetector, ContentRedactor

# Initialize detector
detector = PIIDetector()

# Detect PII
text = "Email me at john@example.com"
matches = detector.detect(text)

# Redact content
redactor = ContentRedactor(detector=detector)
redacted_text = redactor.redact(text)
print(redacted_text)  # "Email me at [EMAIL]"
```

### PII Reports

Generate PII detection reports:

```python
from threadcrumb.security import ContentRedactor

redactor = ContentRedactor()
report = redactor.scan_and_report(text)

print(report)
# {
#   "total_matches": 2,
#   "contains_pii": True,
#   "matches_by_type": {
#     "email": 1,
#     "phone": 1
#   },
#   "positions": [...]
# }
```

## Data Encryption

Encrypt sensitive data at rest using industry-standard encryption.

### Features

- **Algorithm**: Fernet (AES-128-CBC + HMAC authentication)
- **Key Management**: Secure key storage with restrictive permissions
- **Scope**: Cache files, sensitive configuration
- **Performance**: Minimal overhead (~5-10%)

### Setup

```bash
# Install security dependencies
pip install threadcrumb[security]

# Generate encryption key
python -c "from threadcrumb.security import DataEncryptor; print(DataEncryptor.generate_key())"
```

### Basic Usage

```bash
# Encrypt cache during export
threadcrumb generate --encrypt-cache

# Export is slower but data is encrypted
```

### Key Management

#### Default Key Location

Keys are stored at `~/.threadcrumb/encryption.key` with permissions set to `0600` (owner read/write only).

#### Custom Key

Provide a custom encryption key:

```bash
# Set via environment variable
export THREADCRUMB_ENCRYPTION_KEY="your-base64-key"

threadcrumb generate --encrypt-cache
```

#### Key Rotation

Rotate encryption keys periodically:

```python
from threadcrumb.security import DataEncryptor
from pathlib import Path

# Generate new key
new_key = DataEncryptor.generate_key()

# Save to file
encryptor = DataEncryptor(key=new_key)
encryptor.save_key(Path.home() / ".threadcrumb" / "encryption.key")

# Re-encrypt existing cache with new key
# (clear cache and re-fetch)
```

### File Encryption

Encrypt specific files:

```python
from threadcrumb.security import DataEncryptor
from pathlib import Path

encryptor = DataEncryptor()

# Encrypt a file
encryptor.encrypt_file(
    input_path=Path("sensitive.json"),
    output_path=Path("sensitive.json.enc")
)

# Decrypt a file
encryptor.decrypt_file(
    input_path=Path("sensitive.json.enc"),
    output_path=Path("sensitive.json")
)
```

### Cache Directory Encryption

Encrypt entire cache directory:

```python
from threadcrumb.security import encrypt_cache_directory, DataEncryptor
from pathlib import Path

encryptor = DataEncryptor()
cache_dir = Path.home() / ".threadcrumb" / "cache"

encrypt_cache_directory(cache_dir, encryptor)
# Creates encrypted version at cache_encrypted/
```

### Performance Impact

| Operation | Without Encryption | With Encryption | Overhead |
|-----------|-------------------|-----------------|----------|
| Cache Write | 20ms | 25ms | +25% |
| Cache Read | 10ms | 12ms | +20% |
| Full Export (1000 msg) | 2m 15s | 2m 30s | +11% |

## Audit Logging

Comprehensive activity logging for compliance and security monitoring.

### Features

- **Structured Logging**: JSON format for easy parsing
- **Event Types**: Authentication, data access, exports, errors
- **Severity Levels**: Info, Warning, Error, Critical
- **Metadata**: Contextual information with each event

### Setup

```yaml
security:
  audit_logging: true
  audit_log_path: "~/.threadcrumb/audit.log"
  min_audit_level: "info"  # info, warning, error, critical
```

### Event Types

| Event | Description | Level |
|-------|-------------|-------|
| `auth_success` | Successful Slack authentication | Info |
| `auth_failure` | Failed authentication attempt | Warning |
| `data_access` | Channel or message access | Info |
| `data_export` | Wiki generation completed | Info |
| `pii_detected` | PII found in content | Warning |
| `pii_redacted` | PII redacted from content | Info |
| `encryption_enabled` | Encryption activated | Info |
| `config_changed` | Configuration modified | Info |
| `error_occurred` | Operation failed | Error |

### Log Format

Each log entry is a JSON object:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "event_type": "data_export",
  "level": "info",
  "message": "Exported 10 channels (250 threads) in markdown format",
  "user": "user@company.com",
  "workspace_id": "T12345678",
  "metadata": {
    "format": "markdown",
    "channel_count": 10,
    "thread_count": 250
  }
}
```

### Usage

```python
from threadcrumb.security import AuditLogger, AuditEventType, AuditLevel

# Initialize audit logger
audit_logger = AuditLogger(
    log_file=Path("audit.log"),
    min_level=AuditLevel.INFO
)

# Log events
audit_logger.log_auth_success(
    user="user@company.com",
    workspace_id="T12345678"
)

audit_logger.log_data_export(
    format="markdown",
    channel_count=10,
    thread_count=250
)

audit_logger.log_pii_detected(
    pii_type="email",
    count=5,
    channel_id="C12345678"
)
```

### Audit Reports

Generate audit reports:

```python
from threadcrumb.security import AuditLogger

logger = AuditLogger()
report = logger.generate_report(output_path=Path("audit_report.json"))

print(report)
# {
#   "generated_at": "2024-01-15T11:00:00Z",
#   "total_events": 150,
#   "events_by_type": {
#     "data_export": 10,
#     "pii_detected": 45,
#     ...
#   },
#   "recent_errors": [...]
# }
```

### Log Rotation

Use `logrotate` for production systems:

```bash
# /etc/logrotate.d/threadcrumb
/home/user/.threadcrumb/audit.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
}
```

## Best Practices

### 1. Defense in Depth

Layer multiple security controls:

```bash
threadcrumb generate \
  --redact-pii \          # PII protection
  --encrypt-cache \       # Encryption at rest
  --use-sqlite-cache      # Centralized secure storage
```

### 2. Principle of Least Privilege

Export only what you need:

```bash
# Export specific channels only
threadcrumb generate --channels "general,announcements"

# Exclude sensitive channels
threadcrumb generate --exclude "hr-confidential,legal"
```

### 3. Regular Security Audits

Review audit logs regularly:

```bash
# Check for PII detections
grep "pii_detected" ~/.threadcrumb/audit.log

# Check for errors
grep "error_occurred" ~/.threadcrumb/audit.log

# Generate monthly report
python -c "
from threadcrumb.security import AuditLogger
from pathlib import Path
logger = AuditLogger()
logger.generate_report(Path('audit_report.json'))
"
```

### 4. Secure Credential Management

Never hardcode credentials:

```bash
# ✗ Bad: Credentials in config file
# config.yaml:
# slack:
#   access_token: "xoxp-..."

# ✓ Good: Use environment variables
export SLACK_ACCESS_TOKEN="xoxp-..."
threadcrumb generate
```

### 5. Data Retention Policies

Clear old cache and exports:

```bash
# Clear cache older than 30 days
find ~/.threadcrumb/cache -mtime +30 -delete

# Clear old exports
find ./output -mtime +90 -delete

# Clear old audit logs (keep 1 year)
find ~/.threadcrumb -name "audit.log.*" -mtime +365 -delete
```

## Compliance

ThreadCrumb security features support compliance with various regulations.

### GDPR (General Data Protection Regulation)

**Requirements Addressed:**

1. **Right to be Forgotten**
   - PII detection and redaction
   - Secure data deletion

2. **Data Minimization**
   - Channel filtering
   - PII redaction
   - Selective exports

3. **Audit Trail**
   - Comprehensive audit logging
   - Data access tracking

**Usage:**
```bash
threadcrumb generate \
  --redact-pii \
  --channels "public-only" \
  --encrypt-cache
```

### HIPAA (Health Insurance Portability and Accountability Act)

**Requirements Addressed:**

1. **Access Controls**
   - Authentication logging
   - User tracking

2. **Audit Controls**
   - Comprehensive audit logs
   - Activity monitoring

3. **Integrity Controls**
   - Encryption at rest
   - Secure storage

4. **Transmission Security**
   - HTTPS for all API calls
   - Encrypted cache

**Usage:**
```bash
threadcrumb generate \
  --redact-pii \
  --encrypt-cache \
  --exclude "patient-data"
```

### SOC 2 (Service Organization Control 2)

**Requirements Addressed:**

1. **Security**
   - Encryption
   - Access controls
   - PII detection

2. **Availability**
   - Export resumption
   - Error handling

3. **Confidentiality**
   - PII redaction
   - Encrypted storage

4. **Processing Integrity**
   - Audit logging
   - Data validation

**Usage:**
```bash
# Full security configuration
threadcrumb generate \
  --redact-pii \
  --encrypt-cache \
  --use-sqlite-cache \
  --interactive
```

### PCI DSS (Payment Card Industry Data Security Standard)

**Requirements Addressed:**

1. **Protect Cardholder Data**
   - Credit card number detection
   - Automatic redaction

2. **Encrypt Transmission**
   - HTTPS for all communications

3. **Maintain Audit Logs**
   - Comprehensive logging
   - Access tracking

**Usage:**
```bash
threadcrumb generate \
  --redact-pii \  # Detects and redacts credit cards
  --encrypt-cache
```

## Security Checklist

Before exporting sensitive data:

- [ ] PII detection enabled
- [ ] Appropriate redaction strategy selected
- [ ] Cache encryption enabled
- [ ] Audit logging configured
- [ ] Sensitive channels excluded
- [ ] Credentials stored securely (env vars, not config files)
- [ ] Output directory has appropriate permissions
- [ ] Regular security audits scheduled
- [ ] Data retention policy defined
- [ ] Compliance requirements verified

## Incident Response

If PII is accidentally exported:

1. **Immediate Actions**
   ```bash
   # Delete exposed files
   rm -rf ./output/*

   # Clear cache
   rm -rf ~/.threadcrumb/cache/*

   # Review audit logs
   grep "pii_detected" ~/.threadcrumb/audit.log
   ```

2. **Investigation**
   - Check audit logs for affected channels
   - Identify scope of exposure
   - Document incident

3. **Remediation**
   - Re-export with PII redaction enabled
   - Update security procedures
   - Notify affected parties if required

4. **Prevention**
   ```bash
   # Enable PII redaction by default
   echo "security:" >> ~/.threadcrumb/config.yaml
   echo "  redact_pii: true" >> ~/.threadcrumb/config.yaml
   ```

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. Email security@threadcrumb.dev with details
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## See Also

- [Configuration Guide](CONFIGURATION.md)
- [Performance Guide](PERFORMANCE.md)
- [Confluence Export Guide](CONFLUENCE_EXPORT.md)

# ThreadCrumb Configuration Guide

Comprehensive guide for configuring ThreadCrumb for your needs.

## Table of Contents

- [Configuration File](#configuration-file)
- [Environment Variables](#environment-variables)
- [AI Provider Configuration](#ai-provider-configuration)
- [Performance Settings](#performance-settings)
- [Security Configuration](#security-configuration)
- [Cache Configuration](#cache-configuration)

## Configuration File

ThreadCrumb uses a YAML configuration file located at `~/.threadcrumb/config.yaml`.

### Initialize Configuration

```bash
threadcrumb config-init
```

This creates a default configuration file that you can customize.

### Configuration Structure

```yaml
slack:
  access_token: ""  # Set via auth command or environment variable
  workspace_id: ""
  cache_dir: "~/.threadcrumb/cache"
  rate_limit_delay: 1.0
  max_retries: 3

ai:
  provider: "bedrock"  # bedrock, openai, or anthropic
  region: "us-east-1"
  model_name: "anthropic.claude-3-sonnet-20240229-v1:0"
  max_tokens: 4096
  temperature: 0.7
  aws_profile: null
  fallback_enabled: true

  # OpenAI settings (when provider=openai)
  openai_api_key: ""  # Or set OPENAI_API_KEY env var
  openai_model: "gpt-4-turbo-preview"

  # Anthropic settings (when provider=anthropic)
  anthropic_api_key: ""  # Or set ANTHROPIC_API_KEY env var
  anthropic_model: "claude-3-opus-20240229"

processing:
  max_thread_depth: 50
  min_message_length: 10
  thread_reconstruction: true

output:
  create_index: true
  interlink_pages: true
  include_toc: true
  include_search: true

confluence:
  base_url: ""
  username: ""
  api_token: ""
  space_key: ""
  root_page_title: "Slack Wiki"
  parent_page_id: null
  use_cloud: true

performance:
  parallel_workers: 4
  use_sqlite_cache: false
  chunk_size: 100

security:
  enable_pii_detection: false
  redact_pii: false
  encrypt_cache: false
  audit_logging: true
  audit_log_path: "~/.threadcrumb/audit.log"
```

## Environment Variables

Override configuration with environment variables:

### Slack Configuration

```bash
export SLACK_ACCESS_TOKEN="xoxp-..."
export SLACK_WORKSPACE_ID="T..."
```

### AI Provider Configuration

#### AWS Bedrock

```bash
export AWS_REGION="us-east-1"
export AWS_PROFILE="your-profile"
```

#### OpenAI

```bash
export OPENAI_API_KEY="sk-..."
```

#### Anthropic

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Confluence Configuration

```bash
export CONFLUENCE_URL="https://yourcompany.atlassian.net"
export CONFLUENCE_USERNAME="your-email@company.com"
export CONFLUENCE_API_TOKEN="your-api-token"
export CONFLUENCE_SPACE_KEY="TEAM"
```

### Security Configuration

```bash
export THREADCRUMB_ENCRYPTION_KEY="base64-encoded-key"
export THREADCRUMB_REDACT_PII="true"
```

## AI Provider Configuration

### AWS Bedrock

AWS Bedrock provides access to Claude and other foundation models.

#### Prerequisites

1. AWS account with Bedrock access
2. Model access enabled in your AWS region
3. AWS credentials configured

#### Configuration

```yaml
ai:
  provider: "bedrock"
  region: "us-east-1"
  model_name: "anthropic.claude-3-sonnet-20240229-v1:0"
  max_tokens: 4096
  temperature: 0.7
  aws_profile: "your-profile"  # Optional
```

#### Available Models

- `anthropic.claude-3-opus-20240229-v1:0` - Most capable, higher cost
- `anthropic.claude-3-sonnet-20240229-v1:0` - Balanced performance/cost
- `anthropic.claude-3-haiku-20240307-v1:0` - Fastest, lower cost
- `anthropic.claude-v2:1` - Previous generation

#### CLI Usage

```bash
threadcrumb generate --ai-provider bedrock
```

### OpenAI

Access GPT-4 and GPT-3.5 models.

#### Prerequisites

1. OpenAI API key from https://platform.openai.com/api-keys

#### Installation

```bash
pip install threadcrumb[ai-openai]
```

#### Configuration

```yaml
ai:
  provider: "openai"
  openai_api_key: "sk-..."
  openai_model: "gpt-4-turbo-preview"
  max_tokens: 4096
  temperature: 0.7
```

Or use environment variable:

```bash
export OPENAI_API_KEY="sk-..."
```

#### Available Models

- `gpt-4-turbo-preview` - Most capable
- `gpt-4` - Standard GPT-4
- `gpt-3.5-turbo` - Faster, lower cost

#### CLI Usage

```bash
threadcrumb generate --ai-provider openai
```

### Anthropic

Direct access to Claude models via Anthropic API.

#### Prerequisites

1. Anthropic API key from https://console.anthropic.com/

#### Installation

```bash
pip install threadcrumb[ai-anthropic]
```

#### Configuration

```yaml
ai:
  provider: "anthropic"
  anthropic_api_key: "sk-ant-..."
  anthropic_model: "claude-3-opus-20240229"
  max_tokens: 4096
  temperature: 0.7
```

Or use environment variable:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

#### Available Models

- `claude-3-opus-20240229` - Most capable
- `claude-3-sonnet-20240229` - Balanced
- `claude-3-haiku-20240307` - Fastest

#### CLI Usage

```bash
threadcrumb generate --ai-provider anthropic
```

## Performance Settings

### Parallel Processing

Process multiple channels concurrently for faster exports.

#### Configuration

```yaml
performance:
  parallel_workers: 4  # Number of concurrent workers
```

#### CLI Usage

```bash
# Enable parallel processing with default workers (4)
threadcrumb generate --parallel

# Specify number of workers
threadcrumb generate --parallel --max-workers 8
```

#### Recommendations

- **Small workspaces** (< 10 channels): 2-4 workers
- **Medium workspaces** (10-50 channels): 4-8 workers
- **Large workspaces** (50+ channels): 8-16 workers

### SQLite Cache

Use database caching instead of file-based caching for better performance.

#### Configuration

```yaml
performance:
  use_sqlite_cache: true
```

#### CLI Usage

```bash
threadcrumb generate --use-sqlite-cache
```

#### Benefits

- **Faster lookups** - Indexed queries vs. file reads
- **Less I/O** - Single database file vs. many small files
- **Better concurrency** - SQLite handles concurrent access
- **Query capabilities** - SQL-based filtering and stats

### Export Resumption

Resume interrupted exports from checkpoints.

#### CLI Usage

```bash
# Start export
threadcrumb generate --parallel

# If interrupted, resume with:
threadcrumb generate --resume
```

Checkpoints are stored in `~/.threadcrumb/checkpoints/` and include:
- Processed channels
- Progress percentage
- Error information
- Timestamp

## Security Configuration

### PII Detection and Redaction

Automatically detect and remove sensitive information.

#### Supported PII Types

- Email addresses
- Phone numbers
- Social Security Numbers (SSN)
- Credit card numbers
- IP addresses
- API keys and tokens
- AWS keys
- GitHub tokens
- Passwords
- URLs
- Dates of birth

#### Configuration

```yaml
security:
  enable_pii_detection: true
  redact_pii: true
```

#### CLI Usage

```bash
threadcrumb generate --redact-pii
```

#### Redaction Strategies

- **PLACEHOLDER**: Replace with `[EMAIL]`, `[PHONE]`, etc. (default)
- **MASK**: Replace with `a****@*****.com`
- **HASH**: Replace with hash like `[EMAIL:a1b2c3d4]`
- **REMOVE**: Remove entirely

### Cache Encryption

Encrypt cached data at rest using AES-128.

#### Prerequisites

```bash
pip install threadcrumb[security]
```

#### Configuration

```yaml
security:
  encrypt_cache: true
```

#### CLI Usage

```bash
threadcrumb generate --encrypt-cache
```

#### Key Management

Encryption keys are stored in `~/.threadcrumb/encryption.key` with restrictive permissions (0600).

To use a custom key:

```bash
export THREADCRUMB_ENCRYPTION_KEY="your-base64-encoded-key"
```

### Audit Logging

Track all operations for compliance.

#### Configuration

```yaml
security:
  audit_logging: true
  audit_log_path: "~/.threadcrumb/audit.log"
```

#### Logged Events

- Authentication success/failure
- Data access and exports
- PII detection and redaction
- Configuration changes
- Errors and failures

#### Log Format

JSON lines format:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "event_type": "data_export",
  "level": "info",
  "message": "Exported 5 channels (42 threads) in markdown format",
  "user": "user@company.com",
  "metadata": {
    "format": "markdown",
    "channel_count": 5,
    "thread_count": 42
  }
}
```

## Cache Configuration

### File-Based Cache (Default)

```yaml
slack:
  cache_dir: "~/.threadcrumb/cache"
```

#### Structure

```
~/.threadcrumb/cache/
├── messages/
│   ├── C12345.json
│   └── C67890.json
├── channels.json
└── users.json
```

### SQLite Cache

```yaml
performance:
  use_sqlite_cache: true
```

#### Database Schema

```sql
CREATE TABLE messages (
    ts TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    user_id TEXT,
    text TEXT,
    thread_ts TEXT,
    reply_count INTEGER,
    data TEXT  -- Full message JSON
);

CREATE INDEX idx_channel ON messages(channel_id);
CREATE INDEX idx_thread ON messages(thread_ts);
```

### Cache Management

```bash
# Clear file cache
rm -rf ~/.threadcrumb/cache/

# Clear SQLite cache
rm ~/.threadcrumb/cache.db

# Clear checkpoints
rm -rf ~/.threadcrumb/checkpoints/
```

## Advanced Configuration

### Custom Templates

Override default output templates:

```yaml
output:
  template_dir: "~/mythreadcrumb-templates"
```

### Rate Limiting

Adjust Slack API rate limiting:

```yaml
slack:
  rate_limit_delay: 1.0  # Seconds between requests
  max_retries: 3         # Max retry attempts
```

### Processing Filters

Control what content gets processed:

```yaml
processing:
  min_message_length: 10      # Skip very short messages
  max_thread_depth: 50        # Limit thread nesting
  thread_reconstruction: true # Reconstruct threaded conversations
```

## Troubleshooting

### AI Provider Issues

**Problem**: AI provider connection fails

**Solutions**:
1. Check API credentials
2. Verify model access/availability
3. Check region settings (Bedrock)
4. Test with fallback mode: `--no-ai`

### Performance Issues

**Problem**: Export is slow

**Solutions**:
1. Enable parallel processing: `--parallel`
2. Use SQLite cache: `--use-sqlite-cache`
3. Increase workers: `--max-workers 8`
4. Disable AI temporarily: `--no-ai`

### Cache Issues

**Problem**: Cache corruption or errors

**Solutions**:
1. Clear cache and retry
2. Switch to SQLite cache
3. Disable caching: `--no-cache`

## See Also

- [Performance Guide](PERFORMANCE.md)
- [Security Guide](SECURITY.md)
- [Docker Guide](DOCKER.md)
- [Confluence Export](CONFLUENCE_EXPORT.md)

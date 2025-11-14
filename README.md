# ThreadCrumb

AI-powered Slack workspace analyzer and wiki generator. ThreadCrumb connects to your Slack workspaces, analyzes channel history, and generates structured, interlinked wikis or FAQs using AWS Bedrock AI for intelligent content organization.

## Features

### 🔐 Slack Integration
- **OAuth 2.0 Authentication** with configurable scopes
- **Multi-channel support** with selective inclusion/exclusion
- **Incremental sync** with timestamp-based updates
- **Rate limit handling** with exponential backoff
- **File attachment processing** with local caching

### 🤖 AI Integration (Multiple Providers)
- **Multiple AI providers** - AWS Bedrock, OpenAI, and Anthropic
- **Model flexibility** - configurable AI model selection (Claude 3, GPT-4, etc.)
- **Content categorization** with custom taxonomies
- **Topic extraction** and clustering
- **Summary generation** for threads and channels
- **Q&A pair generation** from discussions
- **Sentiment/importance scoring** for content prioritization
- **Fallback mode** when AI services are unavailable

### ⚡ Performance & Scalability
- **Parallel processing** - process multiple channels concurrently
- **SQLite caching** - efficient database caching for better performance
- **Export resumption** - resume interrupted exports with checkpoints
- **Incremental sync** - only fetch new messages since last sync

### 🔍 Search & Discovery
- **Full-text search indexing** - build searchable indices of your content
- **Whoosh integration** - optional advanced search capabilities
- **Search command** - query your wiki from the CLI

### 🎨 User Experience
- **Interactive mode** - guided workflows with rich TUI
- **Progress tracking** - real-time progress bars and status
- **Colored output** - better readability with syntax highlighting

### 🔒 Security & Compliance
- **PII detection** - automatic detection of sensitive information
- **Content redaction** - mask or remove PII from exports
- **Encryption at rest** - encrypt cached data with AES-128
- **Audit logging** - comprehensive activity logging for compliance

### 📊 Content Processing Pipeline
```
Raw Messages → Thread Reconstruction → AI Analysis → Structured Content → Interlinked Wiki
```

### 📝 Output Formats
- **Markdown wiki** with hierarchical navigation
- **Static HTML site** with search functionality
- **JSON/XML** structured data for external processing
- **Plain text export** with basic formatting

## Installation

### Prerequisites

- Python 3.9 or higher
- AWS account with Bedrock access (for AI features)
- Slack workspace with admin privileges

### Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/threadcrumb.git
cd threadcrumb

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package (basic features)
pip install -e .

# Or install with all optional features
pip install -e .[all]
```

### Optional Features

Install specific feature sets as needed:

```bash
# Search functionality with Whoosh
pip install threadcrumb[search]

# OpenAI integration
pip install threadcrumb[ai-openai]

# Anthropic (Claude) integration
pip install threadcrumb[ai-anthropic]

# Interactive mode with rich TUI
pip install threadcrumb[interactive]

# Security features (encryption, PII detection)
pip install threadcrumb[security]

# All features
pip install threadcrumb[all]
```

## Quick Start

### 1. Configure AWS Credentials

Set up AWS credentials for Bedrock access:

```bash
# Using AWS CLI
aws configure

# Or set environment variables
export AWS_REGION=us-east-1
export AWS_PROFILE=your-profile
```

### 2. Create Slack App

1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app "From scratch"
3. Add OAuth scopes under **OAuth & Permissions**:
   - `channels:history`
   - `channels:read`
   - `groups:history`
   - `groups:read`
   - `users:read`
   - `team:read`
   - `files:read`
4. Note your **Client ID** and **Client Secret**

### 3. Authenticate with Slack

```bash
threadcrumb auth
```

Follow the prompts to enter your Slack app credentials. A browser window will open for OAuth authorization.

### 4. Generate Wiki

```bash
# Generate Markdown wiki from all channels
threadcrumb generate

# Generate HTML wiki from specific channels
threadcrumb generate --channels "general,dev-team" --format html

# Generate without AI (faster, basic export)
threadcrumb generate --no-ai --format markdown
```

## Usage

### Commands

#### `threadcrumb auth`
Authenticate with your Slack workspace.

```bash
threadcrumb auth [OPTIONS]
```

**Options:**
- `--client-id TEXT` - Slack app client ID
- `--client-secret TEXT` - Slack app client secret
- `--port INTEGER` - OAuth callback port (default: 8000)

#### `threadcrumb generate`
Generate wiki from Slack workspace.

```bash
threadcrumb generate [OPTIONS]
```

**Options:**
- `--channels TEXT` - Comma-separated list of channels (default: all)
- `--exclude TEXT` - Comma-separated list of channels to exclude
- `--output PATH` - Output directory (default: ./output)
- `--format [markdown|html|json|xml]` - Output format (default: markdown)
- `--no-ai` - Disable AI processing (faster)
- `--no-cache` - Disable message caching
- `--parallel` - Process channels in parallel for better performance
- `--max-workers INTEGER` - Max parallel workers (default: 4)
- `--interactive, -i` - Interactive mode with guided prompts
- `--build-index` - Build search index after generation
- `--ai-provider [bedrock|openai|anthropic]` - AI provider to use (default: bedrock)
- `--use-sqlite-cache` - Use SQLite cache instead of file cache
- `--resume` - Resume previous interrupted export
- `--redact-pii` - Detect and redact PII from exports
- `--encrypt-cache` - Encrypt cached data at rest

**Examples:**

```bash
# Generate Markdown wiki from all channels
threadcrumb generate

# Interactive mode with guided selection
threadcrumb generate --interactive

# Parallel processing with search indexing
threadcrumb generate --parallel --build-index

# Use OpenAI with PII redaction
threadcrumb generate --ai-provider openai --redact-pii

# Resume interrupted export
threadcrumb generate --resume

# High-performance export with all features
threadcrumb generate --parallel --max-workers 8 --use-sqlite-cache --build-index

# Secure export with encryption and PII redaction
threadcrumb generate --redact-pii --encrypt-cache --format html
```

#### `threadcrumb export-confluence`
Export wiki directly to Confluence.

```bash
threadcrumb export-confluence [OPTIONS]
```

**Options:**
- `--channels TEXT` - Comma-separated list of channels (default: all)
- `--exclude TEXT` - Comma-separated list of channels to exclude
- `--no-ai` - Disable AI processing
- `--no-cache` - Disable message caching
- `--confluence-url TEXT` - Confluence base URL
- `--username TEXT` - Confluence username
- `--api-token TEXT` - Confluence API token
- `--space-key TEXT` - Confluence space key
- `--parent-page-id TEXT` - Parent page ID for wiki root
- `--structure [flat|hierarchical|by-category]` - Page organization
- `--dry-run` - Preview without creating pages

**Examples:**

```bash
# Export to Confluence Cloud
threadcrumb export-confluence \
  --confluence-url https://mycompany.atlassian.net \
  --username me@mycompany.com \
  --api-token my-token \
  --space-key TEAM

# Export specific channels with dry run
threadcrumb export-confluence --channels "general,dev" --dry-run

# Export organized by category
threadcrumb export-confluence --structure by-category
```

See [Confluence Export Guide](docs/CONFLUENCE_EXPORT.md) for detailed documentation.

#### `threadcrumb search`
Search the generated wiki content.

```bash
threadcrumb search QUERY [OPTIONS]
```

**Arguments:**
- `QUERY` - Search query string

**Options:**
- `--index-path PATH` - Path to search index (default: output/search_index.json)
- `--limit INTEGER` - Maximum results to return (default: 10)

**Examples:**

```bash
# Search for a topic
threadcrumb search "authentication"

# Search with custom index path
threadcrumb search "database" --index-path ./wiki/search_index.json

# Limit results
threadcrumb search "error" --limit 5
```

Note: Generate search index with `--build-index` flag when running `threadcrumb generate`.

#### `threadcrumb list-channels`
List all channels in workspace.

```bash
threadcrumb list-channels
```

#### `threadcrumb config-init`
Initialize configuration file.

```bash
threadcrumb config-init
```

### Configuration

ThreadCrumb uses a YAML configuration file located at `~/.threadcrumb/config.yaml`.

Initialize with default settings:

```bash
threadcrumb config-init
```

**Example configuration:**

```yaml
slack:
  access_token: null
  workspace_id: null
  channels: []
  exclude_channels: []
  rate_limit_delay: 1.0
  max_retries: 3
  cache_enabled: true
  cache_dir: .threadcrumb/cache

ai:
  provider: bedrock
  model_name: anthropic.claude-3-sonnet-20240229-v1:0
  region: us-east-1
  max_tokens: 4096
  temperature: 0.7
  fallback_enabled: true
  aws_profile: null

processing:
  thread_reconstruction: true
  include_attachments: true
  min_message_length: 10
  max_thread_depth: 50
  categorization_enabled: true
  topic_extraction_enabled: true
  summary_enabled: true
  qa_generation_enabled: true
  sentiment_analysis: false
  importance_scoring: true

output:
  format: markdown
  output_dir: output
  create_index: true
  interlink_pages: true
  include_search: true
  include_toc: true
  date_format: '%Y-%m-%d %H:%M:%S'
```

### Environment Variables

You can override configuration with environment variables:

```bash
# Slack configuration
export SLACK_CLIENT_ID=your-client-id
export SLACK_CLIENT_SECRET=your-client-secret
export SLACK_ACCESS_TOKEN=your-access-token

# AWS configuration
export AWS_REGION=us-east-1
export AWS_PROFILE=your-profile
export AI_MODEL=anthropic.claude-3-haiku-20240307-v1:0
```

## Output Formats

### Markdown Wiki

Organized directory structure with interlinked pages:

```
output/
├── README.md              # Main index
├── categories.md          # Category index
├── topics.md             # Topic index
├── faq.md                # Generated FAQ
├── general/              # Channel directory
│   ├── README.md         # Channel overview
│   └── thread-*.md       # Individual threads
└── engineering/
    ├── README.md
    └── thread-*.md
```

### HTML Static Site

Self-contained website with search:

```
output/
├── index.html            # Home page
├── channels.html         # Channel list
├── categories.html       # Category index
├── topics.html          # Topic index
├── faq.html             # FAQ page
├── channel_*.html       # Channel pages
└── thread_*.html        # Thread pages
```

### JSON Export

Structured data with indices:

```json
{
  "metadata": {
    "channel_count": 5,
    "total_threads": 123,
    "export_version": "1.0"
  },
  "channels": [...],
  "indices": {
    "categories": {...},
    "topics": {...},
    "qa_pairs": [...]
  }
}
```

### XML Export

Similar structure to JSON, formatted as XML with proper hierarchy.

### Confluence Export (API)

Direct export to Confluence Cloud or Server:

```bash
threadcrumb export-confluence \
  --confluence-url https://yourcompany.atlassian.net \
  --username your.email@company.com \
  --api-token your-api-token \
  --space-key TEAM
```

Features:
- Automatic page creation and updates
- Native Confluence formatting
- Interactive macros (TOC, expand, info panels)
- Auto-labeling for organization
- Multiple structure options (flat, hierarchical, by-category)

See [Confluence Export Guide](docs/CONFLUENCE_EXPORT.md) for detailed setup.

## Advanced Usage

### Customizing AI Models

Edit your config file to use different Bedrock models:

```yaml
ai:
  model_name: anthropic.claude-3-haiku-20240307-v1:0  # Faster, cheaper
  # or
  model_name: anthropic.claude-3-opus-20240229-v1:0   # More powerful
```

### Selective Channel Processing

```bash
# Process only specific channels
threadcrumb generate --channels "general,announcements,dev-team"

# Process all except specific channels
threadcrumb generate --exclude "spam,test-channel"
```

### Incremental Updates

ThreadCrumb caches messages locally. Re-running will use cached data:

```bash
# Use cached messages (faster)
threadcrumb generate

# Force fresh fetch
threadcrumb generate --no-cache
```

### Batch Processing

For large workspaces, process channels in batches:

```bash
# Batch 1
threadcrumb generate --channels "chan1,chan2,chan3" --output ./batch1

# Batch 2
threadcrumb generate --channels "chan4,chan5,chan6" --output ./batch2
```

## Troubleshooting

### AWS Bedrock Access

If you get authentication errors:

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check Bedrock model access
aws bedrock list-foundation-models --region us-east-1
```

### Slack Rate Limits

If you hit rate limits:

1. Increase `rate_limit_delay` in config
2. Process fewer channels at once
3. Use cached data when possible

### Missing Dependencies

```bash
# Reinstall all dependencies
pip install -e ".[dev]"
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=threadcrumb
```

### Code Formatting

```bash
# Format code
black threadcrumb/

# Lint
flake8 threadcrumb/

# Type checking
mypy threadcrumb/
```

## Architecture

```
threadcrumb/
├── slack/           # Slack API integration
│   ├── auth.py      # OAuth authentication
│   ├── client.py    # API client with rate limiting
│   └── messages.py  # Message fetching & thread reconstruction
├── ai/              # AI integration
│   ├── bedrock.py   # AWS Bedrock client
│   └── processor.py # Content analysis & processing
├── processing/      # Content processing pipeline
│   └── pipeline.py  # Main processing logic
├── output/          # Output formatters
│   ├── markdown.py  # Markdown formatter
│   ├── html.py      # HTML formatter
│   └── structured.py # JSON/XML formatters
├── utils/           # Utilities
│   ├── logging.py   # Logging setup
│   └── progress.py  # Progress tracking
├── config.py        # Configuration management
└── cli.py           # Command-line interface
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [Slack SDK](https://slack.dev/python-slack-sdk/)
- AI powered by [AWS Bedrock](https://aws.amazon.com/bedrock/)
- CLI built with [Click](https://click.palletsprojects.com/)

## Support

For issues and questions:
- GitHub Issues: [Report a bug](https://github.com/yourusername/threadcrumb/issues)
- Documentation: [Read the docs](https://github.com/yourusername/threadcrumb/wiki)

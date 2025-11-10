# Confluence Export Guide

ThreadCrumb can export your Slack wiki directly to Confluence Cloud or Server using the Confluence REST API. This guide covers setup, configuration, and usage.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Getting Confluence API Token](#getting-confluence-api-token)
- [Configuration](#configuration)
- [Basic Usage](#basic-usage)
- [Advanced Usage](#advanced-usage)
- [Page Organization](#page-organization)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Confluence Cloud or Server/Data Center instance
- Confluence space where you have edit permissions
- API token (Cloud) or password (Server)
- ThreadCrumb installed and Slack authentication completed

## Getting Confluence API Token

### For Confluence Cloud

1. Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Give it a label (e.g., "ThreadCrumb")
4. Copy the token (you won't be able to see it again!)

### For Confluence Server/Data Center

Use your Confluence password as the API token.

## Configuration

### Method 1: Configuration File

Edit `~/.threadcrumb/config.yaml`:

```yaml
confluence:
  # Base URL for your Confluence instance
  base_url: https://yourcompany.atlassian.net

  # Username (email for Cloud, username for Server)
  username: your.email@company.com

  # API token (from Atlassian Account Settings)
  api_token: your-api-token-here

  # Space key where wiki will be created
  space_key: TEAM

  # Use Cloud API (true) or Server API (false)
  use_cloud: true

  # Root page title for your wiki
  root_page_title: "Slack Wiki"

  # Optional: Parent page ID to nest wiki under
  parent_page_id: null

  # Page organization structure (flat, hierarchical, by-category)
  structure: flat

  # Add labels to pages for better organization
  add_labels: true

  # Dry run mode (test without creating pages)
  dry_run: false
```

### Method 2: Environment Variables

```bash
export CONFLUENCE_URL=https://yourcompany.atlassian.net
export CONFLUENCE_USERNAME=your.email@company.com
export CONFLUENCE_API_TOKEN=your-api-token-here
export CONFLUENCE_SPACE_KEY=TEAM
```

### Method 3: Command Line Options

Pass credentials directly via CLI (overrides config and env vars):

```bash
threadcrumb export-confluence \
  --confluence-url https://yourcompany.atlassian.net \
  --username your.email@company.com \
  --api-token your-api-token-here \
  --space-key TEAM
```

## Basic Usage

### Export All Channels

```bash
threadcrumb export-confluence
```

This will:
1. Connect to Slack and fetch all channels
2. Process messages and threads
3. Analyze content with AI
4. Create pages in your Confluence space

### Export Specific Channels

```bash
threadcrumb export-confluence --channels "general,engineering,product"
```

### Exclude Channels

```bash
threadcrumb export-confluence --exclude "private,test"
```

### Quick Export Without AI

For faster exports without AI analysis:

```bash
threadcrumb export-confluence --no-ai
```

## Advanced Usage

### Dry Run Mode

Test the export without actually creating pages:

```bash
threadcrumb export-confluence --dry-run
```

This will:
- Process all channels
- Show what pages would be created
- NOT actually create any pages in Confluence

### Different Page Organizations

#### Flat Structure (Default)

```bash
threadcrumb export-confluence --structure flat
```

Creates:
```
Slack Wiki (root)
├── general Channel
│   ├── Thread 1
│   ├── Thread 2
│   └── Thread 3
├── engineering Channel
│   ├── Thread 1
│   └── Thread 2
├── Categories
├── Topics
└── FAQ
```

#### Hierarchical Structure

```bash
threadcrumb export-confluence --structure hierarchical
```

Same as flat, with deeper nesting for better organization.

#### By Category

```bash
threadcrumb export-confluence --structure by-category
```

Organizes threads by AI-detected categories:

```
Slack Wiki (root)
├── Category: Technical Discussion
│   ├── Thread 1
│   ├── Thread 2
│   └── Thread 3
├── Category: Bug Reports
│   ├── Thread 1
│   └── Thread 2
├── Category: Feature Requests
│   └── Thread 1
└── FAQ
```

### Nest Under Existing Page

To create your wiki under an existing Confluence page:

```bash
# Find parent page ID in Confluence URL:
# https://yourcompany.atlassian.net/wiki/spaces/TEAM/pages/123456/Parent+Page
# Parent page ID is: 123456

threadcrumb export-confluence --parent-page-id 123456
```

### Update Existing Wiki

ThreadCrumb automatically updates existing pages if they already exist:

```bash
# First export
threadcrumb export-confluence

# Update later with new content
threadcrumb export-confluence
```

Pages with the same title will be updated instead of duplicated.

## Page Organization

### Generated Pages

ThreadCrumb creates the following page structure:

1. **Root Page** - Main wiki homepage with statistics and navigation
2. **Channel Pages** - Overview page for each channel
3. **Thread Pages** - Individual thread discussions with:
   - AI-generated summary
   - Categories and topics (as labels)
   - Key points
   - Q&A pairs (in expandable sections)
   - Full conversation
4. **Categories Page** - Index of threads by category
5. **Topics Page** - Index of threads by topic
6. **FAQ Page** - Top questions and answers from all threads

### Page Features

Each page includes:

- **Table of Contents** - Auto-generated navigation
- **Metadata Panels** - Thread information, statistics
- **Status Lozenges** - Visual category/topic indicators
- **Expandable Sections** - Q&A pairs collapse for readability
- **Cross-Links** - Related thread references
- **Labels** - Automatic labeling for search and filtering

### Labels

Pages are automatically labeled with:

- `slack-wiki` - All generated pages
- `slack-channel` - Channel overview pages
- `slack-thread` - Individual thread pages
- Category names (e.g., `bug-report`, `feature-request`)
- `faq` - FAQ page
- `index` - Index pages

## Troubleshooting

### Authentication Errors

**Error: 401 Unauthorized**

- Check your API token is correct
- For Cloud: Ensure you're using your email address as username
- For Server: Ensure you're using your username (not email)
- Verify token hasn't expired

**Error: 403 Forbidden**

- Check you have edit permissions in the space
- Verify the space key is correct
- Confirm you can create pages manually in the space

### Connection Errors

**Error: Connection refused**

- Check base URL is correct
- For Cloud: URL should be `https://yourcompany.atlassian.net`
- For Server: Include port if needed (e.g., `http://confluence.company.com:8090`)
- Verify `use_cloud` setting matches your Confluence type

### Page Creation Errors

**Error: Page title already exists**

- This is normal - ThreadCrumb will update the existing page
- Use `--dry-run` to preview without creating pages

**Error: Parent page not found**

- Verify the parent page ID exists
- Check you have access to the parent page
- Try without `--parent-page-id` to create at space root

### Content Issues

**Missing AI Analysis**

- Ensure AWS Bedrock is configured
- Check AI token limits haven't been exceeded
- Try without `--no-ai` flag

**Pages are Empty**

- Check channel has enough messages
- Verify thread reconstruction is enabled
- Lower `min_message_length` in config

## Best Practices

### 1. Start with Dry Run

Always test first:

```bash
threadcrumb export-confluence --dry-run
```

### 2. Start Small

Begin with one or two channels:

```bash
threadcrumb export-confluence --channels "general"
```

### 3. Use Staging Space

Create a test space first to verify formatting and structure.

### 4. Schedule Regular Updates

Use cron to keep wiki up-to-date:

```bash
# Daily at 2 AM
0 2 * * * /path/to/venv/bin/threadcrumb export-confluence
```

### 5. Monitor API Rate Limits

Confluence has rate limits:
- Cloud: ~100 requests/minute per user
- Server: Varies by configuration

For large wikis, consider:
- Processing fewer channels at a time
- Increasing `rate_limit_delay` in Slack config
- Running during off-hours

## Complete Example

```bash
# 1. Configure Confluence
export CONFLUENCE_URL=https://mycompany.atlassian.net
export CONFLUENCE_USERNAME=me@mycompany.com
export CONFLUENCE_API_TOKEN=my-secret-token
export CONFLUENCE_SPACE_KEY=ENG

# 2. Test with dry run
threadcrumb export-confluence \
  --channels "engineering,product" \
  --structure by-category \
  --dry-run

# 3. Review output, then export for real
threadcrumb export-confluence \
  --channels "engineering,product" \
  --structure by-category

# 4. Check Confluence
# Visit: https://mycompany.atlassian.net/wiki/spaces/ENG
```

## API Reference

For programmatic usage:

```python
from threadcrumb.confluence import export_to_confluence
from threadcrumb.processing import ContentPipeline

# ... process your channels ...

page_map = export_to_confluence(
    channels=processed_channels,
    confluence_url="https://mycompany.atlassian.net",
    username="me@mycompany.com",
    api_token="token",
    space_key="TEAM",
    root_page_title="My Wiki",
    structure="by-category",
    dry_run=False,
    use_cloud=True
)

# page_map is a dict mapping page titles to page IDs
print(f"Created {len(page_map)} pages")
```

## Support

For issues or questions:
- Check [Troubleshooting](#troubleshooting) section
- Review [Confluence REST API docs](https://developer.atlassian.com/cloud/confluence/rest/v2/)
- Open an issue on GitHub

## Next Steps

- Customize page templates in `threadcrumb/confluence/storage_format.py`
- Add custom macros or formatting
- Integrate with Confluence automation rules
- Set up page watchers for notifications

# Slackcrumb

Playwright-based Slack history exporter for users without API access.

## Install

```bash
cd slackcrumb
pip install -e .
playwright install chromium
```

## Quick Start

```bash
# 1. Log in (opens browser for manual SSO/password login)
slackcrumb login --workspace-url https://your-team.slack.com

# 2. List visible channels
slackcrumb channels --workspace-url https://your-team.slack.com

# 3. Scrape channels
slackcrumb scrape --channels general --format json --oldest-date 2025-09-01

# 4. Search-based scrape
slackcrumb scrape --search "pendo" --format markdown --workspace-url https://your-team.slack.com

# 5. Resume interrupted export
slackcrumb status
slackcrumb scrape --resume <export-id>
```

## Commands

| Command | Purpose |
|---------|---------|
| `slackcrumb login` | Manual browser login; session persists across runs |
| `slackcrumb channels` | List all channels visible in the sidebar |
| `slackcrumb scrape` | Scrape channels or search results |
| `slackcrumb status` | List resumable exports |
| `slackcrumb config-init` | Create default config at `~/.slackcrumb/config.yaml` |

## Scrape Options

- `--channels` / `-ch` — Channel names (repeatable)
- `--search` / `-s` — Search query
- `--oldest-date` — Stop at this date (YYYY-MM-DD, inclusive)
- `--newest-date` — Skip messages after this date (YYYY-MM-DD, inclusive)
- `--exclude-bots` / `--include-bots` — Skip messages from Slack apps and bots (default: include)
- `--format` / `-f` — `json` or `markdown`
- `--output` / `-o` — Output directory
- `--split-by month` — Write one file per month under `<output>/<year>/`, named `<channel>_<YYYY-MM>`
- `--headless` / `--no-headless` — Browser visibility
- `--expand-threads` / `--no-expand-threads` — Scrape thread replies
- `--resume` — Resume by export ID

### Example: monthly knowledge-base export

```bash
slackcrumb scrape --channels studio \
  --oldest-date 2024-01-01 --newest-date 2024-06-30 \
  --exclude-bots --format markdown \
  --output slack_knowledge_base --split-by month
```

This writes `slack_knowledge_base/2024/studio_2024-01.md` through `studio_2024-06.md` in one run — no per-month reruns needed. Threads stay grouped under the month of their parent message.

## How It Works

1. Uses Playwright's persistent browser context (cookies survive across runs)
2. User logs in manually once via the real browser
3. Scrolls channel history upward, parsing messages from the DOM
4. Optionally expands threads by clicking reply indicators
5. Saves checkpoints after each batch for crash recovery
6. Outputs structured JSON or readable Markdown

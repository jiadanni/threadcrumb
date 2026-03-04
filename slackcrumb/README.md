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

# 2. Scrape channels
slackcrumb scrape --channels general --format json --oldest-date 2025-09-01

# 3. Search-based scrape
slackcrumb scrape --search "pendo" --format markdown --workspace-url https://your-team.slack.com

# 4. Resume interrupted export
slackcrumb status
slackcrumb scrape --resume <export-id>
```

## Commands

| Command | Purpose |
|---------|---------|
| `slackcrumb login` | Manual browser login; session persists across runs |
| `slackcrumb scrape` | Scrape channels or search results |
| `slackcrumb status` | List resumable exports |
| `slackcrumb config-init` | Create default config at `~/.slackcrumb/config.yaml` |

## Scrape Options

- `--channels` / `-ch` — Channel names (repeatable)
- `--search` / `-s` — Search query
- `--oldest-date` — Stop at this date (YYYY-MM-DD)
- `--format` / `-f` — `json` or `markdown`
- `--output` / `-o` — Output directory
- `--headless` / `--no-headless` — Browser visibility
- `--expand-threads` / `--no-expand-threads` — Scrape thread replies
- `--resume` — Resume by export ID

## How It Works

1. Uses Playwright's persistent browser context (cookies survive across runs)
2. User logs in manually once via the real browser
3. Scrolls channel history upward, parsing messages from the DOM
4. Optionally expands threads by clicking reply indicators
5. Saves checkpoints after each batch for crash recovery
6. Outputs structured JSON or readable Markdown

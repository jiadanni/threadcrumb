"""Click CLI for Slackcrumb."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import click
from colorama import Fore, Style

from . import __version__
from .checkpoint import Checkpoint
from .config import DEFAULT_CONFIG_PATH, SlackcrumbConfig, ensure_dirs
from .exceptions import SlackcrumbError
from .utils.logging import setup_logging


@click.group()
@click.version_option(__version__)
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
@click.option("-c", "--config", "config_path", type=click.Path(), default=None,
              help="Path to config YAML file.")
@click.pass_context
def cli(ctx, verbose, config_path):
    """Slackcrumb — Playwright-based Slack history exporter."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["logger"] = setup_logging(verbose)
    ctx.obj["config"] = SlackcrumbConfig.load(Path(config_path) if config_path else None)
    ensure_dirs()


@cli.command()
@click.option("--workspace-url", required=True, help="Slack workspace URL (e.g. https://myteam.slack.com)")
@click.pass_context
def login(ctx, workspace_url):
    """Open browser for manual Slack login. Session is persisted."""
    config = ctx.obj["config"]
    config.workspace_url = workspace_url
    config.browser.headless = False  # must be visible for manual login

    async def _login():
        from .browser.session import BrowserSession
        from .browser.auth import wait_for_login

        session = BrowserSession(config.browser)
        try:
            await session.start()
            page = await session.new_page()
            await wait_for_login(page, workspace_url)
            click.echo(f"{Fore.GREEN}Login successful! Session saved.{Style.RESET_ALL}")
        except SlackcrumbError as e:
            click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}", err=True)
            sys.exit(1)
        finally:
            await session.close()

    asyncio.run(_login())


@cli.command()
@click.option("--channels", "-ch", multiple=True, help="Channel names to scrape.")
@click.option("--search", "-s", "search_query", help="Search query instead of channel scrape.")
@click.option("--oldest-date", help="Stop scrolling at this date (YYYY-MM-DD).")
@click.option("--format", "-f", "output_format", type=click.Choice(["json", "markdown"]),
              default="json", help="Output format.")
@click.option("--output", "-o", "output_dir", default=".", help="Output directory.")
@click.option("--headless/--no-headless", default=True, help="Run browser headlessly.")
@click.option("--resume", "resume_id", default=None, help="Resume a previous export by ID.")
@click.option("--expand-threads/--no-expand-threads", default=True,
              help="Expand and scrape thread replies.")
@click.option("--workspace-url", default=None, help="Override workspace URL from config.")
@click.pass_context
def scrape(ctx, channels, search_query, oldest_date, output_format, output_dir,
           headless, resume_id, expand_threads, workspace_url):
    """Scrape messages from Slack channels or search results."""
    config = ctx.obj["config"]
    logger = ctx.obj["logger"]

    if workspace_url:
        config.workspace_url = workspace_url
    if not config.workspace_url:
        click.echo(f"{Fore.RED}No workspace URL. Use --workspace-url or set it in config.{Style.RESET_ALL}", err=True)
        sys.exit(1)

    config.browser.headless = headless
    config.scrape.channels = list(channels)
    config.scrape.search_query = search_query
    config.scrape.oldest_date = oldest_date
    config.scrape.expand_threads = expand_threads
    config.output.format = output_format
    config.output.output_dir = output_dir

    if not channels and not search_query and not resume_id:
        click.echo(f"{Fore.RED}Specify --channels, --search, or --resume.{Style.RESET_ALL}", err=True)
        sys.exit(1)

    async def _scrape():
        from .browser.session import BrowserSession
        from .browser.auth import is_logged_in, wait_for_login
        from .scraper.channel import scrape_channel
        from .scraper.search import search_messages
        from .formatters.json_fmt import write_json
        from .formatters.markdown_fmt import write_markdown
        from .models import ExportResult

        # Set up checkpoint
        if resume_id:
            checkpoint = Checkpoint.load(resume_id)
            logger.info("Resuming export %s", resume_id)
            # Restore channels from checkpoint if not specified
            if not config.scrape.channels:
                config.scrape.channels = list(checkpoint.data.channels.keys())
            if checkpoint.data.search_query and not config.scrape.search_query:
                config.scrape.search_query = checkpoint.data.search_query
        else:
            checkpoint = Checkpoint(workspace_url=config.workspace_url)
            checkpoint.data.format = output_format
            if search_query:
                checkpoint.data.search_query = search_query
            checkpoint.save()

        click.echo(f"Export ID: {Fore.CYAN}{checkpoint.export_id}{Style.RESET_ALL}")

        session = BrowserSession(config.browser)
        try:
            await session.start()
            page = await session.new_page()

            # Check auth
            await page.goto(config.workspace_url, wait_until="domcontentloaded")
            if not await is_logged_in(page):
                click.echo(f"{Fore.YELLOW}Not logged in. Opening browser for login...{Style.RESET_ALL}")
                config.browser.headless = False
                await session.close()
                session = BrowserSession(config.browser)
                await session.start()
                page = await session.new_page()
                await wait_for_login(page, config.workspace_url)

            result = ExportResult(
                workspace=config.workspace_url,
                export_date=datetime.now().isoformat(),
            )

            if config.scrape.search_query:
                # Search mode
                messages = await search_messages(page, config.scrape.search_query, config.scrape)
                from .models import ChannelExport
                channel_export = ChannelExport(
                    name=f"search_{config.scrape.search_query[:20]}",
                    standalone_messages=messages,
                    total_messages=len(messages),
                    status="completed",
                    export_started=datetime.now().isoformat(),
                    export_finished=datetime.now().isoformat(),
                )
                result.channels.append(channel_export)
            else:
                # Channel mode
                for ch_name in config.scrape.channels:
                    try:
                        export = await scrape_channel(
                            page, config.workspace_url, ch_name, config.scrape, checkpoint
                        )
                        result.channels.append(export)
                        click.echo(
                            f"  {Fore.GREEN}#{ch_name}: {export.total_messages} messages{Style.RESET_ALL}"
                        )
                    except SlackcrumbError as e:
                        click.echo(f"  {Fore.RED}#{ch_name}: {e}{Style.RESET_ALL}", err=True)
                        logger.error("Channel %s failed: %s", ch_name, e)

            # Write output
            if output_format == "markdown":
                path = write_markdown(result, config.output)
            else:
                path = write_json(result, config.output)

            click.echo(f"\n{Fore.GREEN}Output written to: {path}{Style.RESET_ALL}")

        except SlackcrumbError as e:
            click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}", err=True)
            sys.exit(1)
        finally:
            await session.close()

    asyncio.run(_scrape())


@cli.command()
def status():
    """Show resumable scrape exports."""
    ensure_dirs()
    checkpoints = Checkpoint.find_resumable()
    if not checkpoints:
        click.echo("No resumable exports found.")
        return

    click.echo(f"\n{'ID':<14} {'Workspace':<35} {'Channels':<18} {'Updated':<22} {'Search'}")
    click.echo("-" * 100)
    for cp in checkpoints:
        search = cp.get("search_query") or ""
        click.echo(
            f"{cp['export_id']:<14} {cp['workspace']:<35} {cp['channels']:<18} "
            f"{cp['updated'][:19]:<22} {search}"
        )
    click.echo(f"\nResume with: slackcrumb scrape --resume <ID>")


@cli.command("config-init")
@click.option("--force", is_flag=True, help="Overwrite existing config.")
def config_init(force):
    """Create a default configuration file."""
    ensure_dirs()
    if DEFAULT_CONFIG_PATH.exists() and not force:
        click.echo(f"Config already exists at {DEFAULT_CONFIG_PATH}. Use --force to overwrite.")
        return

    config = SlackcrumbConfig()
    DEFAULT_CONFIG_PATH.write_text(config.to_yaml(), encoding="utf-8")
    click.echo(f"{Fore.GREEN}Config written to {DEFAULT_CONFIG_PATH}{Style.RESET_ALL}")

"""
Command-line interface for ThreadCrumb.
"""

import sys
import click
from pathlib import Path
from typing import Optional
import logging

from . import __version__
from .config import Config, load_config, get_default_config_path
from .slack import SlackAuthenticator, SlackClient, MessageFetcher, ThreadReconstructor
from .confluence import export_to_confluence
from .utils import setup_logging
from .utils.progress import ProgressTracker
from .ai import BedrockClient, AIProcessor
from .processing import ContentPipeline
from .search import SearchIndex
from .cli_commands import execute_generate_command

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__)
@click.option('--config', type=click.Path(exists=True), help='Path to configuration file')
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
@click.option('--log-file', type=click.Path(), help='Path to log file')
@click.pass_context
def cli(ctx, config, verbose, log_file):
    """ThreadCrumb - AI-powered Slack workspace analyzer and wiki generator."""
    # Setup logging
    setup_logging(
        level='DEBUG' if verbose else 'INFO',
        log_file=Path(log_file) if log_file else None,
        verbose=verbose
    )

    # Load configuration
    config_path = config or get_default_config_path()
    ctx.obj = load_config(str(config_path) if config_path else None)

    logger.info(f"ThreadCrumb v{__version__}")


@cli.command()
@click.option('--client-id', prompt='Slack Client ID', help='Slack app client ID')
@click.option('--client-secret', prompt='Slack Client Secret', hide_input=True, help='Slack app client secret')
@click.option('--port', default=8000, help='OAuth callback port')
@click.pass_obj
def auth(config: Config, client_id: str, client_secret: str, port: int):
    """Authenticate with Slack workspace."""
    try:
        authenticator = SlackAuthenticator(client_id, client_secret, port)

        click.echo("Starting Slack authentication...")
        token_data = authenticator.authenticate()

        # Save token
        token_path = Path.home() / ".threadcrumb" / "slack_token.json"
        authenticator.save_token(token_data, token_path)

        # Update config
        config.slack.access_token = token_data["access_token"]
        config.slack.workspace_id = token_data.get("team", {}).get("id")

        # Save config
        config_path = get_default_config_path()
        config.to_file(str(config_path))

        click.echo(click.style("✓ Authentication successful!", fg='green'))
        click.echo(f"Token saved to: {token_path}")
        click.echo(f"Config saved to: {config_path}")

    except Exception as e:
        click.echo(click.style(f"✗ Authentication failed: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.option('--channels', help='Comma-separated list of channels to fetch (leave empty for all)')
@click.option('--exclude', help='Comma-separated list of channels to exclude')
@click.option('--output', type=click.Path(), default='output', help='Output directory')
@click.option('--format', type=click.Choice(['markdown', 'html', 'json', 'xml']), default='markdown', help='Output format')
@click.option('--no-ai', is_flag=True, help='Disable AI processing (faster, basic export only)')
@click.option('--no-cache', is_flag=True, help='Disable message caching')
@click.option('--parallel', is_flag=True, help='Process channels in parallel for better performance')
@click.option('--max-workers', type=int, default=4, help='Max parallel workers (default: 4)')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode with guided prompts')
@click.option('--build-index', is_flag=True, help='Build search index after generation')
@click.option('--ai-provider', type=click.Choice(['bedrock', 'openai', 'anthropic']),
              default='bedrock', help='AI provider to use')
@click.option('--use-sqlite-cache', is_flag=True, help='Use SQLite cache instead of file cache')
@click.option('--resume', is_flag=True, help='Resume previous interrupted export')
@click.option('--redact-pii', is_flag=True, help='Detect and redact PII from exports')
@click.option('--encrypt-cache', is_flag=True, help='Encrypt cached data at rest')
@click.pass_obj
def generate(config: Config, channels: Optional[str], exclude: Optional[str],
             output: str, format: str, no_ai: bool, no_cache: bool,
             parallel: bool, max_workers: int, interactive: bool,
             build_index: bool, ai_provider: str, use_sqlite_cache: bool,
             resume: bool, redact_pii: bool, encrypt_cache: bool):
    """Generate wiki from Slack workspace."""
    execute_generate_command(
        config=config,
        channels=channels,
        exclude=exclude,
        output=output,
        format=format,
        no_ai=no_ai,
        no_cache=no_cache,
        parallel=parallel,
        max_workers=max_workers,
        interactive=interactive,
        build_index=build_index,
        ai_provider=ai_provider,
        use_sqlite_cache=use_sqlite_cache,
        resume=resume,
        redact_pii=redact_pii,
        encrypt_cache=encrypt_cache
    )


@cli.command()
@click.option('--channels', help='Comma-separated list of channels to export (leave empty for all)')
@click.option('--exclude', help='Comma-separated list of channels to exclude')
@click.option('--no-ai', is_flag=True, help='Disable AI processing')
@click.option('--no-cache', is_flag=True, help='Disable message caching')
@click.option('--confluence-url', help='Confluence base URL (or set CONFLUENCE_URL env var)')
@click.option('--username', help='Confluence username (or set CONFLUENCE_USERNAME env var)')
@click.option('--api-token', help='Confluence API token (or set CONFLUENCE_API_TOKEN env var)')
@click.option('--space-key', help='Confluence space key (or set CONFLUENCE_SPACE_KEY env var)')
@click.option('--parent-page-id', help='Parent page ID for wiki root')
@click.option('--structure', type=click.Choice(['flat', 'hierarchical', 'by-category']),
              default='flat', help='Page organization structure')
@click.option('--dry-run', is_flag=True, help='Preview without creating pages')
@click.pass_obj
def export_confluence(
    config: Config,
    channels: Optional[str],
    exclude: Optional[str],
    no_ai: bool,
    no_cache: bool,
    confluence_url: Optional[str],
    username: Optional[str],
    api_token: Optional[str],
    space_key: Optional[str],
    parent_page_id: Optional[str],
    structure: str,
    dry_run: bool
):
    """Export wiki directly to Confluence."""
    try:
        # Check Slack token
        if not config.slack.access_token:
            click.echo(click.style("✗ No Slack access token found. Run 'threadcrumb auth' first.", fg='red'), err=True)
            sys.exit(1)

        # Get Confluence credentials (command line overrides config/env)
        confluence_url = confluence_url or config.confluence.base_url
        username = username or config.confluence.username
        api_token = api_token or config.confluence.api_token
        space_key = space_key or config.confluence.space_key

        if not all([confluence_url, username, api_token, space_key]):
            click.echo(click.style(
                "✗ Missing Confluence credentials. Provide via options or config file.",
                fg='red'), err=True)
            click.echo("\nRequired:")
            click.echo("  --confluence-url or CONFLUENCE_URL")
            click.echo("  --username or CONFLUENCE_USERNAME")
            click.echo("  --api-token or CONFLUENCE_API_TOKEN")
            click.echo("  --space-key or CONFLUENCE_SPACE_KEY")
            sys.exit(1)

        # Initialize Slack client
        click.echo("Connecting to Slack...")
        slack_client = SlackClient(
            token=config.slack.access_token,
            rate_limit_delay=config.slack.rate_limit_delay,
            max_retries=config.slack.max_retries
        )

        workspace_info = slack_client.get_workspace_info()
        click.echo(f"Connected to workspace: {workspace_info['name']}")

        # Fetch and process channels (same as generate command)
        click.echo("Fetching channels...")
        all_channels = slack_client.list_channels()

        channel_names = [ch.strip() for ch in channels.split(',')] if channels else None
        exclude_names = [ch.strip() for ch in exclude.split(',')] if exclude else []

        if channel_names:
            selected_channels = [
                ch for ch in all_channels
                if ch['name'] in channel_names and ch['name'] not in exclude_names
            ]
        else:
            selected_channels = [
                ch for ch in all_channels
                if ch['name'] not in exclude_names
            ]

        if not selected_channels:
            click.echo(click.style("✗ No channels selected", fg='red'), err=True)
            sys.exit(1)

        click.echo(f"Processing {len(selected_channels)} channels...")

        # Initialize AI if enabled
        ai_processor = None
        if not no_ai:
            try:
                click.echo("Initializing AI processor...")
                bedrock_client = BedrockClient(
                    region=config.ai.region,
                    model_name=config.ai.model_name,
                    max_tokens=config.ai.max_tokens,
                    temperature=config.ai.temperature,
                    aws_profile=config.ai.aws_profile
                )

                if bedrock_client.test_connection():
                    ai_processor = AIProcessor(
                        bedrock_client=bedrock_client,
                        fallback_enabled=config.ai.fallback_enabled
                    )
                    click.echo(click.style("✓ AI processor initialized", fg='green'))
                else:
                    click.echo(click.style("! AI connection failed, continuing without AI", fg='yellow'))
            except Exception as e:
                click.echo(click.style(f"! AI initialization failed: {e}", fg='yellow'))

        # Process channels
        message_fetcher = MessageFetcher(
            client=slack_client,
            cache_enabled=not no_cache,
            cache_dir=Path(config.slack.cache_dir)
        )

        thread_reconstructor = ThreadReconstructor(
            max_depth=config.processing.max_thread_depth
        )

        pipeline = ContentPipeline(
            ai_processor=ai_processor,
            min_message_length=config.processing.min_message_length,
            min_thread_messages=2
        )

        processed_channels = []

        with ProgressTracker(len(selected_channels), "Processing channels") as progress:
            for channel in selected_channels:
                progress.set_description(f"Processing #{channel['name']}")

                try:
                    messages = message_fetcher.fetch_channel_messages(
                        channel['id'],
                        use_cache=not no_cache
                    )

                    threads = thread_reconstructor.reconstruct_threads(
                        messages,
                        fetch_replies=config.processing.thread_reconstruction,
                        message_fetcher=message_fetcher
                    )

                    processed_channel = pipeline.process_channel(
                        threads=threads,
                        channel_info=channel,
                        use_ai=not no_ai and ai_processor is not None
                    )

                    processed_channels.append(processed_channel)

                except Exception as e:
                    logger.error(f"Error processing channel {channel['name']}: {e}")
                    click.echo(click.style(f"! Error processing #{channel['name']}: {e}", fg='yellow'))

                progress.update(1)

        if not processed_channels:
            click.echo(click.style("✗ No channels processed successfully", fg='red'), err=True)
            sys.exit(1)

        # Export to Confluence
        click.echo(f"\n{'[DRY RUN] ' if dry_run else ''}Exporting to Confluence...")
        click.echo(f"Space: {space_key}")
        click.echo(f"Structure: {structure}")

        page_map = export_to_confluence(
            channels=processed_channels,
            confluence_url=confluence_url,
            username=username,
            api_token=api_token,
            space_key=space_key,
            root_page_title=config.confluence.root_page_title,
            parent_page_id=parent_page_id or config.confluence.parent_page_id,
            structure=structure,
            dry_run=dry_run,
            use_cloud=config.confluence.use_cloud
        )

        if dry_run:
            click.echo(click.style("\n✓ Dry run completed!", fg='green'))
            click.echo(f"Would create {len(page_map)} pages in Confluence")
        else:
            click.echo(click.style("\n✓ Successfully exported to Confluence!", fg='green'))
            click.echo(f"Created {len(page_map)} pages in space {space_key}")
            click.echo(f"\nView your wiki: {confluence_url}/wiki/spaces/{space_key}")

        # Print statistics
        total_threads = sum(len(ch.threads) for ch in processed_channels)
        click.echo("\nStatistics:")
        click.echo(f"  Channels: {len(processed_channels)}")
        click.echo(f"  Threads: {total_threads}")
        click.echo(f"  Pages Created: {len(page_map)}")

    except Exception as e:
        logger.exception("Error exporting to Confluence")
        click.echo(click.style(f"✗ Error: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.pass_obj
def config_init(config: Config):
    """Initialize configuration file."""
    config_path = get_default_config_path()

    if config_path.exists():
        click.confirm(f"Config file exists at {config_path}. Overwrite?", abort=True)

    config.to_file(str(config_path))

    click.echo(click.style(f"✓ Configuration file created: {config_path}", fg='green'))
    click.echo("\nEdit this file to customize your settings.")


@cli.command()
@click.pass_obj
def list_channels(config: Config):
    """List all channels in workspace."""
    try:
        if not config.slack.access_token:
            click.echo(click.style("✗ No Slack access token found. Run 'threadcrumb auth' first.", fg='red'), err=True)
            sys.exit(1)

        slack_client = SlackClient(token=config.slack.access_token)

        click.echo("Fetching channels...")
        channels = slack_client.list_channels()

        click.echo(f"\nFound {len(channels)} channels:\n")

        for channel in sorted(channels, key=lambda x: x['name']):
            status = "🔒" if channel.get('is_private') else "📢"
            members = channel.get('num_members', 0)
            click.echo(f"{status} #{channel['name']} ({members} members)")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.argument('query')
@click.option('--index-path', type=click.Path(exists=True), default='output/search_index.json', help='Path to search index')
@click.option('--limit', type=int, default=10, help='Maximum results to return')
@click.pass_obj
def search(config: Config, query: str, index_path: str, limit: int):
    """Search the generated wiki content."""
    try:
        index_file = Path(index_path)

        if not index_file.exists():
            click.echo(click.style(f"✗ Search index not found: {index_path}", fg='red'), err=True)
            click.echo("\nGenerate an index with: threadcrumb generate --build-index")
            sys.exit(1)

        # Load search index
        search_index = SearchIndex()
        search_index.load(index_file)

        # Perform search
        click.echo(f"Searching for: '{query}'\n")
        results = search_index.search(query, max_results=limit)

        if not results:
            click.echo("No results found.")
            return

        click.echo(f"Found {len(results)} results:\n")

        for i, result in enumerate(results, 1):
            click.echo(f"{i}. {result.thread_title}")
            click.echo(f"   Score: {result.score:.2f}")
            if result.excerpt:
                click.echo(f"   {result.excerpt}")
            if result.url:
                click.echo(f"   URL: {result.url}")
            click.echo()

    except Exception as e:
        logger.exception("Error searching")
        click.echo(click.style(f"✗ Error: {e}", fg='red'), err=True)
        sys.exit(1)


def main():
    """Main entry point."""
    cli(obj=None)


if __name__ == '__main__':
    main()

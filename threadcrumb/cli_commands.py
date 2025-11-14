"""
Enhanced CLI command implementations with full feature integration.
"""

import sys
import uuid
import click
import logging
from pathlib import Path
from typing import List, Dict, Optional

from .config import Config
from .slack import SlackClient, MessageFetcher, ThreadReconstructor
from .ai import AIProcessor
from .ai.providers import get_ai_provider
from .processing import ContentPipeline
from .output import MarkdownFormatter, HTMLFormatter, JSONFormatter, XMLFormatter
from .utils import ProgressTracker
from .utils.parallel import ChannelProcessor
from .search import SearchIndex
from .cache.sqlite_cache import SQLiteCache
from .resumption import CheckpointManager, ExportState
from .security import PIIDetector, ContentRedactor, AuditLogger, AuditEventType, DataEncryptor
from .interactive import InteractiveMode

logger = logging.getLogger(__name__)


def execute_generate_command(
    config: Config,
    channels: Optional[str],
    exclude: Optional[str],
    output: str,
    format: str,
    no_ai: bool,
    no_cache: bool,
    parallel: bool,
    max_workers: int,
    interactive: bool,
    build_index: bool,
    ai_provider: str,
    use_sqlite_cache: bool,
    resume: bool,
    redact_pii: bool,
    encrypt_cache: bool
):
    """Execute the generate command with all features integrated."""

    # Initialize audit logger
    audit_logger = AuditLogger(
        enable_console=True,
        min_level="info"
    )

    try:
        # Check for access token
        if not config.slack.access_token:
            click.echo(click.style("✗ No Slack access token found. Run 'threadcrumb auth' first.", fg='red'), err=True)
            sys.exit(1)

        # Initialize Slack client
        click.echo("Connecting to Slack...")
        slack_client = SlackClient(
            token=config.slack.access_token,
            rate_limit_delay=config.slack.rate_limit_delay,
            max_retries=config.slack.max_retries
        )

        workspace_info = slack_client.get_workspace_info()
        workspace_id = workspace_info.get('id')
        click.echo(f"Connected to workspace: {workspace_info['name']}")

        audit_logger.log_auth_success(
            user=workspace_info.get('name'),
            workspace_id=workspace_id
        )

        # List channels
        click.echo("Fetching channels...")
        all_channels = slack_client.list_channels()

        # Interactive mode for channel selection
        if interactive:
            try:
                interactive_mode = InteractiveMode()
                channel_names = [ch.strip() for ch in channels.split(',')] if channels else None
                selected_channels = interactive_mode.select_channels(
                    all_channels,
                    preselected=channel_names
                )

                # Let user select format in interactive mode
                if not format:
                    format = interactive_mode.select_format()

            except Exception as e:
                click.echo(click.style(f"! Interactive mode failed: {e}", fg='yellow'))
                click.echo("Falling back to standard mode...")
                interactive = False

        # Non-interactive channel filtering
        if not interactive:
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

        click.echo(f"Processing {len(selected_channels)} channels")

        # Check for resumable export
        checkpoint_manager = CheckpointManager()
        checkpoint = None
        export_id = str(uuid.uuid4())

        if resume:
            checkpoint = checkpoint_manager.find_resumable_export(
                output_format=format,
                output_path=output
            )

            if checkpoint:
                click.echo(f"Found resumable export from {checkpoint.updated_at}")
                click.echo(f"Progress: {checkpoint.get_progress_percentage():.1f}% complete")

                if click.confirm("Resume this export?"):
                    export_id = checkpoint.export_id
                    click.echo("Resuming export...")
                else:
                    checkpoint_manager.delete_checkpoint(checkpoint.export_id)
                    checkpoint = None

        # Create new checkpoint if not resuming
        if not checkpoint:
            checkpoint = checkpoint_manager.create_checkpoint(
                export_id=export_id,
                total_channels=len(selected_channels),
                output_format=format,
                output_path=output
            )
            checkpoint.state = ExportState.PROCESSING_CHANNELS

        # Initialize security features
        content_redactor = None
        if redact_pii:
            click.echo("Enabling PII detection and redaction...")
            pii_detector = PIIDetector()
            content_redactor = ContentRedactor(detector=pii_detector)
            audit_logger.log(
                event_type=AuditEventType.PII_DETECTED,
                message="PII detection enabled",
                workspace_id=workspace_id
            )

        # Initialize encryption
        encryptor = None
        if encrypt_cache:
            click.echo("Enabling cache encryption...")
            encryptor = DataEncryptor()
            audit_logger.log(
                event_type=AuditEventType.ENCRYPTION_ENABLED,
                message="Cache encryption enabled",
                workspace_id=workspace_id
            )

        # Initialize AI provider
        ai_processor = None
        if not no_ai:
            try:
                click.echo(f"Initializing {ai_provider} AI provider...")
                ai_client = get_ai_provider(ai_provider, config)

                if ai_client and ai_client.test_connection():
                    ai_processor = AIProcessor(
                        bedrock_client=ai_client if ai_provider == 'bedrock' else None,
                        fallback_enabled=config.ai.fallback_enabled
                    )
                    click.echo(click.style(f"✓ {ai_provider} AI provider initialized", fg='green'))
                    audit_logger.log(
                        event_type=AuditEventType.CONFIG_CHANGED,
                        message=f"Using {ai_provider} AI provider"
                    )
                else:
                    click.echo(click.style(f"! {ai_provider} connection failed, continuing without AI", fg='yellow'))

            except Exception as e:
                click.echo(click.style(f"! AI initialization failed: {e}", fg='yellow'))
                logger.exception("AI initialization error")
                audit_logger.log_error(f"AI initialization failed: {e}")

        # Initialize cache
        message_fetcher = None
        if use_sqlite_cache:
            click.echo("Using SQLite cache...")
            cache_path = Path.home() / ".threadcrumb" / "cache.db"
            cache = SQLiteCache(db_path=cache_path)

            message_fetcher = MessageFetcher(
                client=slack_client,
                cache_enabled=not no_cache,
                sqlite_cache=cache
            )
        else:
            message_fetcher = MessageFetcher(
                client=slack_client,
                cache_enabled=not no_cache,
                cache_dir=Path(config.slack.cache_dir)
            )

        # Initialize processing components
        thread_reconstructor = ThreadReconstructor(
            max_depth=config.processing.max_thread_depth
        )

        pipeline = ContentPipeline(
            ai_processor=ai_processor,
            min_message_length=config.processing.min_message_length,
            min_thread_messages=2
        )

        # Process channels (parallel or sequential)
        processed_channels = []

        if parallel:
            click.echo(f"Processing channels in parallel (workers: {max_workers})...")

            channel_processor = ChannelProcessor(
                message_fetcher=message_fetcher,
                thread_reconstructor=thread_reconstructor,
                pipeline=pipeline,
                use_ai=not no_ai and ai_processor is not None,
                max_workers=max_workers
            )

            # Filter out already processed channels if resuming
            channels_to_process = selected_channels
            if checkpoint:
                channels_to_process = [
                    ch for ch in selected_channels
                    if not checkpoint.is_channel_processed(ch['id'])
                ]

            results = channel_processor.process_channels(channels_to_process)

            for result in results:
                if result.success:
                    processed_channels.append(result.data)
                    if checkpoint:
                        checkpoint.mark_channel_completed(result.channel_id, thread_count=len(result.data.threads))
                        checkpoint_manager.save_checkpoint(checkpoint)
                else:
                    click.echo(click.style(f"! Error processing channel: {result.error}", fg='yellow'))
                    if checkpoint:
                        checkpoint.mark_channel_failed(result.channel_id, str(result.error))
                        checkpoint_manager.save_checkpoint(checkpoint)

        else:
            # Sequential processing
            with ProgressTracker(len(selected_channels), "Processing channels") as progress:
                for channel in selected_channels:
                    # Skip if already processed (resumption)
                    if checkpoint and checkpoint.is_channel_processed(channel['id']):
                        progress.update(1)
                        continue

                    progress.set_description(f"Processing #{channel['name']}")
                    checkpoint.mark_channel_started(channel['id'])

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

                        # Apply PII redaction if enabled
                        if content_redactor:
                            for thread in processed_channel.threads:
                                for msg in thread.messages:
                                    if 'text' in msg:
                                        msg['text'] = content_redactor.redact(msg['text'])

                        processed_channels.append(processed_channel)

                        checkpoint.mark_channel_completed(channel['id'], len(threads))
                        checkpoint_manager.save_checkpoint(checkpoint)

                    except Exception as e:
                        logger.error(f"Error processing channel {channel['name']}: {e}")
                        click.echo(click.style(f"! Error processing #{channel['name']}: {e}", fg='yellow'))
                        checkpoint.mark_channel_failed(channel['id'], str(e))
                        checkpoint_manager.save_checkpoint(checkpoint)

                    progress.update(1)

        if not processed_channels:
            click.echo(click.style("✗ No channels processed successfully", fg='red'), err=True)
            sys.exit(1)

        # Update checkpoint state
        checkpoint.state = ExportState.GENERATING_OUTPUT
        checkpoint_manager.save_checkpoint(checkpoint)

        # Generate output
        output_dir = Path(output)
        click.echo(f"\nGenerating {format} output...")

        if format == 'markdown':
            formatter = MarkdownFormatter(
                output_dir=output_dir,
                create_index=config.output.create_index,
                interlink_pages=config.output.interlink_pages,
                include_toc=config.output.include_toc
            )
            formatter.format_channels(processed_channels)

        elif format == 'html':
            formatter = HTMLFormatter(
                output_dir=output_dir,
                include_search=config.output.include_search
            )
            formatter.format_channels(processed_channels)

        elif format == 'json':
            formatter = JSONFormatter(
                output_path=output_dir / "slack_wiki.json",
                pretty=True
            )
            formatter.format_channels(processed_channels)

        elif format == 'xml':
            formatter = XMLFormatter(
                output_path=output_dir / "slack_wiki.xml",
                pretty=True
            )
            formatter.format_channels(processed_channels)

        # Build search index if requested
        if build_index:
            click.echo("\nBuilding search index...")
            search_index = SearchIndex()
            search_index.build_from_channels(processed_channels)

            index_path = output_dir / "search_index.json"
            search_index.save(index_path)

            click.echo(f"Search index saved to: {index_path}")

        # Mark export complete
        checkpoint.state = ExportState.COMPLETED
        checkpoint_manager.save_checkpoint(checkpoint)

        # Log export completion
        total_threads = sum(len(ch.threads) for ch in processed_channels)
        audit_logger.log_data_export(
            format=format,
            channel_count=len(processed_channels),
            thread_count=total_threads
        )

        click.echo(click.style(f"\n✓ Wiki generated successfully!", fg='green'))
        click.echo(f"Output location: {output_dir}")

        # Print statistics
        click.echo(f"\nStatistics:")
        click.echo(f"  Channels: {len(processed_channels)}")
        click.echo(f"  Threads: {total_threads}")

        if build_index:
            click.echo(f"  Search index: {index_path}")

        # Cleanup checkpoint after successful completion
        checkpoint_manager.delete_checkpoint(export_id)

    except Exception as e:
        logger.exception("Error generating wiki")
        click.echo(click.style(f"✗ Error: {e}", fg='red'), err=True)
        audit_logger.log_error(str(e))
        sys.exit(1)

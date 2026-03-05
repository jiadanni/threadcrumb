"""Helper functions for CLI commands."""

import logging
import click
from pathlib import Path
from typing import List, Optional, Dict

from .config import Config
from .slack import SlackClient, MessageFetcher
from .ai import AIProcessor
from .ai.providers import get_ai_provider
from .cache.sqlite_cache import SQLiteCache
from .security import PIIDetector, ContentRedactor, AuditLogger, AuditEventType
from .resumption import CheckpointManager, ExportCheckpoint

logger = logging.getLogger(__name__)


def initialize_security(
    audit_logger: AuditLogger,
    redact_pii: bool,
    workspace_id: str = None
) -> Optional[ContentRedactor]:
    """
    Initialize security features.

    Args:
        audit_logger: Audit logger instance
        redact_pii: Whether to enable PII redaction
        workspace_id: Slack workspace ID

    Returns:
        ContentRedactor if PII redaction enabled, None otherwise
    """
    if not redact_pii:
        return None

    click.echo("Enabling PII detection and redaction...")

    # Initialize PII detector and redactor
    pii_detector = PIIDetector()
    content_redactor = ContentRedactor(detector=pii_detector)

    audit_logger.log(
        event_type=AuditEventType.PII_DETECTED,
        message="PII detection enabled for export",
        workspace_id=workspace_id
    )

    return content_redactor


def initialize_ai_provider(
    config: Config,
    provider_name: str,
    no_ai: bool,
    audit_logger: AuditLogger
):
    """
    Initialize AI provider.

    Args:
        config: Configuration object
        provider_name: Name of AI provider (bedrock, openai, anthropic)
        no_ai: Whether AI is disabled
        audit_logger: Audit logger instance

    Returns:
        AI processor instance or None
    """
    if no_ai:
        return None

    try:
        click.echo(f"Initializing {provider_name} AI provider...")

        # Get provider-specific implementation
        ai_provider = get_ai_provider(provider_name, config)

        if not ai_provider:
            click.echo(click.style(f"! {provider_name} provider not available", fg='yellow'))
            return None

        # Test connection
        try:
            test_response = ai_provider.invoke(
                prompt="Test",
                system="You are a helpful assistant. Respond with 'OK'.",
                max_tokens=10
            )
            if test_response:
                click.echo(click.style(f"✓ {provider_name} AI provider initialized", fg='green'))
                audit_logger.log(
                    event_type=AuditEventType.CONFIG_CHANGED,
                    message=f"Using {provider_name} as AI provider"
                )
                return AIProcessor(
                    bedrock_client=ai_provider if provider_name == 'bedrock' else None,
                    fallback_enabled=config.ai.fallback_enabled
                )
        except Exception as e:
            click.echo(click.style(f"! {provider_name} connection test failed: {e}", fg='yellow'))
            return None

    except Exception as e:
        click.echo(click.style(f"! AI initialization failed: {e}", fg='yellow'))
        audit_logger.log_error(f"AI initialization failed: {e}")
        return None


def initialize_cache(
    config: Config,
    use_sqlite_cache: bool,
    no_cache: bool,
    encrypt_cache: bool,
    slack_client: SlackClient
) -> MessageFetcher:
    """
    Initialize message cache.

    Args:
        config: Configuration object
        use_sqlite_cache: Whether to use SQLite cache
        no_cache: Whether caching is disabled
        encrypt_cache: Whether to encrypt cache
        slack_client: Slack client instance

    Returns:
        MessageFetcher instance
    """
    if no_cache:
        return MessageFetcher(
            client=slack_client,
            cache_enabled=False
        )

    if use_sqlite_cache:
        click.echo("Using SQLite cache...")
        cache_path = Path.home() / ".threadcrumb" / "cache.db"
        cache = SQLiteCache(db_path=cache_path)

        return MessageFetcher(
            client=slack_client,
            cache_enabled=True,
            cache_dir=None,
            sqlite_cache=cache
        )
    else:
        return MessageFetcher(
            client=slack_client,
            cache_enabled=True,
            cache_dir=Path(config.slack.cache_dir)
        )


def filter_channels(
    all_channels: List[Dict],
    channel_names: Optional[List[str]],
    exclude_names: List[str],
    interactive: bool
) -> List[Dict]:
    """
    Filter channels based on criteria.

    Args:
        all_channels: List of all channels
        channel_names: Specific channels to include
        exclude_names: Channels to exclude
        interactive: Whether to use interactive selection

    Returns:
        Filtered list of channels
    """
    if interactive:
        try:
            from .interactive import InteractiveMode
            interactive_mode = InteractiveMode()
            preselected = channel_names if channel_names else None
            return interactive_mode.select_channels(all_channels, preselected=preselected)
        except ImportError:
            click.echo(click.style("! Interactive mode requires 'rich' package", fg='yellow'))
            click.echo("Install with: pip install threadcrumb[interactive]")
            # Fall through to non-interactive selection

    # Non-interactive filtering
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

    return selected_channels


def handle_resumption(
    resume: bool,
    output_format: str,
    output_path: str
) -> Optional['ExportCheckpoint']:
    """
    Handle export resumption.

    Args:
        resume: Whether to resume previous export
        output_format: Output format
        output_path: Output path

    Returns:
        Checkpoint if resuming, None otherwise
    """
    if not resume:
        return None

    checkpoint_manager = CheckpointManager()
    checkpoint = checkpoint_manager.find_resumable_export(
        output_format=output_format,
        output_path=output_path
    )

    if checkpoint:
        click.echo(f"Found resumable export from {checkpoint.updated_at}")
        progress = checkpoint.get_progress_percentage()
        done = len(checkpoint.processed_channels)
        total = checkpoint.total_channels
        click.echo(f"Progress: {progress:.1f}% ({done}/{total} channels)")

        if click.confirm("Resume this export?"):
            return checkpoint
        else:
            checkpoint_manager.delete_checkpoint(checkpoint.export_id)

    return None

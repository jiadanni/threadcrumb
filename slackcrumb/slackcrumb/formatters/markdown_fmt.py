"""Readable markdown output formatter."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..config import OutputConfig
from ..models import ExportResult, Message, Thread


def _format_message(msg: Message, indent: str = "") -> str:
    """Format a single message as markdown."""
    lines = []
    header = f"{indent}**{msg.user}**"
    if msg.datetime_str:
        header += f" — {msg.datetime_str}"
    if msg.is_bot:
        header += " (bot)"
    lines.append(header)
    lines.append("")

    # Message text, preserving paragraphs
    for para in msg.text.split("\n"):
        lines.append(f"{indent}{para}")
    lines.append("")

    # Reactions
    if msg.reactions:
        reaction_str = " ".join(f":{r.emoji}: ({r.count})" for r in msg.reactions)
        lines.append(f"{indent}Reactions: {reaction_str}")
        lines.append("")

    # Attachments
    for att in msg.attachments:
        lines.append(f"{indent}> [Attachment] {att[:100]}")
    if msg.attachments:
        lines.append("")

    return "\n".join(lines)


def _format_thread(thread: Thread) -> str:
    """Format a thread (parent + replies) as markdown."""
    lines = []
    lines.append(_format_message(thread.parent))

    if thread.replies:
        lines.append(f"  *{len(thread.replies)} replies:*")
        lines.append("")
        for reply in thread.replies:
            lines.append(_format_message(reply, indent="> "))
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def format_markdown(result: ExportResult) -> str:
    """Format an ExportResult as readable markdown."""
    lines = []
    lines.append(f"# Slack Export — {result.workspace}")
    lines.append(f"*Exported: {result.export_date}*")
    lines.append("")

    for channel in result.channels:
        lines.append(f"## #{channel.name}")
        lines.append(f"*{channel.total_messages} messages | Status: {channel.status}*")
        lines.append("")

        # Threads
        for thread in channel.threads:
            lines.append(_format_thread(thread))

        # Standalone messages
        if channel.standalone_messages:
            if channel.threads:
                lines.append("### Other Messages")
                lines.append("")
            for msg in channel.standalone_messages:
                lines.append(_format_message(msg))
                lines.append("---")
                lines.append("")

    return "\n".join(lines)


def write_markdown(result: ExportResult, config: OutputConfig) -> Path:
    """Write ExportResult to a Markdown file and return the path."""
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    channels_str = "_".join(c.name for c in result.channels[:3])
    if len(result.channels) > 3:
        channels_str += f"_+{len(result.channels) - 3}"

    filename = config.filename_template.format(
        channel=channels_str or "export",
        date=date_str,
    )
    if not filename.endswith(".md"):
        filename += ".md"

    path = output_dir / filename
    path.write_text(format_markdown(result), encoding="utf-8")
    return path

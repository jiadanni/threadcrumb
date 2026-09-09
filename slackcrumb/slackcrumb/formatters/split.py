"""Split an ExportResult into per-month ExportResults."""

from __future__ import annotations

from datetime import datetime

from ..models import ChannelExport, ExportResult
from ..utils.dates import message_datetime

UNKNOWN_MONTH = "unknown"


def _month_key(dt: datetime | None) -> str:
    return f"{dt.year:04d}-{dt.month:02d}" if dt else UNKNOWN_MONTH


def _channel_bucket(
    buckets: dict[str, ExportResult], result: ExportResult,
    month: str, channel: ChannelExport,
) -> ChannelExport:
    """Get or create the per-month ExportResult and its channel entry."""
    if month not in buckets:
        buckets[month] = ExportResult(
            workspace=result.workspace,
            export_date=result.export_date,
            format_version=result.format_version,
        )
    month_result = buckets[month]
    for ch in month_result.channels:
        if ch.name == channel.name:
            return ch
    ch = ChannelExport(
        name=channel.name,
        export_started=channel.export_started,
        export_finished=channel.export_finished,
        status=channel.status,
    )
    month_result.channels.append(ch)
    return ch


def split_by_month(result: ExportResult) -> dict[str, ExportResult]:
    """Group an export's content into one ExportResult per calendar month.

    Threads are bucketed by their parent message's date, so replies stay
    with their parent. Messages whose date can't be determined land under
    the "unknown" key.
    """
    buckets: dict[str, ExportResult] = {}

    for channel in result.channels:
        for thread in channel.threads:
            month = _month_key(message_datetime(thread.parent))
            _channel_bucket(buckets, result, month, channel).threads.append(thread)
        for msg in channel.standalone_messages:
            month = _month_key(message_datetime(msg))
            _channel_bucket(buckets, result, month, channel).standalone_messages.append(msg)

    for month_result in buckets.values():
        for ch in month_result.channels:
            ch.total_messages = len(ch.threads) + len(ch.standalone_messages)

    return buckets

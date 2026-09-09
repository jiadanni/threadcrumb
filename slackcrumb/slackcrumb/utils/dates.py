"""Date parsing helpers for scraped messages."""

from __future__ import annotations

from datetime import datetime

from dateutil import parser as dateparser

from ..models import Message


def message_datetime(msg: Message) -> datetime | None:
    """Best-effort datetime for a message.

    Prefers the permalink timestamp (epoch seconds or microseconds, e.g.
    "1718452800000000" from /archives/C123/p1718452800000000); falls back
    to parsing the human-readable aria-label (e.g. "Jan 15, 2025 10:30 AM").
    Returns None if neither source is usable.
    """
    ts = msg.timestamp or ""
    if ts.isdigit() and len(ts) in (10, 16):
        try:
            seconds = int(ts) / 1_000_000 if len(ts) == 16 else int(ts)
            return datetime.fromtimestamp(seconds)
        except (ValueError, OverflowError, OSError):
            pass

    if msg.datetime_str:
        try:
            # fuzzy=True skips tokens like "Today at"; missing fields
            # default to the current date.
            return dateparser.parse(msg.datetime_str, fuzzy=True)
        except (ValueError, TypeError, OverflowError):
            return None
    return None

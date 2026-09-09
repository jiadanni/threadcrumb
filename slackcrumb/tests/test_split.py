"""Tests for month splitting and message date parsing."""

from datetime import datetime

from slackcrumb.formatters.split import split_by_month
from slackcrumb.models import ChannelExport, ExportResult, Message, Thread
from slackcrumb.utils.dates import message_datetime


def _ts(year, month, day, hour=12):
    """Build a 16-digit Slack permalink timestamp (epoch microseconds)."""
    epoch = int(datetime(year, month, day, hour).timestamp())
    return f"{epoch}000000"


def _msg(user, text, year, month, day):
    return Message(user=user, text=text, timestamp=_ts(year, month, day))


def _sample_result():
    jan_thread = Thread(
        parent=_msg("alice", "January question", 2024, 1, 15),
        replies=[_msg("bob", "February answer", 2024, 2, 1)],
        reply_count=1,
    )
    channel = ChannelExport(
        name="studio",
        threads=[jan_thread],
        standalone_messages=[
            _msg("carol", "January note", 2024, 1, 20),
            _msg("dave", "June note", 2024, 6, 10),
            Message(user="eve", text="No date", timestamp="not-a-timestamp"),
        ],
        total_messages=4,
        status="completed",
    )
    return ExportResult(
        workspace="https://test-workspace.slack.com",
        channels=[channel],
        export_date="2024-07-01T10:00:00",
    )


def test_message_datetime_from_permalink_timestamp():
    msg = _msg("alice", "hi", 2024, 6, 15)
    dt = message_datetime(msg)
    assert dt is not None
    assert (dt.year, dt.month, dt.day) == (2024, 6, 15)


def test_message_datetime_fallback_to_label():
    msg = Message(user="alice", text="hi", timestamp="xyz",
                  datetime_str="Jan 15, 2025 10:30 AM")
    dt = message_datetime(msg)
    assert dt is not None
    assert (dt.year, dt.month, dt.day) == (2025, 1, 15)


def test_message_datetime_unparseable():
    msg = Message(user="alice", text="hi", timestamp="xyz", datetime_str="")
    assert message_datetime(msg) is None


def test_split_by_month_buckets():
    buckets = split_by_month(_sample_result())
    assert set(buckets) == {"2024-01", "2024-06", "unknown"}


def test_split_by_month_thread_stays_with_parent():
    buckets = split_by_month(_sample_result())
    jan = buckets["2024-01"].channels[0]
    assert len(jan.threads) == 1
    # The February reply stays under its January parent
    assert jan.threads[0].replies[0].text == "February answer"
    assert len(jan.standalone_messages) == 1
    assert jan.total_messages == 2


def test_split_by_month_preserves_metadata():
    buckets = split_by_month(_sample_result())
    june = buckets["2024-06"]
    assert june.workspace == "https://test-workspace.slack.com"
    assert june.export_date == "2024-07-01T10:00:00"
    assert june.channels[0].name == "studio"
    assert june.channels[0].status == "completed"


def test_split_by_month_unknown_bucket():
    buckets = split_by_month(_sample_result())
    unknown = buckets["unknown"].channels[0]
    assert unknown.standalone_messages[0].user == "eve"


def test_split_by_month_empty_result():
    result = ExportResult(workspace="test", export_date="2024-01-01")
    assert split_by_month(result) == {}

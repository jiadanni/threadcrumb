"""Tests for data models."""

from slackcrumb.models import Message, Reaction, Thread, ChannelExport, ExportResult


def test_message_to_dict(sample_message):
    d = sample_message.to_dict()
    assert d["user"] == "alice"
    assert d["text"] == "Hello world"
    assert d["timestamp"] == "1234567890123456"
    assert len(d["reactions"]) == 1
    assert d["reactions"][0]["emoji"] == "thumbsup"
    assert d["reactions"][0]["count"] == 3
    assert d["is_bot"] is False


def test_message_defaults():
    msg = Message(user="test", text="hi", timestamp="123")
    assert msg.reactions == []
    assert msg.attachments == []
    assert msg.is_bot is False
    assert msg.datetime_str == ""


def test_thread_to_dict(sample_thread):
    d = sample_thread.to_dict()
    assert d["parent"]["user"] == "alice"
    assert len(d["replies"]) == 2
    assert d["reply_count"] == 2
    assert d["replies"][0]["user"] == "bob"


def test_thread_reply_count_fallback():
    parent = Message(user="a", text="parent", timestamp="1")
    replies = [Message(user="b", text="reply", timestamp="2")]
    thread = Thread(parent=parent, replies=replies)
    d = thread.to_dict()
    assert d["reply_count"] == 1  # falls back to len(replies)


def test_channel_export_to_dict(sample_channel_export):
    d = sample_channel_export.to_dict()
    assert d["channel"] == "general"
    assert d["status"] == "completed"
    assert d["total_messages"] == 4
    assert len(d["threads"]) == 1
    assert len(d["standalone_messages"]) == 1


def test_export_result_to_dict(sample_export_result):
    d = sample_export_result.to_dict()
    assert d["workspace"] == "https://test-workspace.slack.com"
    assert d["format_version"] == "1.0"
    assert len(d["channels"]) == 1


def test_reaction_defaults():
    r = Reaction(emoji="fire")
    assert r.count == 1

"""Shared test fixtures."""

import pytest
from pathlib import Path
import tempfile

from slackcrumb.config import SlackcrumbConfig, BrowserConfig, ScrapeConfig, OutputConfig
from slackcrumb.models import Message, Reaction, Thread, ChannelExport, ExportResult


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def sample_config():
    return SlackcrumbConfig(
        workspace_url="https://test-workspace.slack.com",
        browser=BrowserConfig(headless=True),
        scrape=ScrapeConfig(channels=["general", "pendo"]),
        output=OutputConfig(format="json", output_dir="."),
    )


@pytest.fixture
def sample_message():
    return Message(
        user="alice",
        text="Hello world",
        timestamp="1234567890123456",
        datetime_str="Jan 15, 2025 10:30 AM",
        reactions=[Reaction(emoji="thumbsup", count=3)],
        is_bot=False,
    )


@pytest.fixture
def sample_thread(sample_message):
    replies = [
        Message(user="bob", text="Hey!", timestamp="1234567890123457", datetime_str="Jan 15, 2025 10:31 AM"),
        Message(user="charlie", text="Hi there", timestamp="1234567890123458", datetime_str="Jan 15, 2025 10:32 AM"),
    ]
    return Thread(parent=sample_message, replies=replies, reply_count=2)


@pytest.fixture
def sample_channel_export(sample_thread, sample_message):
    standalone = Message(user="dave", text="Standalone msg", timestamp="1234567890123460")
    return ChannelExport(
        name="general",
        threads=[sample_thread],
        standalone_messages=[standalone],
        total_messages=4,
        status="completed",
        export_started="2025-01-15T10:00:00",
        export_finished="2025-01-15T10:05:00",
    )


@pytest.fixture
def sample_export_result(sample_channel_export):
    return ExportResult(
        workspace="https://test-workspace.slack.com",
        channels=[sample_channel_export],
        export_date="2025-01-15T10:05:00",
    )

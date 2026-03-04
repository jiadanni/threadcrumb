"""Tests for checkpoint/resumption system."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from slackcrumb.checkpoint import Checkpoint, CheckpointData, ChannelProgress, CHECKPOINT_DIR
from slackcrumb.exceptions import CheckpointError


@pytest.fixture
def checkpoint_dir(tmp_path):
    """Override checkpoint dir to use temp directory."""
    with patch("slackcrumb.checkpoint.CHECKPOINT_DIR", tmp_path):
        yield tmp_path


def test_checkpoint_create(checkpoint_dir):
    cp = Checkpoint(export_id="test123", workspace_url="https://test.slack.com")
    assert cp.export_id == "test123"
    assert cp.data.workspace_url == "https://test.slack.com"


def test_checkpoint_save_and_load(checkpoint_dir):
    cp = Checkpoint(export_id="test456", workspace_url="https://test.slack.com")
    cp.update_channel("general", "1234567890", 50)
    cp.mark_thread_expanded("general", "1234567890")
    cp.save()

    loaded = Checkpoint.load("test456")
    assert loaded.export_id == "test456"
    assert loaded.data.workspace_url == "https://test.slack.com"
    assert loaded.get_last_timestamp("general") == "1234567890"
    assert loaded.is_thread_expanded("general", "1234567890")


def test_checkpoint_update_channel(checkpoint_dir):
    cp = Checkpoint(export_id="test789")
    cp.update_channel("pendo", "ts123", 10)
    assert cp.data.channels["pendo"].status == "in_progress"
    assert cp.data.channels["pendo"].last_message_ts == "ts123"
    assert cp.data.channels["pendo"].message_count == 10


def test_checkpoint_mark_channel_complete(checkpoint_dir):
    cp = Checkpoint(export_id="testabc")
    cp.update_channel("general", "ts1", 100)
    cp.mark_channel_complete("general")
    assert cp.is_channel_complete("general")
    assert not cp.is_channel_complete("random")


def test_checkpoint_thread_tracking(checkpoint_dir):
    cp = Checkpoint(export_id="testdef")
    assert not cp.is_thread_expanded("general", "ts1")
    cp.mark_thread_expanded("general", "ts1")
    assert cp.is_thread_expanded("general", "ts1")
    assert not cp.is_thread_expanded("general", "ts2")

    # Marking again should not duplicate
    cp.mark_thread_expanded("general", "ts1")
    assert len(cp.data.channels["general"].expanded_threads) == 1


def test_checkpoint_load_nonexistent(checkpoint_dir):
    with pytest.raises(CheckpointError):
        Checkpoint.load("nonexistent")


def test_checkpoint_find_resumable(checkpoint_dir):
    # Create two checkpoints
    cp1 = Checkpoint(export_id="cp1", workspace_url="https://a.slack.com")
    cp1.update_channel("general", "ts1", 10)
    cp1.mark_channel_complete("general")
    cp1.save()

    cp2 = Checkpoint(export_id="cp2", workspace_url="https://b.slack.com")
    cp2.update_channel("random", "ts2", 5)
    cp2.save()

    results = Checkpoint.find_resumable()
    assert len(results) == 2
    ids = {r["export_id"] for r in results}
    assert "cp1" in ids
    assert "cp2" in ids


def test_checkpoint_data_serialization():
    data = CheckpointData(
        export_id="ser1",
        workspace_url="https://test.slack.com",
        channels={
            "general": ChannelProgress(
                name="general", status="completed", last_message_ts="ts1",
                message_count=100, expanded_threads=["t1", "t2"]
            )
        },
    )
    d = data.to_dict()
    restored = CheckpointData.from_dict(d)
    assert restored.export_id == "ser1"
    assert restored.channels["general"].status == "completed"
    assert restored.channels["general"].expanded_threads == ["t1", "t2"]


def test_checkpoint_get_last_timestamp_missing_channel(checkpoint_dir):
    cp = Checkpoint(export_id="testmissing")
    assert cp.get_last_timestamp("nonexistent") == ""

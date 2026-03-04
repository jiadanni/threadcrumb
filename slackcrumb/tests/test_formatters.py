"""Tests for JSON and Markdown formatters."""

import json
import pytest
from pathlib import Path

from slackcrumb.formatters.json_fmt import format_json, write_json
from slackcrumb.formatters.markdown_fmt import format_markdown, write_markdown
from slackcrumb.config import OutputConfig


def test_format_json(sample_export_result):
    output = format_json(sample_export_result)
    data = json.loads(output)
    assert data["workspace"] == "https://test-workspace.slack.com"
    assert len(data["channels"]) == 1
    assert data["channels"][0]["channel"] == "general"
    assert data["channels"][0]["total_messages"] == 4


def test_write_json(sample_export_result, tmp_path):
    config = OutputConfig(output_dir=str(tmp_path))
    path = write_json(sample_export_result, config)
    assert path.exists()
    assert path.suffix == ".json"
    data = json.loads(path.read_text())
    assert data["workspace"] == "https://test-workspace.slack.com"


def test_format_markdown(sample_export_result):
    output = format_markdown(sample_export_result)
    assert "# Slack Export" in output
    assert "## #general" in output
    assert "**alice**" in output
    assert "Hello world" in output
    assert "2 replies" in output
    assert "bob" in output


def test_write_markdown(sample_export_result, tmp_path):
    config = OutputConfig(output_dir=str(tmp_path), format="markdown")
    path = write_markdown(sample_export_result, config)
    assert path.exists()
    assert path.suffix == ".md"
    content = path.read_text()
    assert "# Slack Export" in content


def test_format_json_empty():
    from slackcrumb.models import ExportResult
    result = ExportResult(workspace="test", export_date="2025-01-01")
    output = format_json(result)
    data = json.loads(output)
    assert data["channels"] == []


def test_format_markdown_with_reactions(sample_export_result):
    output = format_markdown(sample_export_result)
    assert "thumbsup" in output
    assert "(3)" in output


def test_format_markdown_standalone_messages(sample_export_result):
    output = format_markdown(sample_export_result)
    assert "Standalone msg" in output


def test_write_json_creates_dir(sample_export_result, tmp_path):
    nested = tmp_path / "sub" / "dir"
    config = OutputConfig(output_dir=str(nested))
    path = write_json(sample_export_result, config)
    assert path.exists()
    assert nested.exists()

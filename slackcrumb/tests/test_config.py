"""Tests for config loading and serialization."""

import pytest
from pathlib import Path

from slackcrumb.config import SlackcrumbConfig, BrowserConfig, ScrapeConfig, OutputConfig
from slackcrumb.exceptions import ConfigError


def test_default_config():
    config = SlackcrumbConfig()
    assert config.workspace_url == ""
    assert config.browser.headless is False
    assert config.scrape.scroll_pause == 1.5
    assert config.output.format == "json"


def test_config_to_yaml():
    config = SlackcrumbConfig(workspace_url="https://test.slack.com")
    yaml_str = config.to_yaml()
    assert "workspace_url: https://test.slack.com" in yaml_str
    assert "browser:" in yaml_str


def test_config_to_dict():
    config = SlackcrumbConfig(workspace_url="https://test.slack.com")
    d = config.to_dict()
    assert d["workspace_url"] == "https://test.slack.com"
    assert "browser" in d
    assert "scrape" in d
    assert "output" in d


def test_config_from_dict():
    data = {
        "workspace_url": "https://myteam.slack.com",
        "browser": {"headless": True, "viewport_width": 1920},
        "scrape": {"channels": ["general"], "scroll_pause": 2.0},
        "output": {"format": "markdown"},
    }
    config = SlackcrumbConfig._from_dict(data)
    assert config.workspace_url == "https://myteam.slack.com"
    assert config.browser.headless is True
    assert config.browser.viewport_width == 1920
    assert config.scrape.channels == ["general"]
    assert config.scrape.scroll_pause == 2.0
    assert config.output.format == "markdown"


def test_config_from_dict_ignores_unknown_keys():
    data = {
        "browser": {"headless": True, "unknown_key": "value"},
        "scrape": {},
    }
    config = SlackcrumbConfig._from_dict(data)
    assert config.browser.headless is True


def test_config_load_nonexistent(tmp_path):
    config = SlackcrumbConfig.load(tmp_path / "nonexistent.yaml")
    assert config.workspace_url == ""  # returns defaults


def test_config_load_valid_yaml(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("workspace_url: https://test.slack.com\nbrowser:\n  headless: true\n")
    config = SlackcrumbConfig.load(path)
    assert config.workspace_url == "https://test.slack.com"
    assert config.browser.headless is True


def test_config_load_invalid_yaml(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("{{invalid yaml")
    with pytest.raises(ConfigError):
        SlackcrumbConfig.load(path)


def test_config_load_empty_yaml(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("")
    config = SlackcrumbConfig.load(path)
    assert config.workspace_url == ""


def test_scrape_config_defaults():
    sc = ScrapeConfig()
    assert sc.expand_threads is True
    assert sc.scroll_max_retries == 5
    assert sc.batch_size == 50
    assert sc.retry_count == 3

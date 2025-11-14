"""
Tests for configuration management.
"""

import pytest
import os
from pathlib import Path

from threadcrumb.config import (
    Config, SlackConfig, AIConfig, ConfluenceConfig,
    load_config, get_default_config_path
)


@pytest.mark.unit
class TestSlackConfig:
    """Test SlackConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SlackConfig()

        assert config.access_token is None
        assert config.rate_limit_delay == 1.0
        assert config.max_retries == 3
        assert config.cache_enabled == True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SlackConfig(
            access_token="xoxb-test",
            rate_limit_delay=2.0,
            max_retries=5
        )

        assert config.access_token == "xoxb-test"
        assert config.rate_limit_delay == 2.0
        assert config.max_retries == 5


@pytest.mark.unit
class TestAIConfig:
    """Test AIConfig class."""

    def test_default_values(self):
        """Test default AI configuration."""
        config = AIConfig()

        assert config.provider == "bedrock"
        assert config.region == "us-east-1"
        assert config.temperature == 0.7
        assert config.fallback_enabled == True


@pytest.mark.unit
class TestConfluenceConfig:
    """Test ConfluenceConfig class."""

    def test_default_values(self):
        """Test default Confluence configuration."""
        config = ConfluenceConfig()

        assert config.base_url is None
        assert config.use_cloud == True
        assert config.root_page_title == "Slack Wiki"
        assert config.structure == "flat"
        assert config.add_labels == True


@pytest.mark.unit
class TestConfig:
    """Test main Config class."""

    def test_default_config(self):
        """Test creating default configuration."""
        config = Config()

        assert isinstance(config.slack, SlackConfig)
        assert isinstance(config.ai, AIConfig)
        assert isinstance(config.confluence, ConfluenceConfig)

    def test_from_file_nonexistent(self, temp_dir):
        """Test loading from non-existent file."""
        config_path = temp_dir / "nonexistent.yaml"
        config = Config.from_file(str(config_path))

        assert isinstance(config, Config)

    def test_from_file_valid(self, temp_dir):
        """Test loading from valid YAML file."""
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
slack:
  access_token: xoxb-test-token
  rate_limit_delay: 2.0

ai:
  region: us-west-2
  temperature: 0.5

confluence:
  base_url: https://test.atlassian.net
  space_key: TEST
""")

        config = Config.from_file(str(config_path))

        assert config.slack.access_token == "xoxb-test-token"
        assert config.slack.rate_limit_delay == 2.0
        assert config.ai.region == "us-west-2"
        assert config.ai.temperature == 0.5
        assert config.confluence.base_url == "https://test.atlassian.net"

    def test_to_file(self, temp_dir):
        """Test saving configuration to file."""
        config = Config()
        config.slack.access_token = "xoxb-test"
        config.ai.region = "us-west-2"

        config_path = temp_dir / "config.yaml"
        config.to_file(str(config_path))

        assert config_path.exists()

        # Reload and verify
        loaded_config = Config.from_file(str(config_path))
        assert loaded_config.slack.access_token == "xoxb-test"
        assert loaded_config.ai.region == "us-west-2"

    def test_from_env(self, monkeypatch):
        """Test loading from environment variables."""
        monkeypatch.setenv("SLACK_ACCESS_TOKEN", "xoxb-env-token")
        monkeypatch.setenv("AWS_REGION", "eu-west-1")
        monkeypatch.setenv("CONFLUENCE_URL", "https://env.atlassian.net")
        monkeypatch.setenv("CONFLUENCE_SPACE_KEY", "ENV")

        config = Config.from_env()

        assert config.slack.access_token == "xoxb-env-token"
        assert config.ai.region == "eu-west-1"
        assert config.confluence.base_url == "https://env.atlassian.net"
        assert config.confluence.space_key == "ENV"

    def test_get_default_config_path(self):
        """Test getting default config path."""
        path = get_default_config_path()

        assert isinstance(path, Path)
        assert path.name == "config.yaml"
        assert ".threadcrumb" in str(path)

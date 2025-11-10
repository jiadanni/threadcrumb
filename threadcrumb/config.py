"""
Configuration management for ThreadCrumb.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict


@dataclass
class SlackConfig:
    """Slack integration configuration."""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    access_token: Optional[str] = None
    workspace_id: Optional[str] = None
    channels: List[str] = field(default_factory=list)
    exclude_channels: List[str] = field(default_factory=list)
    rate_limit_delay: float = 1.0
    max_retries: int = 3
    cache_enabled: bool = True
    cache_dir: str = ".threadcrumb/cache"


@dataclass
class AIConfig:
    """AI service configuration."""
    provider: str = "bedrock"  # bedrock, openai, anthropic
    model_name: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    region: str = "us-east-1"
    max_tokens: int = 4096
    temperature: float = 0.7
    fallback_enabled: bool = True
    aws_profile: Optional[str] = None


@dataclass
class ProcessingConfig:
    """Content processing configuration."""
    thread_reconstruction: bool = True
    include_attachments: bool = True
    min_message_length: int = 10
    max_thread_depth: int = 50
    categorization_enabled: bool = True
    topic_extraction_enabled: bool = True
    summary_enabled: bool = True
    qa_generation_enabled: bool = True
    sentiment_analysis: bool = False
    importance_scoring: bool = True


@dataclass
class OutputConfig:
    """Output format configuration."""
    format: str = "markdown"  # markdown, html, json, xml, confluence
    output_dir: str = "output"
    create_index: bool = True
    interlink_pages: bool = True
    include_search: bool = True
    include_toc: bool = True
    date_format: str = "%Y-%m-%d %H:%M:%S"


@dataclass
class Config:
    """Main application configuration."""
    slack: SlackConfig = field(default_factory=SlackConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            return cls()

        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}

        return cls(
            slack=SlackConfig(**data.get('slack', {})),
            ai=AIConfig(**data.get('ai', {})),
            processing=ProcessingConfig(**data.get('processing', {})),
            output=OutputConfig(**data.get('output', {}))
        )

    def to_file(self, config_path: str) -> None:
        """Save configuration to YAML file."""
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'slack': asdict(self.slack),
            'ai': asdict(self.ai),
            'processing': asdict(self.processing),
            'output': asdict(self.output)
        }

        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config = cls()

        # Slack config from env
        if os.getenv('SLACK_CLIENT_ID'):
            config.slack.client_id = os.getenv('SLACK_CLIENT_ID')
        if os.getenv('SLACK_CLIENT_SECRET'):
            config.slack.client_secret = os.getenv('SLACK_CLIENT_SECRET')
        if os.getenv('SLACK_ACCESS_TOKEN'):
            config.slack.access_token = os.getenv('SLACK_ACCESS_TOKEN')

        # AI config from env
        if os.getenv('AWS_REGION'):
            config.ai.region = os.getenv('AWS_REGION')
        if os.getenv('AWS_PROFILE'):
            config.ai.aws_profile = os.getenv('AWS_PROFILE')
        if os.getenv('AI_MODEL'):
            config.ai.model_name = os.getenv('AI_MODEL')

        return config


def get_default_config_path() -> Path:
    """Get the default configuration file path."""
    return Path.home() / ".threadcrumb" / "config.yaml"


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file and environment."""
    if config_path is None:
        config_path = get_default_config_path()

    # Start with file config
    if Path(config_path).exists():
        config = Config.from_file(str(config_path))
    else:
        config = Config()

    # Override with environment variables
    env_config = Config.from_env()
    if env_config.slack.access_token:
        config.slack.access_token = env_config.slack.access_token
    if env_config.slack.client_id:
        config.slack.client_id = env_config.slack.client_id
    if env_config.slack.client_secret:
        config.slack.client_secret = env_config.slack.client_secret
    if env_config.ai.aws_profile:
        config.ai.aws_profile = env_config.ai.aws_profile

    return config

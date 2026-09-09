"""Configuration dataclasses and YAML loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .exceptions import ConfigError

DEFAULT_CONFIG_DIR = Path.home() / ".slackcrumb"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"


@dataclass
class BrowserConfig:
    headless: bool = False
    user_data_dir: str = str(DEFAULT_CONFIG_DIR / "browser_data")
    viewport_width: int = 1280
    viewport_height: int = 900
    slow_mo: int = 0
    timeout: int = 30_000  # ms


@dataclass
class ScrapeConfig:
    channels: list[str] = field(default_factory=list)
    search_query: str | None = None
    oldest_date: str | None = None
    newest_date: str | None = None
    exclude_bots: bool = False
    expand_threads: bool = True
    scroll_pause: float = 1.5  # seconds between scrolls
    scroll_max_retries: int = 5  # consecutive empty scrolls before stopping
    batch_size: int = 50  # messages per checkpoint save
    max_threads_per_channel: int | None = None
    navigation_timeout: int = 60_000  # ms
    retry_count: int = 3
    retry_backoff: float = 2.0  # seconds, multiplied each retry


@dataclass
class OutputConfig:
    format: str = "json"  # json or markdown
    output_dir: str = "."
    filename_template: str = "{channel}_{date}"
    split_by: str | None = None  # None (single file) or "month"


@dataclass
class SlackcrumbConfig:
    workspace_url: str = ""
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    scrape: ScrapeConfig = field(default_factory=ScrapeConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def load(cls, path: Path | None = None) -> SlackcrumbConfig:
        """Load config from YAML file, falling back to defaults."""
        path = path or DEFAULT_CONFIG_PATH
        if not path.exists():
            return cls()

        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(
                f"Invalid YAML in {path}: {e}",
                suggestion="Run 'slackcrumb config-init' to create a valid config file.",
            )

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> SlackcrumbConfig:
        browser_data = data.get("browser", {})
        scrape_data = data.get("scrape", {})
        output_data = data.get("output", {})

        return cls(
            workspace_url=data.get("workspace_url", ""),
            browser=BrowserConfig(**{
                k: v for k, v in browser_data.items()
                if k in BrowserConfig.__dataclass_fields__
            }),
            scrape=ScrapeConfig(**{
                k: v for k, v in scrape_data.items()
                if k in ScrapeConfig.__dataclass_fields__
            }),
            output=OutputConfig(**{
                k: v for k, v in output_data.items()
                if k in OutputConfig.__dataclass_fields__
            }),
        )

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)


def ensure_dirs() -> None:
    """Create required directories."""
    for d in [
        DEFAULT_CONFIG_DIR,
        DEFAULT_CONFIG_DIR / "browser_data",
        DEFAULT_CONFIG_DIR / "checkpoints",
        DEFAULT_CONFIG_DIR / "cache",
        DEFAULT_CONFIG_DIR / "logs",
    ]:
        d.mkdir(parents=True, exist_ok=True)

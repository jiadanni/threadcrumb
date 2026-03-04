"""Slackcrumb exception hierarchy."""

from __future__ import annotations


class SlackcrumbError(Exception):
    """Base exception for all Slackcrumb errors."""

    def __init__(self, message: str, suggestion: str | None = None):
        self.suggestion = suggestion
        full = message
        if suggestion:
            full = f"{message}\n  Suggestion: {suggestion}"
        super().__init__(full)


class BrowserError(SlackcrumbError):
    """Error launching or interacting with the browser."""


class AuthError(SlackcrumbError):
    """Authentication-related error."""


class NavigationError(SlackcrumbError):
    """Error navigating to a page or waiting for content."""


class ScrapeError(SlackcrumbError):
    """Error during the scraping process."""


class ParseError(SlackcrumbError):
    """Error parsing DOM elements into data models."""


class ConfigError(SlackcrumbError):
    """Error in configuration."""


class CheckpointError(SlackcrumbError):
    """Error saving or loading checkpoints."""

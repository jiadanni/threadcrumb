"""Playwright persistent browser context management."""

from __future__ import annotations

import logging
from pathlib import Path

from playwright.async_api import BrowserContext, Playwright, async_playwright

from ..config import BrowserConfig, ensure_dirs
from ..exceptions import BrowserError

logger = logging.getLogger("slackcrumb")


class BrowserSession:
    """Manages a persistent Playwright Chromium browser context."""

    def __init__(self, config: BrowserConfig):
        self.config = config
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise BrowserError(
                "Browser not started.",
                suggestion="Call 'await session.start()' before using the browser.",
            )
        return self._context

    async def start(self) -> BrowserContext:
        """Launch browser with persistent context (cookies/localStorage survive)."""
        ensure_dirs()
        user_data_dir = Path(self.config.user_data_dir)
        user_data_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._playwright = await async_playwright().start()
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=self.config.headless,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
                slow_mo=self.config.slow_mo,
                args=[
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            self._context.set_default_timeout(self.config.timeout)
            logger.info("Browser started (headless=%s)", self.config.headless)
            return self._context
        except Exception as e:
            raise BrowserError(
                f"Failed to launch browser: {e}",
                suggestion="Run 'playwright install chromium' to install the browser.",
            ) from e

    async def new_page(self):
        """Get a new page, or reuse the first if one already exists."""
        pages = self.context.pages
        if pages:
            return pages[0]
        return await self.context.new_page()

    async def close(self) -> None:
        """Close browser context and Playwright."""
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        logger.info("Browser closed")

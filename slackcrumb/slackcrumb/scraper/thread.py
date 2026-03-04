"""Thread panel expansion and reply scraping."""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import ElementHandle, Page

from ..browser import selectors
from ..config import ScrapeConfig
from ..models import Message
from .parser import parse_message_element

logger = logging.getLogger("slackcrumb")


async def expand_thread(
    page: Page, message_element: ElementHandle, config: ScrapeConfig
) -> list[Message]:
    """Click a message's reply bar to open the thread panel and parse replies.

    Returns list of reply Messages (excluding the parent).
    """
    replies: list[Message] = []

    try:
        # Click the reply bar to open thread panel
        reply_bar = await message_element.query_selector(selectors.REPLY_BAR)
        if not reply_bar:
            reply_bar = await message_element.query_selector(selectors.REPLY_COUNT_BUTTON)
        if not reply_bar:
            reply_bar = await message_element.query_selector(selectors.REPLY_BAR_FALLBACK)
        if not reply_bar:
            return replies

        await reply_bar.click()

        # Wait for thread panel to appear
        try:
            await page.wait_for_selector(
                selectors.THREAD_PANEL, timeout=config.navigation_timeout
            )
        except Exception:
            logger.warning("Thread panel did not appear, skipping.")
            return replies

        # Give panel time to fully load
        await asyncio.sleep(config.scroll_pause)

        # Parse thread messages (skip first one as it's the parent)
        thread_elements = await page.query_selector_all(selectors.THREAD_PANEL_MESSAGES)

        for i, el in enumerate(thread_elements):
            if i == 0:
                continue  # skip parent message
            msg = await parse_message_element(el)
            if msg:
                replies.append(msg)

        # Close thread panel
        await _close_thread_panel(page)

    except Exception as e:
        logger.warning("Error expanding thread: %s", e)
        # Try to close panel if it's open
        await _close_thread_panel(page)

    return replies


async def _close_thread_panel(page: Page) -> None:
    """Close the thread panel if it's open."""
    try:
        close_btn = await page.query_selector(selectors.THREAD_PANEL_CLOSE)
        if close_btn:
            await close_btn.click()
            await asyncio.sleep(0.5)
    except Exception:
        # Panel might already be closed
        pass

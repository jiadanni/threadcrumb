"""Keyword search via Slack's search bar."""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Page

from ..browser import selectors
from ..config import ScrapeConfig
from ..exceptions import ScrapeError
from ..models import Message
from .parser import parse_message_element

logger = logging.getLogger("slackcrumb")


async def search_messages(
    page: Page, query: str, config: ScrapeConfig
) -> list[Message]:
    """Use Slack's search bar to find messages matching a query.

    Returns list of Messages from search results.
    """
    logger.info("Searching for: %s", query)

    # Click search button (top nav search)
    search_btn = await page.query_selector(selectors.SEARCH_BUTTON)
    if not search_btn:
        search_btn = await page.query_selector(selectors.SEARCH_INPUT)
    if not search_btn:
        raise ScrapeError(
            "Could not find search bar.",
            suggestion="Make sure you're on a Slack workspace page.",
        )
    await search_btn.click()

    # Wait for search input field to appear and type query
    await asyncio.sleep(0.5)
    input_field = await page.wait_for_selector(
        selectors.SEARCH_INPUT_FIELD, timeout=config.navigation_timeout
    )
    if not input_field:
        # Fallback: type into whatever is focused
        await page.keyboard.type(query)
    else:
        await input_field.fill(query)
    await page.keyboard.press("Enter")

    # Wait for results
    await asyncio.sleep(config.scroll_pause * 2)

    # Click Messages tab if available
    messages_tab = await page.query_selector(selectors.SEARCH_TAB_MESSAGES)
    if messages_tab:
        await messages_tab.click()
        await asyncio.sleep(config.scroll_pause)

    # Parse results
    messages: list[Message] = []
    seen_timestamps: set[str] = set()

    # Scroll through results
    empty_scrolls = 0
    while empty_scrolls < config.scroll_max_retries:
        results = await page.query_selector_all(selectors.SEARCH_RESULT_ITEM)
        new_count = 0

        for result in results:
            msg = await parse_message_element(result)
            if msg and msg.timestamp not in seen_timestamps:
                seen_timestamps.add(msg.timestamp)
                messages.append(msg)
                new_count += 1

        if new_count == 0:
            empty_scrolls += 1
        else:
            empty_scrolls = 0

        # Scroll results list
        results_list = await page.query_selector(selectors.SEARCH_RESULTS_LIST)
        if results_list:
            await results_list.evaluate(
                "el => el.scrollTop = el.scrollHeight"
            )
            await asyncio.sleep(config.scroll_pause)
        else:
            break

    logger.info("Found %d messages for query '%s'.", len(messages), query)
    return messages

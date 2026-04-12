"""Channel navigation and scroll-based message scraping."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from dateutil import parser as dateparser
from playwright.async_api import Page

from ..browser import selectors
from ..browser.auth import detect_session_expiry, handle_reauth
from ..checkpoint import Checkpoint
from ..config import ScrapeConfig
from ..exceptions import NavigationError
from ..models import ChannelExport, Message, Thread
from ..utils.progress import progress_bar
from .parser import get_reply_count, parse_message_element
from .thread import expand_thread

logger = logging.getLogger("slackcrumb")


async def navigate_to_channel(
    page: Page, workspace_url: str, channel_name: str, timeout: int = 60_000
) -> None:
    """Navigate to a channel by constructing its archive URL."""
    url = f"{workspace_url.rstrip('/')}/archives/{channel_name}"
    logger.info("Navigating to channel: %s", channel_name)

    for attempt in range(3):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            # Wait for message pane to appear
            await page.wait_for_selector(
                selectors.MESSAGE_PANE, timeout=timeout, state="attached"
            )
            return
        except Exception as e:
            if attempt == 2:
                raise NavigationError(
                    f"Failed to navigate to #{channel_name}: {e}",
                    suggestion="Check that the channel name is correct and you have access.",
                )
            logger.warning("Navigation attempt %d failed, retrying...", attempt + 1)
            await asyncio.sleep(2 * (attempt + 1))


async def scrape_channel(
    page: Page,
    workspace_url: str,
    channel_name: str,
    config: ScrapeConfig,
    checkpoint: Checkpoint,
) -> ChannelExport:
    """Scrape all messages from a channel using the scroll loop.

    1. Navigate to channel
    2. Scroll up to load history
    3. Parse messages, deduplicate
    4. Optionally expand threads
    5. Save checkpoints throughout
    """
    export = ChannelExport(
        name=channel_name,
        export_started=datetime.now().isoformat(),
        status="in_progress",
    )

    # Check if channel already completed in checkpoint
    if checkpoint.is_channel_complete(channel_name):
        logger.info("Channel #%s already completed, skipping.", channel_name)
        export.status = "completed"
        return export

    await navigate_to_channel(page, workspace_url, channel_name, config.navigation_timeout)

    # Parse oldest_date if provided
    oldest_dt = None
    if config.oldest_date:
        oldest_dt = dateparser.parse(config.oldest_date)

    # Resume from checkpoint if available
    last_ts = checkpoint.get_last_timestamp(channel_name)
    if last_ts:
        logger.info("Resuming channel #%s from timestamp %s", channel_name, last_ts)

    # Scroll loop: collect all messages
    all_messages: dict[str, Message] = {}  # keyed by timestamp for dedup
    empty_scroll_count = 0

    logger.info("Starting scroll loop for #%s...", channel_name)

    while True:
        # Check for session expiry
        if await detect_session_expiry(page, workspace_url):
            await handle_reauth(page, workspace_url)
            await navigate_to_channel(page, workspace_url, channel_name, config.navigation_timeout)

        # Scroll to top of message pane
        scroll_container = await page.query_selector(selectors.SCROLL_CONTAINER)
        if scroll_container:
            await scroll_container.evaluate("el => el.scrollTop = 0")

        await asyncio.sleep(config.scroll_pause)

        # Parse visible messages
        elements = await page.query_selector_all(selectors.MESSAGE_ITEM)
        new_count = 0

        for el in elements:
            msg = await parse_message_element(el)
            if msg and msg.timestamp and msg.timestamp not in all_messages:
                # Check oldest_date cutoff
                if oldest_dt and msg.datetime_str:
                    try:
                        msg_dt = dateparser.parse(msg.datetime_str)
                        if msg_dt and msg_dt < oldest_dt:
                            logger.info("Reached oldest_date cutoff.")
                            empty_scroll_count = config.scroll_max_retries  # force stop
                            break
                    except (ValueError, TypeError):
                        pass

                # Skip if resuming and message is before checkpoint
                if last_ts and msg.timestamp <= last_ts:
                    continue

                all_messages[msg.timestamp] = msg
                new_count += 1

        if new_count == 0:
            empty_scroll_count += 1
            if empty_scroll_count >= config.scroll_max_retries:
                logger.info(
                    "Stopping scroll: %d consecutive empty scrolls.", empty_scroll_count
                )
                break
        else:
            empty_scroll_count = 0

        # Check for beginning-of-channel marker
        beginning = await page.query_selector(selectors.CHANNEL_BEGINNING_MARKER)
        if beginning:
            logger.info("Reached beginning of #%s.", channel_name)
            break

        # Save checkpoint periodically
        if len(all_messages) % config.batch_size < new_count:
            latest_ts = max(all_messages.keys()) if all_messages else ""
            checkpoint.update_channel(channel_name, latest_ts, len(all_messages))
            checkpoint.save()

    messages = sorted(all_messages.values(), key=lambda m: m.timestamp)
    logger.info("Collected %d messages from #%s.", len(messages), channel_name)

    # Thread expansion
    threads: list[Thread] = []
    standalone: list[Message] = []

    if config.expand_threads:
        # Re-query elements to expand threads
        elements = await page.query_selector_all(selectors.MESSAGE_ITEM)
        pbar = progress_bar(total=len(elements), desc=f"#{channel_name} threads", unit="thread")

        for el in elements:
            reply_count = await get_reply_count(el)
            msg = await parse_message_element(el)

            if msg and reply_count > 0:
                ts = msg.timestamp
                if checkpoint.is_thread_expanded(channel_name, ts):
                    pbar.update(1)
                    continue

                replies = await expand_thread(page, el, config)
                thread = Thread(parent=msg, replies=replies, reply_count=reply_count)
                threads.append(thread)

                checkpoint.mark_thread_expanded(channel_name, ts)
                checkpoint.save()
            elif msg:
                standalone.append(msg)

            pbar.update(1)

        pbar.close()
    else:
        standalone = messages

    export.threads = threads
    export.standalone_messages = standalone
    export.total_messages = len(messages)
    export.export_finished = datetime.now().isoformat()
    export.status = "completed"

    checkpoint.mark_channel_complete(channel_name)
    checkpoint.save()

    return export

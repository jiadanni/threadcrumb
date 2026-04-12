"""DOM element → data model conversion."""

from __future__ import annotations

import logging
import re

from playwright.async_api import ElementHandle, Page

from ..browser import selectors
from ..models import Message, Reaction

logger = logging.getLogger("slackcrumb")


async def parse_message_element(element: ElementHandle) -> Message | None:
    """Parse a single message DOM element into a Message model.

    Returns None if the element doesn't contain a parseable message.
    """
    try:
        # Extract sender
        sender_el = await element.query_selector(selectors.MESSAGE_SENDER)
        user = await sender_el.inner_text() if sender_el else "Unknown"

        # Extract text
        text_el = await element.query_selector(selectors.MESSAGE_TEXT)
        if not text_el:
            text_el = await element.query_selector(selectors.MESSAGE_BODY)
        text = await text_el.inner_text() if text_el else ""

        if not text.strip() and user == "Unknown":
            return None

        # Extract timestamp — Slack uses a.c-timestamp with aria-label
        # e.g. aria-label="Today at 14:02:38", href="/archives/C.../p1234567890123456"
        ts_el = await element.query_selector(selectors.MESSAGE_TIMESTAMP)
        timestamp = ""
        datetime_str = ""
        if ts_el:
            datetime_str = await ts_el.get_attribute("aria-label") or ""
            # Extract unique timestamp from href like /archives/C123/p1234567890123456
            href = await ts_el.get_attribute("href") or ""
            match = re.search(r"/p(\d+)", href)
            if match:
                timestamp = match.group(1)
            if not timestamp:
                timestamp = datetime_str

        # Check if bot
        is_bot = False
        bot_label = await element.query_selector(selectors.BOT_LABEL)
        app_badge = await element.query_selector(selectors.APP_BADGE)
        if bot_label or app_badge:
            is_bot = True

        # Parse reactions
        reactions = await _parse_reactions(element)

        # Parse attachments
        attachments = await _parse_attachments(element)

        return Message(
            user=user.strip(),
            text=text.strip(),
            timestamp=timestamp,
            datetime_str=datetime_str.strip(),
            reactions=reactions,
            is_bot=is_bot,
            attachments=attachments,
        )
    except Exception as e:
        logger.warning("Failed to parse message element: %s", e)
        return None


async def _parse_reactions(element: ElementHandle) -> list[Reaction]:
    """Parse reaction elements from a message.

    Slack uses [data-qa="reactji"] buttons with aria-label like
    "1 reaction, react with thumbsup emoji"
    """
    reactions = []
    items = await element.query_selector_all(selectors.REACTION_ITEM)
    for item in items:
        try:
            label = await item.get_attribute("aria-label") or ""
            # Parse "1 reaction, react with thumbsup emoji"
            # or "3 reactions, react with fire emoji"
            count_match = re.match(r"(\d+)\s+reaction", label)
            emoji_match = re.search(r"react with (.+?)(?:\s+emoji)?$", label)
            count = int(count_match.group(1)) if count_match else 1
            emoji = emoji_match.group(1).strip() if emoji_match else "?"
            reactions.append(Reaction(emoji=emoji, count=count))
        except Exception:
            continue

    return reactions


async def _parse_attachments(element: ElementHandle) -> list[str]:
    """Extract attachment descriptions from a message."""
    attachments = []
    for sel in [selectors.ATTACHMENT_IMAGE, selectors.FILE_ATTACHMENT]:
        items = await element.query_selector_all(sel)
        for item in items:
            try:
                text = await item.inner_text()
                if text.strip():
                    attachments.append(text.strip()[:200])
            except Exception:
                continue
    return attachments


async def get_reply_count(element: ElementHandle) -> int:
    """Extract the reply count from a message's reply bar."""
    # Try primary selector
    reply_btn = await element.query_selector(selectors.REPLY_COUNT_BUTTON)
    if not reply_btn:
        # Fallback to class-based selector
        reply_btn = await element.query_selector(selectors.REPLY_BAR_FALLBACK)
    if not reply_btn:
        return 0
    text = await reply_btn.inner_text()
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


async def parse_messages_from_page(page: Page) -> list[Message]:
    """Parse all visible messages from the current message pane."""
    elements = await page.query_selector_all(selectors.MESSAGE_ITEM)
    messages = []
    for el in elements:
        msg = await parse_message_element(el)
        if msg:
            messages.append(msg)
    return messages

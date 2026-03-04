"""Tests for the parser module (unit tests without Playwright)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from slackcrumb.scraper.parser import parse_message_element, get_reply_count


@pytest.fixture
def mock_element():
    """Create a mock ElementHandle."""
    el = AsyncMock()

    # Sender
    sender = AsyncMock()
    sender.inner_text = AsyncMock(return_value="alice")
    el.query_selector = AsyncMock(side_effect=_mock_query_selector)

    return el


def _mock_query_selector(selector):
    """Return appropriate mock based on selector."""
    mock = AsyncMock()
    if "sender_name" in selector:
        mock.inner_text = AsyncMock(return_value="alice")
        mock.get_attribute = AsyncMock(return_value=None)
    elif "message-text" in selector or "message_kit__blocks" in selector:
        mock.inner_text = AsyncMock(return_value="Hello world")
    elif "message_timestamp" in selector:
        mock.get_attribute = AsyncMock(return_value="Jan 15, 2025 10:30 AM")
        mock.inner_text = AsyncMock(return_value="10:30 AM")
    elif "timestamp" in selector and "link" not in selector:
        mock.get_attribute = AsyncMock(return_value="10:30 AM")
    elif "c-timestamp" in selector:
        mock.get_attribute = AsyncMock(return_value="/archives/C123/p1234567890123456")
    elif "bot_label" in selector or "app_badge" in selector:
        return None
    elif "reaction" in selector:
        return None
    elif "attachment" in selector or "message_file" in selector:
        mock.query_selector_all = AsyncMock(return_value=[])
        return mock
    elif "reply_bar_count" in selector:
        mock.inner_text = AsyncMock(return_value="3 replies")
        return mock
    else:
        return None
    return mock


@pytest.mark.asyncio
async def test_parse_message_element_basic():
    """Test parsing a basic message element."""
    el = AsyncMock()

    sender = AsyncMock()
    sender.inner_text = AsyncMock(return_value="  alice  ")

    text = AsyncMock()
    text.inner_text = AsyncMock(return_value="Hello world")

    ts = AsyncMock()
    ts.get_attribute = AsyncMock(return_value="Jan 15, 2025 10:30 AM")

    ts_link = AsyncMock()
    ts_link.get_attribute = AsyncMock(return_value="/archives/C123/p1234567890123456")

    reaction_container = None

    async def side_effect(selector):
        if "sender_name" in selector:
            return sender
        if "message-text" in selector:
            return text
        if "message_kit__blocks" in selector:
            return text
        if "message_timestamp" in selector and "link" not in selector:
            return ts
        if "c-timestamp" in selector:
            return ts_link
        if "bot_label" in selector:
            return None
        if "app_badge" in selector:
            return None
        if "reactions" in selector and "reaction" not in selector.split('"')[-1]:
            return reaction_container
        return None

    el.query_selector = AsyncMock(side_effect=side_effect)
    el.query_selector_all = AsyncMock(return_value=[])

    msg = await parse_message_element(el)
    assert msg is not None
    assert msg.user == "alice"
    assert msg.text == "Hello world"
    assert msg.timestamp == "1234567890123456"
    assert msg.is_bot is False


@pytest.mark.asyncio
async def test_parse_message_element_returns_none_for_empty():
    """Test that empty elements return None."""
    el = AsyncMock()
    el.query_selector = AsyncMock(return_value=None)
    el.query_selector_all = AsyncMock(return_value=[])

    msg = await parse_message_element(el)
    assert msg is None


@pytest.mark.asyncio
async def test_get_reply_count():
    el = AsyncMock()
    btn = AsyncMock()
    btn.inner_text = AsyncMock(return_value="5 replies")
    el.query_selector = AsyncMock(return_value=btn)

    count = await get_reply_count(el)
    assert count == 5


@pytest.mark.asyncio
async def test_get_reply_count_no_replies():
    el = AsyncMock()
    el.query_selector = AsyncMock(return_value=None)

    count = await get_reply_count(el)
    assert count == 0

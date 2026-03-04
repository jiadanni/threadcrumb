"""Authentication flow — manual login with wait."""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Page

from ..exceptions import AuthError
from . import selectors

logger = logging.getLogger("slackcrumb")

LOGIN_WAIT_TIMEOUT = 300  # 5 minutes max wait for manual login
LOGIN_CHECK_INTERVAL = 2  # seconds between checks


async def is_logged_in(page: Page) -> bool:
    """Check if the user is logged into Slack.

    Uses multiple strategies: URL path, data-qa selectors, and broad DOM checks.
    """
    try:
        url = page.url

        # If we're on a login/sign-in page, definitely not logged in
        if any(p in url for p in ["/signin", "/sign_in", "oauth", "/ssb/redirect"]):
            return False

        # URL-based: if we're on /client/ or /archives/ we're in the app
        if "/client/" in url or "/archives/" in url:
            return True

        # Confirmed selectors from live Slack DOM (March 2026)
        for sel in [
            selectors.CLIENT_CONTAINER,
            selectors.MESSAGE_INPUT,
            selectors.CHANNEL_SIDEBAR,
            selectors.TOP_NAV,
            selectors.TAB_RAIL,
        ]:
            el = await page.query_selector(sel)
            if el:
                return True

        return False
    except Exception:
        return False


async def wait_for_login(page: Page, workspace_url: str) -> None:
    """Navigate to workspace and wait for user to complete manual login.

    Shows the browser window and polls for login indicators.
    Raises AuthError if timeout is reached.
    """
    url = workspace_url.rstrip("/")
    logger.info("Navigating to %s for login...", url)
    await page.goto(url, wait_until="domcontentloaded")

    # Already logged in?
    if await is_logged_in(page):
        logger.info("Already logged in!")
        return

    logger.info(
        "Please log in to Slack in the browser window. "
        "Waiting up to %d seconds...",
        LOGIN_WAIT_TIMEOUT,
    )

    elapsed = 0
    while elapsed < LOGIN_WAIT_TIMEOUT:
        await asyncio.sleep(LOGIN_CHECK_INTERVAL)
        elapsed += LOGIN_CHECK_INTERVAL

        if await is_logged_in(page):
            logger.info("Login successful!")
            return

        if elapsed % 30 == 0:
            logger.info("Still waiting for login... (%ds elapsed)", elapsed)

    raise AuthError(
        f"Login timed out after {LOGIN_WAIT_TIMEOUT}s.",
        suggestion="Try again with 'slackcrumb login'. Complete the login faster.",
    )


async def detect_session_expiry(page: Page, workspace_url: str) -> bool:
    """Check if we've been redirected to a login page (session expired)."""
    current = page.url
    if any(p in current for p in ["/signin", "/sign_in", "oauth", "/ssb/redirect"]):
        return True
    return not await is_logged_in(page)


async def handle_reauth(page: Page, workspace_url: str) -> None:
    """Pause scraping and wait for re-authentication."""
    logger.warning("Session appears to have expired. Please re-authenticate.")
    await wait_for_login(page, workspace_url)

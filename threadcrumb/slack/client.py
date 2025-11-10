"""
Slack API client with rate limiting and retry logic.
"""

import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Handle rate limiting for Slack API requests."""

    def __init__(self, min_delay: float = 1.0, max_retries: int = 3):
        """
        Initialize rate limiter.

        Args:
            min_delay: Minimum delay between requests in seconds
            max_retries: Maximum number of retries for rate limited requests
        """
        self.min_delay = min_delay
        self.max_retries = max_retries
        self.last_request_time = 0.0

    def wait(self):
        """Wait if necessary to respect rate limits."""
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.min_delay:
            wait_time = self.min_delay - time_since_last
            time.sleep(wait_time)

        self.last_request_time = time.time()

    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with exponential backoff retry.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            SlackApiError: If all retries are exhausted
        """
        retries = 0
        base_delay = 1.0

        while retries <= self.max_retries:
            try:
                self.wait()
                return func(*args, **kwargs)
            except SlackApiError as e:
                if e.response.status_code == 429:  # Rate limited
                    retry_after = int(e.response.headers.get("Retry-After", base_delay * (2 ** retries)))
                    logger.warning(f"Rate limited. Retrying after {retry_after}s...")
                    time.sleep(retry_after)
                    retries += 1
                else:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

        raise SlackApiError(
            message="Max retries exceeded",
            response={"error": "rate_limit_exceeded"}
        )


class SlackClient:
    """Enhanced Slack API client with rate limiting."""

    def __init__(
        self,
        token: str,
        rate_limit_delay: float = 1.0,
        max_retries: int = 3
    ):
        """
        Initialize Slack client.

        Args:
            token: Slack access token
            rate_limit_delay: Delay between API requests
            max_retries: Maximum retries for rate limited requests
        """
        self.client = WebClient(token=token)
        self.rate_limiter = RateLimiter(rate_limit_delay, max_retries)
        self._workspace_info: Optional[Dict[str, Any]] = None
        self._users_cache: Optional[Dict[str, Dict[str, Any]]] = None

    def get_workspace_info(self) -> Dict[str, Any]:
        """Get workspace information."""
        if self._workspace_info is None:
            response = self.rate_limiter.execute_with_retry(
                self.client.team_info
            )
            self._workspace_info = response["team"]

        return self._workspace_info

    def list_channels(self, types: str = "public_channel,private_channel") -> List[Dict[str, Any]]:
        """
        List all channels in workspace.

        Args:
            types: Channel types to include

        Returns:
            List of channel objects
        """
        channels = []
        cursor = None

        while True:
            response = self.rate_limiter.execute_with_retry(
                self.client.conversations_list,
                types=types,
                limit=200,
                cursor=cursor
            )

            channels.extend(response["channels"])

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return channels

    def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """
        Get information about a specific channel.

        Args:
            channel_id: Channel ID

        Returns:
            Channel information
        """
        response = self.rate_limiter.execute_with_retry(
            self.client.conversations_info,
            channel=channel_id
        )
        return response["channel"]

    def get_channel_history(
        self,
        channel_id: str,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get message history for a channel.

        Args:
            channel_id: Channel ID
            oldest: Oldest timestamp to include
            latest: Latest timestamp to include
            limit: Number of messages per request

        Returns:
            List of messages
        """
        messages = []
        cursor = None

        while True:
            kwargs = {
                "channel": channel_id,
                "limit": limit,
            }

            if oldest:
                kwargs["oldest"] = oldest
            if latest:
                kwargs["latest"] = latest
            if cursor:
                kwargs["cursor"] = cursor

            response = self.rate_limiter.execute_with_retry(
                self.client.conversations_history,
                **kwargs
            )

            messages.extend(response["messages"])

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor or not response["has_more"]:
                break

        return messages

    def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str
    ) -> List[Dict[str, Any]]:
        """
        Get all replies in a thread.

        Args:
            channel_id: Channel ID
            thread_ts: Thread timestamp

        Returns:
            List of messages in thread
        """
        messages = []
        cursor = None

        while True:
            kwargs = {
                "channel": channel_id,
                "ts": thread_ts,
                "limit": 100,
            }

            if cursor:
                kwargs["cursor"] = cursor

            response = self.rate_limiter.execute_with_retry(
                self.client.conversations_replies,
                **kwargs
            )

            messages.extend(response["messages"])

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor or not response["has_more"]:
                break

        return messages

    def get_users(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all users in workspace.

        Returns:
            Dictionary mapping user IDs to user info
        """
        if self._users_cache is not None:
            return self._users_cache

        users = {}
        cursor = None

        while True:
            response = self.rate_limiter.execute_with_retry(
                self.client.users_list,
                limit=200,
                cursor=cursor
            )

            for user in response["members"]:
                users[user["id"]] = user

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        self._users_cache = users
        return users

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get information about a specific user.

        Args:
            user_id: User ID

        Returns:
            User information
        """
        # Check cache first
        if self._users_cache and user_id in self._users_cache:
            return self._users_cache[user_id]

        response = self.rate_limiter.execute_with_retry(
            self.client.users_info,
            user=user_id
        )
        return response["user"]

    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        Get information about a file.

        Args:
            file_id: File ID

        Returns:
            File information
        """
        response = self.rate_limiter.execute_with_retry(
            self.client.files_info,
            file=file_id
        )
        return response["file"]

    def download_file(self, url: str, token: str) -> bytes:
        """
        Download a file from Slack.

        Args:
            url: File URL
            token: Access token

        Returns:
            File content as bytes
        """
        import requests

        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.content

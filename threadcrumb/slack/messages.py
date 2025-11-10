"""
Message fetching and thread reconstruction.
"""

import json
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import logging

from .client import SlackClient

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a Slack message."""
    ts: str
    user: str
    text: str
    channel_id: str
    thread_ts: Optional[str] = None
    reply_count: int = 0
    replies: List["Message"] = field(default_factory=list)
    reactions: List[Dict[str, Any]] = field(default_factory=list)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    files: List[Dict[str, Any]] = field(default_factory=list)
    edited: Optional[Dict[str, Any]] = None
    type: str = "message"
    subtype: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_thread_parent(self) -> bool:
        """Check if this message is a thread parent."""
        return self.reply_count > 0

    @property
    def is_thread_reply(self) -> bool:
        """Check if this message is a thread reply."""
        return self.thread_ts is not None and self.thread_ts != self.ts

    @property
    def timestamp(self) -> datetime:
        """Get message timestamp as datetime."""
        return datetime.fromtimestamp(float(self.ts))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["is_thread_parent"] = self.is_thread_parent
        data["is_thread_reply"] = self.is_thread_reply
        return data


@dataclass
class Thread:
    """Represents a Slack thread."""
    thread_ts: str
    channel_id: str
    parent: Message
    replies: List[Message] = field(default_factory=list)
    participants: Set[str] = field(default_factory=set)

    @property
    def message_count(self) -> int:
        """Total messages in thread including parent."""
        return 1 + len(self.replies)

    @property
    def created_at(self) -> datetime:
        """Thread creation time."""
        return self.parent.timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "thread_ts": self.thread_ts,
            "channel_id": self.channel_id,
            "parent": self.parent.to_dict(),
            "replies": [r.to_dict() for r in self.replies],
            "participants": list(self.participants),
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat()
        }


class MessageFetcher:
    """Fetch messages from Slack channels."""

    def __init__(
        self,
        client: SlackClient,
        cache_dir: Optional[Path] = None,
        cache_enabled: bool = True
    ):
        """
        Initialize message fetcher.

        Args:
            client: Slack client instance
            cache_dir: Directory for caching messages
            cache_enabled: Whether to cache messages
        """
        self.client = client
        self.cache_enabled = cache_enabled
        self.cache_dir = cache_dir or Path(".threadcrumb/cache")

        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, channel_id: str) -> Path:
        """Get cache file path for a channel."""
        return self.cache_dir / f"{channel_id}.json"

    def _load_from_cache(self, channel_id: str) -> Optional[List[Dict[str, Any]]]:
        """Load messages from cache."""
        if not self.cache_enabled:
            return None

        cache_path = self._get_cache_path(channel_id)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                return data.get("messages", [])
        except Exception as e:
            logger.warning(f"Failed to load cache for {channel_id}: {e}")
            return None

    def _save_to_cache(self, channel_id: str, messages: List[Dict[str, Any]]) -> None:
        """Save messages to cache."""
        if not self.cache_enabled:
            return

        cache_path = self._get_cache_path(channel_id)
        try:
            with open(cache_path, 'w') as f:
                json.dump({
                    "channel_id": channel_id,
                    "fetched_at": datetime.now().isoformat(),
                    "message_count": len(messages),
                    "messages": messages
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache for {channel_id}: {e}")

    def fetch_channel_messages(
        self,
        channel_id: str,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Message]:
        """
        Fetch all messages from a channel.

        Args:
            channel_id: Channel ID
            oldest: Oldest timestamp to fetch
            latest: Latest timestamp to fetch
            use_cache: Whether to use cached data

        Returns:
            List of Message objects
        """
        # Try cache first
        if use_cache:
            cached = self._load_from_cache(channel_id)
            if cached:
                logger.info(f"Loaded {len(cached)} messages from cache for {channel_id}")
                return [self._dict_to_message(m, channel_id) for m in cached]

        # Fetch from API
        logger.info(f"Fetching messages for channel {channel_id}...")
        raw_messages = self.client.get_channel_history(
            channel_id=channel_id,
            oldest=oldest,
            latest=latest
        )

        # Cache raw messages
        self._save_to_cache(channel_id, raw_messages)

        # Convert to Message objects
        messages = [self._dict_to_message(m, channel_id) for m in raw_messages]

        logger.info(f"Fetched {len(messages)} messages from {channel_id}")
        return messages

    def fetch_thread_replies(
        self,
        channel_id: str,
        thread_ts: str
    ) -> List[Message]:
        """
        Fetch all replies in a thread.

        Args:
            channel_id: Channel ID
            thread_ts: Thread timestamp

        Returns:
            List of Message objects (includes parent)
        """
        raw_messages = self.client.get_thread_replies(channel_id, thread_ts)
        return [self._dict_to_message(m, channel_id) for m in raw_messages]

    def _dict_to_message(self, msg_dict: Dict[str, Any], channel_id: str) -> Message:
        """Convert raw message dict to Message object."""
        return Message(
            ts=msg_dict.get("ts", ""),
            user=msg_dict.get("user", msg_dict.get("bot_id", "unknown")),
            text=msg_dict.get("text", ""),
            channel_id=channel_id,
            thread_ts=msg_dict.get("thread_ts"),
            reply_count=msg_dict.get("reply_count", 0),
            reactions=msg_dict.get("reactions", []),
            attachments=msg_dict.get("attachments", []),
            files=msg_dict.get("files", []),
            edited=msg_dict.get("edited"),
            type=msg_dict.get("type", "message"),
            subtype=msg_dict.get("subtype"),
            raw=msg_dict
        )


class ThreadReconstructor:
    """Reconstruct conversation threads from messages."""

    def __init__(self, max_depth: int = 50):
        """
        Initialize thread reconstructor.

        Args:
            max_depth: Maximum thread depth to process
        """
        self.max_depth = max_depth

    def reconstruct_threads(
        self,
        messages: List[Message],
        fetch_replies: bool = True,
        message_fetcher: Optional[MessageFetcher] = None
    ) -> List[Thread]:
        """
        Reconstruct threads from a list of messages.

        Args:
            messages: List of messages
            fetch_replies: Whether to fetch full thread replies
            message_fetcher: MessageFetcher for fetching replies

        Returns:
            List of Thread objects
        """
        # Group messages by thread_ts
        thread_map: Dict[str, List[Message]] = defaultdict(list)
        standalone_messages: List[Message] = []

        for msg in messages:
            if msg.is_thread_parent or msg.thread_ts:
                # Use thread_ts as key, or ts if it's a parent
                thread_key = msg.thread_ts or msg.ts
                thread_map[thread_key].append(msg)
            else:
                standalone_messages.append(msg)

        # Build Thread objects
        threads: List[Thread] = []

        for thread_ts, thread_messages in thread_map.items():
            # Find parent message (the one where ts == thread_ts)
            parent = None
            replies = []

            for msg in thread_messages:
                if msg.ts == thread_ts:
                    parent = msg
                else:
                    replies.append(msg)

            if not parent:
                logger.warning(f"No parent found for thread {thread_ts}")
                continue

            # Fetch full replies if needed
            if fetch_replies and parent.reply_count > len(replies) and message_fetcher:
                try:
                    full_thread = message_fetcher.fetch_thread_replies(
                        parent.channel_id,
                        thread_ts
                    )
                    # Remove parent from replies
                    replies = [m for m in full_thread if m.ts != thread_ts]
                except Exception as e:
                    logger.warning(f"Failed to fetch replies for thread {thread_ts}: {e}")

            # Sort replies by timestamp
            replies.sort(key=lambda m: m.ts)

            # Limit depth
            if len(replies) > self.max_depth:
                logger.warning(f"Thread {thread_ts} exceeds max depth, truncating")
                replies = replies[:self.max_depth]

            # Collect participants
            participants = {parent.user}
            participants.update(r.user for r in replies)

            thread = Thread(
                thread_ts=thread_ts,
                channel_id=parent.channel_id,
                parent=parent,
                replies=replies,
                participants=participants
            )

            threads.append(thread)

        # Sort threads by creation time
        threads.sort(key=lambda t: t.created_at, reverse=True)

        logger.info(f"Reconstructed {len(threads)} threads from {len(messages)} messages")
        return threads

    def group_by_conversation(
        self,
        messages: List[Message],
        time_gap_minutes: int = 30
    ) -> List[List[Message]]:
        """
        Group messages into conversations based on time gaps.

        Args:
            messages: List of messages
            time_gap_minutes: Minutes of silence to consider new conversation

        Returns:
            List of conversation groups
        """
        if not messages:
            return []

        # Sort by timestamp
        sorted_messages = sorted(messages, key=lambda m: m.ts)

        conversations: List[List[Message]] = []
        current_conversation: List[Message] = [sorted_messages[0]]

        for i in range(1, len(sorted_messages)):
            prev_msg = sorted_messages[i - 1]
            curr_msg = sorted_messages[i]

            time_diff = curr_msg.timestamp - prev_msg.timestamp
            gap_minutes = time_diff.total_seconds() / 60

            if gap_minutes > time_gap_minutes:
                # Start new conversation
                conversations.append(current_conversation)
                current_conversation = [curr_msg]
            else:
                current_conversation.append(curr_msg)

        # Add last conversation
        if current_conversation:
            conversations.append(current_conversation)

        return conversations

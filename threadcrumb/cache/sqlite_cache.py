"""
SQLite-based caching for improved performance.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SQLiteCache:
    """SQLite cache for Slack messages and metadata."""

    def __init__(self, db_path: Path = None):
        """
        Initialize SQLite cache.

        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = Path.home() / ".threadcrumb" / "cache" / "messages.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        cursor = self.conn.cursor()

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                ts TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                user_id TEXT,
                text TEXT,
                thread_ts TEXT,
                reply_count INTEGER DEFAULT 0,
                data JSON NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_channel (channel_id),
                INDEX idx_thread (thread_ts)
            )
        """)

        # Channels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                data JSON NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                real_name TEXT,
                data JSON NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Sync metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_meta (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()
        logger.debug("Initialized SQLite cache schema")

    def save_messages(
        self,
        channel_id: str,
        messages: List[Dict[str, Any]]
    ) -> None:
        """
        Save messages to cache.

        Args:
            channel_id: Channel ID
            messages: List of message dictionaries
        """
        cursor = self.conn.cursor()

        for msg in messages:
            cursor.execute("""
                INSERT OR REPLACE INTO messages
                (ts, channel_id, user_id, text, thread_ts, reply_count, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                msg.get('ts'),
                channel_id,
                msg.get('user'),
                msg.get('text', ''),
                msg.get('thread_ts'),
                msg.get('reply_count', 0),
                json.dumps(msg)
            ))

        self.conn.commit()
        logger.debug(f"Cached {len(messages)} messages for channel {channel_id}")

    def get_messages(
        self,
        channel_id: str,
        since_ts: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages from cache.

        Args:
            channel_id: Channel ID
            since_ts: Optional timestamp to get messages after

        Returns:
            List of message dictionaries
        """
        cursor = self.conn.cursor()

        if since_ts:
            cursor.execute("""
                SELECT data FROM messages
                WHERE channel_id = ? AND ts > ?
                ORDER BY ts DESC
            """, (channel_id, since_ts))
        else:
            cursor.execute("""
                SELECT data FROM messages
                WHERE channel_id = ?
                ORDER BY ts DESC
            """, (channel_id,))

        messages = [json.loads(row['data']) for row in cursor.fetchall()]
        logger.debug(f"Retrieved {len(messages)} messages from cache for channel {channel_id}")

        return messages

    def get_message_count(self, channel_id: str) -> int:
        """
        Get count of cached messages for channel.

        Args:
            channel_id: Channel ID

        Returns:
            Message count
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM messages WHERE channel_id = ?",
            (channel_id,)
        )
        return cursor.fetchone()['count']

    def save_channel(self, channel: Dict[str, Any]) -> None:
        """
        Save channel metadata.

        Args:
            channel: Channel dictionary
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO channels (channel_id, name, data)
            VALUES (?, ?, ?)
        """, (
            channel['id'],
            channel.get('name', ''),
            json.dumps(channel)
        ))

        self.conn.commit()
        logger.debug(f"Cached channel {channel.get('name')}")

    def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get channel metadata.

        Args:
            channel_id: Channel ID

        Returns:
            Channel dictionary or None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT data FROM channels WHERE channel_id = ?",
            (channel_id,)
        )

        row = cursor.fetchone()
        return json.loads(row['data']) if row else None

    def save_users(self, users: Dict[str, Dict[str, Any]]) -> None:
        """
        Save user metadata.

        Args:
            users: Dictionary of user_id -> user data
        """
        cursor = self.conn.cursor()

        for user_id, user_data in users.items():
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_id, name, real_name, data)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                user_data.get('name', ''),
                user_data.get('real_name', ''),
                json.dumps(user_data)
            ))

        self.conn.commit()
        logger.debug(f"Cached {len(users)} users")

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user metadata.

        Args:
            user_id: User ID

        Returns:
            User dictionary or None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT data FROM users WHERE user_id = ?",
            (user_id,)
        )

        row = cursor.fetchone()
        return json.loads(row['data']) if row else None

    def set_meta(self, key: str, value: str) -> None:
        """
        Set metadata value.

        Args:
            key: Metadata key
            value: Metadata value
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sync_meta (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))

        self.conn.commit()

    def get_meta(self, key: str) -> Optional[str]:
        """
        Get metadata value.

        Args:
            key: Metadata key

        Returns:
            Metadata value or None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT value FROM sync_meta WHERE key = ?",
            (key,)
        )

        row = cursor.fetchone()
        return row['value'] if row else None

    def clear_channel(self, channel_id: str) -> None:
        """
        Clear all messages for a channel.

        Args:
            channel_id: Channel ID
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM messages WHERE channel_id = ?",
            (channel_id,)
        )
        self.conn.commit()
        logger.info(f"Cleared cache for channel {channel_id}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Statistics dictionary
        """
        cursor = self.conn.cursor()

        # Total messages
        cursor.execute("SELECT COUNT(*) as count FROM messages")
        total_messages = cursor.fetchone()['count']

        # Total channels
        cursor.execute("SELECT COUNT(*) as count FROM channels")
        total_channels = cursor.fetchone()['count']

        # Total users
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()['count']

        # Database size
        db_size = self.db_path.stat().st_size / (1024 * 1024)  # MB

        return {
            'total_messages': total_messages,
            'total_channels': total_channels,
            'total_users': total_users,
            'db_size_mb': round(db_size, 2),
            'db_path': str(self.db_path)
        }

    def vacuum(self) -> None:
        """Vacuum database to reclaim space."""
        cursor = self.conn.cursor()
        cursor.execute("VACUUM")
        self.conn.commit()
        logger.info("Vacuumed cache database")

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

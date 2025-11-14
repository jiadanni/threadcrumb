"""
Sync state tracking for incremental updates.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SyncState:
    """State for a single channel sync."""
    channel_id: str
    channel_name: str
    last_sync_ts: float
    last_message_ts: Optional[str] = None
    message_count: int = 0
    thread_count: int = 0
    last_error: Optional[str] = None
    synced_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncState":
        """Create from dictionary."""
        return cls(**data)


class SyncTracker:
    """Track sync state for incremental updates."""

    def __init__(self, state_file: Path = None):
        """
        Initialize sync tracker.

        Args:
            state_file: Path to state file (default: .threadcrumb/sync_state.json)
        """
        if state_file is None:
            state_file = Path.home() / ".threadcrumb" / "sync_state.json"

        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        self.states: Dict[str, SyncState] = {}
        self._load_state()

    def _load_state(self) -> None:
        """Load state from file."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)

            for channel_id, state_dict in data.items():
                self.states[channel_id] = SyncState.from_dict(state_dict)

            logger.info(f"Loaded sync state for {len(self.states)} channels")

        except Exception as e:
            logger.error(f"Failed to load sync state: {e}")
            self.states = {}

    def _save_state(self) -> None:
        """Save state to file."""
        try:
            data = {
                channel_id: state.to_dict()
                for channel_id, state in self.states.items()
            }

            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved sync state for {len(self.states)} channels")

        except Exception as e:
            logger.error(f"Failed to save sync state: {e}")

    def get_last_sync(self, channel_id: str) -> Optional[float]:
        """
        Get timestamp of last sync for channel.

        Args:
            channel_id: Channel ID

        Returns:
            Last sync timestamp or None if never synced
        """
        state = self.states.get(channel_id)
        return state.last_sync_ts if state else None

    def get_last_message_ts(self, channel_id: str) -> Optional[str]:
        """
        Get timestamp of last message for channel.

        Args:
            channel_id: Channel ID

        Returns:
            Last message timestamp or None
        """
        state = self.states.get(channel_id)
        return state.last_message_ts if state else None

    def update_sync(
        self,
        channel_id: str,
        channel_name: str,
        message_count: int = 0,
        thread_count: int = 0,
        last_message_ts: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update sync state for a channel.

        Args:
            channel_id: Channel ID
            channel_name: Channel name
            message_count: Number of messages synced
            thread_count: Number of threads synced
            last_message_ts: Timestamp of last message
            error: Error message if sync failed
        """
        import time

        state = SyncState(
            channel_id=channel_id,
            channel_name=channel_name,
            last_sync_ts=time.time(),
            last_message_ts=last_message_ts,
            message_count=message_count,
            thread_count=thread_count,
            last_error=error,
            synced_at=datetime.now().isoformat()
        )

        self.states[channel_id] = state
        self._save_state()

        logger.info(
            f"Updated sync state for #{channel_name}: "
            f"{message_count} messages, {thread_count} threads"
        )

    def get_state(self, channel_id: str) -> Optional[SyncState]:
        """
        Get complete sync state for a channel.

        Args:
            channel_id: Channel ID

        Returns:
            SyncState or None
        """
        return self.states.get(channel_id)

    def get_all_states(self) -> Dict[str, SyncState]:
        """
        Get all sync states.

        Returns:
            Dictionary of channel_id -> SyncState
        """
        return self.states.copy()

    def clear_state(self, channel_id: Optional[str] = None) -> None:
        """
        Clear sync state.

        Args:
            channel_id: Specific channel to clear, or None for all
        """
        if channel_id:
            self.states.pop(channel_id, None)
            logger.info(f"Cleared sync state for channel {channel_id}")
        else:
            self.states.clear()
            logger.info("Cleared all sync states")

        self._save_state()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about sync states.

        Returns:
            Statistics dictionary
        """
        if not self.states:
            return {
                "total_channels": 0,
                "total_messages": 0,
                "total_threads": 0
            }

        total_messages = sum(s.message_count for s in self.states.values())
        total_threads = sum(s.thread_count for s in self.states.values())

        latest_sync = max(
            (s.last_sync_ts for s in self.states.values()),
            default=0
        )

        return {
            "total_channels": len(self.states),
            "total_messages": total_messages,
            "total_threads": total_threads,
            "latest_sync": datetime.fromtimestamp(latest_sync).isoformat() if latest_sync else None
        }

    def is_synced(self, channel_id: str) -> bool:
        """
        Check if channel has been synced before.

        Args:
            channel_id: Channel ID

        Returns:
            True if channel has sync state
        """
        return channel_id in self.states

    def should_sync(
        self,
        channel_id: str,
        max_age_hours: int = 24
    ) -> bool:
        """
        Check if channel should be synced based on age.

        Args:
            channel_id: Channel ID
            max_age_hours: Maximum age in hours before re-sync

        Returns:
            True if should sync
        """
        import time

        state = self.states.get(channel_id)
        if not state:
            return True  # Never synced

        age_hours = (time.time() - state.last_sync_ts) / 3600
        return age_hours >= max_age_hours

    def needs_full_sync(self, channel_id: str) -> bool:
        """
        Check if channel needs full sync (vs incremental).

        Args:
            channel_id: Channel ID

        Returns:
            True if full sync needed
        """
        state = self.states.get(channel_id)
        if not state:
            return True

        # Full sync if last sync had errors
        if state.last_error:
            return True

        # Full sync if no messages found
        if state.message_count == 0:
            return True

        return False

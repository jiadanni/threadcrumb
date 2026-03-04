"""JSON checkpoint/resumption system for scrape progress."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import DEFAULT_CONFIG_DIR
from .exceptions import CheckpointError

logger = logging.getLogger("slackcrumb")

CHECKPOINT_DIR = DEFAULT_CONFIG_DIR / "checkpoints"
CACHE_DIR = DEFAULT_CONFIG_DIR / "cache"


@dataclass
class ChannelProgress:
    name: str
    status: str = "pending"  # pending, in_progress, completed, failed
    last_message_ts: str = ""
    message_count: int = 0
    expanded_threads: list[str] = field(default_factory=list)


@dataclass
class CheckpointData:
    export_id: str = ""
    workspace_url: str = ""
    channels: dict[str, ChannelProgress] = field(default_factory=dict)
    search_query: str | None = None
    created_at: str = ""
    updated_at: str = ""
    format: str = "json"

    def to_dict(self) -> dict:
        return {
            "export_id": self.export_id,
            "workspace_url": self.workspace_url,
            "channels": {
                name: {
                    "status": cp.status,
                    "last_message_ts": cp.last_message_ts,
                    "message_count": cp.message_count,
                    "expanded_threads": cp.expanded_threads,
                }
                for name, cp in self.channels.items()
            },
            "search_query": self.search_query,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "format": self.format,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CheckpointData:
        channels = {}
        for name, cp_data in data.get("channels", {}).items():
            channels[name] = ChannelProgress(
                name=name,
                status=cp_data.get("status", "pending"),
                last_message_ts=cp_data.get("last_message_ts", ""),
                message_count=cp_data.get("message_count", 0),
                expanded_threads=cp_data.get("expanded_threads", []),
            )
        return cls(
            export_id=data.get("export_id", ""),
            workspace_url=data.get("workspace_url", ""),
            channels=channels,
            search_query=data.get("search_query"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            format=data.get("format", "json"),
        )


class Checkpoint:
    """Manages checkpoint persistence for scrape resumption."""

    def __init__(self, export_id: str | None = None, workspace_url: str = ""):
        self.data = CheckpointData(
            export_id=export_id or uuid.uuid4().hex[:12],
            workspace_url=workspace_url,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        self._path = CHECKPOINT_DIR / f"{self.data.export_id}.json"

    @property
    def export_id(self) -> str:
        return self.data.export_id

    def save(self) -> None:
        """Save checkpoint to disk."""
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        self.data.updated_at = datetime.now().isoformat()
        try:
            with open(self._path, "w") as f:
                json.dump(self.data.to_dict(), f, indent=2)
        except OSError as e:
            raise CheckpointError(f"Failed to save checkpoint: {e}")

    @classmethod
    def load(cls, export_id: str) -> Checkpoint:
        """Load an existing checkpoint."""
        path = CHECKPOINT_DIR / f"{export_id}.json"
        if not path.exists():
            raise CheckpointError(
                f"Checkpoint '{export_id}' not found.",
                suggestion="Run 'slackcrumb status' to see available checkpoints.",
            )
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise CheckpointError(f"Failed to load checkpoint: {e}")

        cp = cls.__new__(cls)
        cp.data = CheckpointData.from_dict(data)
        cp._path = path
        return cp

    @classmethod
    def find_resumable(cls) -> list[dict]:
        """List all checkpoints that can be resumed."""
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        results = []
        for path in CHECKPOINT_DIR.glob("*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                channels = data.get("channels", {})
                completed = sum(1 for c in channels.values() if c.get("status") == "completed")
                total = len(channels)
                results.append({
                    "export_id": data.get("export_id", path.stem),
                    "workspace": data.get("workspace_url", ""),
                    "channels": f"{completed}/{total} completed",
                    "updated": data.get("updated_at", ""),
                    "search_query": data.get("search_query"),
                })
            except (json.JSONDecodeError, OSError):
                continue
        return sorted(results, key=lambda r: r.get("updated", ""), reverse=True)

    def update_channel(self, channel: str, last_ts: str, msg_count: int) -> None:
        if channel not in self.data.channels:
            self.data.channels[channel] = ChannelProgress(name=channel)
        cp = self.data.channels[channel]
        cp.status = "in_progress"
        cp.last_message_ts = last_ts
        cp.message_count = msg_count

    def mark_channel_complete(self, channel: str) -> None:
        if channel not in self.data.channels:
            self.data.channels[channel] = ChannelProgress(name=channel)
        self.data.channels[channel].status = "completed"

    def is_channel_complete(self, channel: str) -> bool:
        cp = self.data.channels.get(channel)
        return cp is not None and cp.status == "completed"

    def get_last_timestamp(self, channel: str) -> str:
        cp = self.data.channels.get(channel)
        return cp.last_message_ts if cp else ""

    def mark_thread_expanded(self, channel: str, timestamp: str) -> None:
        if channel not in self.data.channels:
            self.data.channels[channel] = ChannelProgress(name=channel)
        if timestamp not in self.data.channels[channel].expanded_threads:
            self.data.channels[channel].expanded_threads.append(timestamp)

    def is_thread_expanded(self, channel: str, timestamp: str) -> bool:
        cp = self.data.channels.get(channel)
        return cp is not None and timestamp in cp.expanded_threads

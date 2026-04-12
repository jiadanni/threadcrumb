"""Data models for Slack messages, threads, and exports."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Reaction:
    emoji: str
    count: int = 1


@dataclass
class Message:
    user: str
    text: str
    timestamp: str  # unique identifier within a channel
    datetime_str: str = ""
    reactions: list[Reaction] = field(default_factory=list)
    is_bot: bool = False
    attachments: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "user": self.user,
            "text": self.text,
            "timestamp": self.timestamp,
            "datetime": self.datetime_str,
            "reactions": [{"emoji": r.emoji, "count": r.count} for r in self.reactions],
            "is_bot": self.is_bot,
            "attachments": self.attachments,
        }


@dataclass
class Thread:
    parent: Message
    replies: list[Message] = field(default_factory=list)
    reply_count: int = 0

    def to_dict(self) -> dict:
        return {
            "parent": self.parent.to_dict(),
            "replies": [r.to_dict() for r in self.replies],
            "reply_count": self.reply_count or len(self.replies),
        }


@dataclass
class ChannelExport:
    name: str
    threads: list[Thread] = field(default_factory=list)
    standalone_messages: list[Message] = field(default_factory=list)
    export_started: str = ""
    export_finished: str = ""
    total_messages: int = 0
    status: str = "pending"  # pending, in_progress, completed, failed

    def to_dict(self) -> dict:
        return {
            "channel": self.name,
            "status": self.status,
            "export_started": self.export_started,
            "export_finished": self.export_finished,
            "total_messages": self.total_messages,
            "threads": [t.to_dict() for t in self.threads],
            "standalone_messages": [m.to_dict() for m in self.standalone_messages],
        }


@dataclass
class ExportResult:
    workspace: str
    channels: list[ChannelExport] = field(default_factory=list)
    export_date: str = ""
    format_version: str = "1.0"

    def to_dict(self) -> dict:
        return {
            "workspace": self.workspace,
            "export_date": self.export_date,
            "format_version": self.format_version,
            "channels": [c.to_dict() for c in self.channels],
        }

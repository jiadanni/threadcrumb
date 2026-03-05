"""
Checkpoint and resumption system for export operations.

Allows large exports to be resumed after interruptions or failures.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ExportState(str, Enum):
    """Export operation states."""
    STARTED = "started"
    FETCHING_CHANNELS = "fetching_channels"
    PROCESSING_CHANNELS = "processing_channels"
    GENERATING_OUTPUT = "generating_output"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExportCheckpoint:
    """Represents a checkpoint in the export process."""

    # Export metadata
    export_id: str
    state: ExportState
    started_at: str
    updated_at: str

    # Channel processing state
    total_channels: int = 0
    processed_channels: List[str] = field(default_factory=list)
    failed_channels: List[str] = field(default_factory=list)

    # Thread processing state (channel_id -> list of thread_ts)
    processed_threads: Dict[str, List[str]] = field(default_factory=dict)

    # Output generation state
    output_format: Optional[str] = None
    output_path: Optional[str] = None

    # Error tracking
    last_error: Optional[str] = None
    retry_count: int = 0

    # Statistics
    total_threads: int = 0
    total_messages: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ExportCheckpoint':
        """Create from dictionary."""
        return cls(**data)

    def is_channel_processed(self, channel_id: str) -> bool:
        """Check if a channel has been processed."""
        return channel_id in self.processed_channels

    def is_thread_processed(self, channel_id: str, thread_ts: str) -> bool:
        """Check if a specific thread has been processed."""
        return thread_ts in self.processed_threads.get(channel_id, [])

    def mark_channel_started(self, channel_id: str):
        """Mark a channel as being processed."""
        if channel_id not in self.processed_channels and channel_id not in self.failed_channels:
            logger.debug(f"Starting channel: {channel_id}")

    def mark_channel_completed(self, channel_id: str, thread_count: int = 0):
        """Mark a channel as successfully processed."""
        if channel_id not in self.processed_channels:
            self.processed_channels.append(channel_id)
            self.total_threads += thread_count
            logger.info(f"Completed channel: {channel_id} ({thread_count} threads)")

    def mark_channel_failed(self, channel_id: str, error: str):
        """Mark a channel as failed."""
        if channel_id not in self.failed_channels:
            self.failed_channels.append(channel_id)
            self.last_error = error
            logger.error(f"Failed channel: {channel_id} - {error}")

    def mark_thread_processed(self, channel_id: str, thread_ts: str):
        """Mark a specific thread as processed."""
        if channel_id not in self.processed_threads:
            self.processed_threads[channel_id] = []
        if thread_ts not in self.processed_threads[channel_id]:
            self.processed_threads[channel_id].append(thread_ts)

    def get_pending_channels(self, all_channel_ids: List[str]) -> List[str]:
        """Get list of channels that still need to be processed."""
        processed_set = set(self.processed_channels)
        return [ch_id for ch_id in all_channel_ids if ch_id not in processed_set]

    def get_progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_channels == 0:
            return 0.0
        completed = len(self.processed_channels)
        return (completed / self.total_channels) * 100


class CheckpointManager:
    """Manages export checkpoints for resumption."""

    def __init__(self, checkpoint_dir: Path = None):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = checkpoint_dir or Path.home() / ".threadcrumb" / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def create_checkpoint(
        self,
        export_id: str,
        total_channels: int,
        output_format: str = None,
        output_path: str = None
    ) -> ExportCheckpoint:
        """
        Create a new checkpoint for an export.

        Args:
            export_id: Unique identifier for this export
            total_channels: Total number of channels to process
            output_format: Output format (markdown, html, etc.)
            output_path: Output path

        Returns:
            New ExportCheckpoint
        """
        now = datetime.utcnow().isoformat()

        checkpoint = ExportCheckpoint(
            export_id=export_id,
            state=ExportState.STARTED,
            started_at=now,
            updated_at=now,
            total_channels=total_channels,
            output_format=output_format,
            output_path=output_path
        )

        self.save_checkpoint(checkpoint)
        logger.info(f"Created checkpoint for export: {export_id}")

        return checkpoint

    def load_checkpoint(self, export_id: str) -> Optional[ExportCheckpoint]:
        """
        Load a checkpoint by ID.

        Args:
            export_id: Export identifier

        Returns:
            ExportCheckpoint if found, None otherwise
        """
        checkpoint_file = self.checkpoint_dir / f"{export_id}.json"

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, 'r') as f:
                data = json.load(f)

            checkpoint = ExportCheckpoint.from_dict(data)
            logger.info(f"Loaded checkpoint for export: {export_id}")

            return checkpoint

        except Exception as e:
            logger.error(f"Error loading checkpoint {export_id}: {e}")
            return None

    def save_checkpoint(self, checkpoint: ExportCheckpoint):
        """
        Save a checkpoint to disk.

        Args:
            checkpoint: Checkpoint to save
        """
        checkpoint.updated_at = datetime.utcnow().isoformat()
        checkpoint_file = self.checkpoint_dir / f"{checkpoint.export_id}.json"

        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint.to_dict(), f, indent=2)

            logger.debug(f"Saved checkpoint for export: {checkpoint.export_id}")

        except Exception as e:
            logger.error(f"Error saving checkpoint {checkpoint.export_id}: {e}")

    def delete_checkpoint(self, export_id: str):
        """
        Delete a checkpoint file.

        Args:
            export_id: Export identifier
        """
        checkpoint_file = self.checkpoint_dir / f"{export_id}.json"

        if checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info(f"Deleted checkpoint: {export_id}")

    def list_checkpoints(self) -> List[ExportCheckpoint]:
        """
        List all available checkpoints.

        Returns:
            List of checkpoints
        """
        checkpoints = []

        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                checkpoints.append(ExportCheckpoint.from_dict(data))
            except Exception as e:
                logger.error(f"Error reading checkpoint {checkpoint_file}: {e}")

        return sorted(checkpoints, key=lambda c: c.updated_at, reverse=True)

    def find_resumable_export(
        self,
        output_format: str = None,
        output_path: str = None
    ) -> Optional[ExportCheckpoint]:
        """
        Find a resumable export matching the criteria.

        Args:
            output_format: Filter by output format
            output_path: Filter by output path

        Returns:
            Most recent matching checkpoint, or None
        """
        checkpoints = self.list_checkpoints()

        for checkpoint in checkpoints:
            # Only resume non-completed exports
            if checkpoint.state in [ExportState.COMPLETED]:
                continue

            # Match criteria
            if output_format and checkpoint.output_format != output_format:
                continue

            if output_path and checkpoint.output_path != output_path:
                continue

            return checkpoint

        return None

    def cleanup_old_checkpoints(self, keep_count: int = 10):
        """
        Clean up old checkpoints, keeping only the most recent ones.

        Args:
            keep_count: Number of checkpoints to keep
        """
        checkpoints = self.list_checkpoints()

        if len(checkpoints) <= keep_count:
            return

        # Delete oldest checkpoints
        to_delete = checkpoints[keep_count:]

        for checkpoint in to_delete:
            self.delete_checkpoint(checkpoint.export_id)

        logger.info(f"Cleaned up {len(to_delete)} old checkpoints")

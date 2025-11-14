"""Tests for export resumption and checkpoint system."""

import pytest
from pathlib import Path
from threadcrumb.resumption import CheckpointManager, ExportCheckpoint, ExportState


class TestExportCheckpoint:
    """Test ExportCheckpoint functionality."""

    def test_create_checkpoint(self):
        """Test checkpoint creation."""
        checkpoint = ExportCheckpoint(
            export_id="test123",
            state=ExportState.STARTED,
            started_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            total_channels=10
        )

        assert checkpoint.export_id == "test123"
        assert checkpoint.state == ExportState.STARTED
        assert checkpoint.total_channels == 10
        assert len(checkpoint.processed_channels) == 0

    def test_mark_channel_completed(self):
        """Test marking channel as completed."""
        checkpoint = ExportCheckpoint(
            export_id="test123",
            state=ExportState.PROCESSING_CHANNELS,
            started_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            total_channels=10
        )

        checkpoint.mark_channel_completed("C123", thread_count=5)

        assert "C123" in checkpoint.processed_channels
        assert checkpoint.total_threads == 5

    def test_mark_channel_failed(self):
        """Test marking channel as failed."""
        checkpoint = ExportCheckpoint(
            export_id="test123",
            state=ExportState.PROCESSING_CHANNELS,
            started_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            total_channels=10
        )

        checkpoint.mark_channel_failed("C123", "Network error")

        assert "C123" in checkpoint.failed_channels
        assert "Network error" in checkpoint.last_error

    def test_is_channel_processed(self):
        """Test channel processing status check."""
        checkpoint = ExportCheckpoint(
            export_id="test123",
            state=ExportState.PROCESSING_CHANNELS,
            started_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            total_channels=10,
            processed_channels=["C123", "C456"]
        )

        assert checkpoint.is_channel_processed("C123")
        assert not checkpoint.is_channel_processed("C789")

    def test_get_pending_channels(self):
        """Test getting pending channels."""
        checkpoint = ExportCheckpoint(
            export_id="test123",
            state=ExportState.PROCESSING_CHANNELS,
            started_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            total_channels=5,
            processed_channels=["C123", "C456"]
        )

        all_channels = ["C123", "C456", "C789", "C012"]
        pending = checkpoint.get_pending_channels(all_channels)

        assert len(pending) == 2
        assert "C789" in pending
        assert "C012" in pending
        assert "C123" not in pending

    def test_get_progress_percentage(self):
        """Test progress calculation."""
        checkpoint = ExportCheckpoint(
            export_id="test123",
            state=ExportState.PROCESSING_CHANNELS,
            started_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            total_channels=10,
            processed_channels=["C1", "C2", "C3", "C4", "C5"]
        )

        progress = checkpoint.get_progress_percentage()
        assert progress == 50.0

    def test_to_dict_from_dict(self):
        """Test serialization and deserialization."""
        original = ExportCheckpoint(
            export_id="test123",
            state=ExportState.PROCESSING_CHANNELS,
            started_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            total_channels=10,
            processed_channels=["C123"],
            output_format="markdown"
        )

        # Serialize
        data = original.to_dict()
        assert data["export_id"] == "test123"
        assert data["state"] == ExportState.PROCESSING_CHANNELS

        # Deserialize
        restored = ExportCheckpoint.from_dict(data)
        assert restored.export_id == original.export_id
        assert restored.state == original.state
        assert restored.processed_channels == original.processed_channels


class TestCheckpointManager:
    """Test CheckpointManager functionality."""

    def test_create_checkpoint(self, tmp_path):
        """Test checkpoint creation."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        checkpoint = manager.create_checkpoint(
            export_id="test123",
            total_channels=10,
            output_format="markdown",
            output_path="/tmp/output"
        )

        assert checkpoint.export_id == "test123"
        assert checkpoint.total_channels == 10
        assert checkpoint.output_format == "markdown"

        # Verify file was created
        checkpoint_file = tmp_path / "test123.json"
        assert checkpoint_file.exists()

    def test_save_checkpoint(self, tmp_path):
        """Test checkpoint persistence."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        checkpoint = ExportCheckpoint(
            export_id="test456",
            state=ExportState.PROCESSING_CHANNELS,
            started_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            total_channels=5
        )

        manager.save_checkpoint(checkpoint)

        # Verify file exists
        checkpoint_file = tmp_path / "test456.json"
        assert checkpoint_file.exists()

    def test_load_checkpoint(self, tmp_path):
        """Test checkpoint loading."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        # Create checkpoint
        original = manager.create_checkpoint(
            export_id="test789",
            total_channels=15,
            output_format="html"
        )

        # Modify and save
        original.mark_channel_completed("C123", 5)
        manager.save_checkpoint(original)

        # Load checkpoint
        loaded = manager.load_checkpoint("test789")

        assert loaded is not None
        assert loaded.export_id == "test789"
        assert loaded.total_channels == 15
        assert "C123" in loaded.processed_channels

    def test_delete_checkpoint(self, tmp_path):
        """Test checkpoint deletion."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        # Create checkpoint
        manager.create_checkpoint(
            export_id="test_delete",
            total_channels=5
        )

        checkpoint_file = tmp_path / "test_delete.json"
        assert checkpoint_file.exists()

        # Delete
        manager.delete_checkpoint("test_delete")
        assert not checkpoint_file.exists()

    def test_list_checkpoints(self, tmp_path):
        """Test listing all checkpoints."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        # Create multiple checkpoints
        manager.create_checkpoint("exp1", total_channels=5)
        manager.create_checkpoint("exp2", total_channels=10)
        manager.create_checkpoint("exp3", total_channels=15)

        checkpoints = manager.list_checkpoints()

        assert len(checkpoints) == 3
        export_ids = [c.export_id for c in checkpoints]
        assert "exp1" in export_ids
        assert "exp2" in export_ids
        assert "exp3" in export_ids

    def test_find_resumable_export(self, tmp_path):
        """Test finding resumable exports."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        # Create checkpoint
        checkpoint = manager.create_checkpoint(
            export_id="resumable",
            total_channels=10,
            output_format="markdown",
            output_path="/tmp/output"
        )
        checkpoint.state = ExportState.PROCESSING_CHANNELS
        checkpoint.mark_channel_completed("C123", 5)
        manager.save_checkpoint(checkpoint)

        # Find by format and path
        found = manager.find_resumable_export(
            output_format="markdown",
            output_path="/tmp/output"
        )

        assert found is not None
        assert found.export_id == "resumable"
        assert "C123" in found.processed_channels

    def test_find_resumable_export_skip_completed(self, tmp_path):
        """Test that completed exports are not resumable."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        # Create completed checkpoint
        checkpoint = manager.create_checkpoint(
            export_id="completed",
            total_channels=5,
            output_format="html"
        )
        checkpoint.state = ExportState.COMPLETED
        manager.save_checkpoint(checkpoint)

        # Should not find completed export
        found = manager.find_resumable_export(output_format="html")
        assert found is None

    def test_cleanup_old_checkpoints(self, tmp_path):
        """Test cleanup of old checkpoints."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        # Create multiple checkpoints
        for i in range(15):
            manager.create_checkpoint(f"exp{i}", total_channels=5)

        # Keep only 10
        manager.cleanup_old_checkpoints(keep_count=10)

        checkpoints = manager.list_checkpoints()
        assert len(checkpoints) == 10

    def test_resume_after_failure(self, tmp_path):
        """Test resuming after partial failure."""
        manager = CheckpointManager(checkpoint_dir=tmp_path)

        # Simulate interrupted export
        checkpoint = manager.create_checkpoint(
            export_id="interrupted",
            total_channels=10,
            output_format="markdown"
        )

        # Process some channels
        checkpoint.mark_channel_completed("C1", 5)
        checkpoint.mark_channel_completed("C2", 8)
        checkpoint.mark_channel_failed("C3", "Network timeout")
        checkpoint.mark_channel_completed("C4", 3)

        manager.save_checkpoint(checkpoint)

        # Resume - load checkpoint and get pending channels
        loaded = manager.load_checkpoint("interrupted")
        all_channels = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"]
        pending = loaded.get_pending_channels(all_channels)

        # Should have 6 pending (skipping completed C1, C2, C4)
        assert len(pending) == 6
        assert "C1" not in pending  # Already completed
        assert "C3" in pending  # Failed, should retry
        assert "C5" in pending  # Not yet processed

"""
Progress tracking utilities.
"""

from typing import Optional
from tqdm import tqdm


class ProgressTracker:
    """Track progress of long-running operations."""

    def __init__(self, total: int, description: str = "", disable: bool = False):
        """
        Initialize progress tracker.

        Args:
            total: Total number of items
            description: Progress bar description
            disable: Disable progress bar
        """
        self.total = total
        self.description = description
        self.disable = disable
        self.pbar: Optional[tqdm] = None

    def __enter__(self):
        """Enter context manager."""
        if not self.disable:
            self.pbar = tqdm(total=self.total, desc=self.description)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self.pbar:
            self.pbar.close()

    def update(self, n: int = 1) -> None:
        """
        Update progress.

        Args:
            n: Number of items completed
        """
        if self.pbar:
            self.pbar.update(n)

    def set_description(self, desc: str) -> None:
        """
        Update description.

        Args:
            desc: New description
        """
        if self.pbar:
            self.pbar.set_description(desc)

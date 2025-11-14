"""
Parallel processing utilities for improved performance.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
from typing import List, Callable, Any, Optional, Dict
from dataclasses import dataclass
import logging
from tqdm import tqdm

logger = logging.getLogger(__name__)


@dataclass
class ParallelResult:
    """Result from parallel execution."""
    index: int
    success: bool
    result: Any
    error: Optional[Exception] = None


class ParallelProcessor:
    """Process items in parallel with progress tracking."""

    def __init__(
        self,
        max_workers: int = 5,
        use_processes: bool = False,
        show_progress: bool = True
    ):
        """
        Initialize parallel processor.

        Args:
            max_workers: Maximum number of concurrent workers
            use_processes: Use processes instead of threads
            show_progress: Show progress bar
        """
        self.max_workers = max_workers
        self.use_processes = use_processes
        self.show_progress = show_progress

    def map(
        self,
        func: Callable,
        items: List[Any],
        description: str = "Processing"
    ) -> List[ParallelResult]:
        """
        Map function over items in parallel.

        Args:
            func: Function to apply to each item
            items: List of items to process
            description: Progress bar description

        Returns:
            List of ParallelResult objects
        """
        executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        results: List[ParallelResult] = [None] * len(items)

        with executor_class(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(func, item): idx
                for idx, item in enumerate(items)
            }

            # Process results with progress bar
            if self.show_progress:
                pbar = tqdm(total=len(items), desc=description)

            for future in as_completed(future_to_index):
                idx = future_to_index[future]

                try:
                    result = future.result()
                    results[idx] = ParallelResult(
                        index=idx,
                        success=True,
                        result=result
                    )
                except Exception as e:
                    logger.error(f"Error processing item {idx}: {e}")
                    results[idx] = ParallelResult(
                        index=idx,
                        success=False,
                        result=None,
                        error=e
                    )

                if self.show_progress:
                    pbar.update(1)

            if self.show_progress:
                pbar.close()

        return results

    def map_with_context(
        self,
        func: Callable,
        items: List[Any],
        context: Dict[str, Any],
        description: str = "Processing"
    ) -> List[ParallelResult]:
        """
        Map function over items with shared context.

        Args:
            func: Function that takes (item, context)
            items: List of items
            context: Shared context dictionary
            description: Progress description

        Returns:
            List of ParallelResult objects
        """
        def wrapper(item):
            return func(item, context)

        return self.map(wrapper, items, description)


class ChannelProcessor:
    """Process multiple channels in parallel."""

    def __init__(
        self,
        slack_client: Any,
        message_fetcher: Any,
        thread_reconstructor: Any,
        pipeline: Any,
        max_workers: int = 5
    ):
        """
        Initialize channel processor.

        Args:
            slack_client: Slack client instance
            message_fetcher: Message fetcher instance
            thread_reconstructor: Thread reconstructor instance
            pipeline: Content pipeline instance
            max_workers: Maximum parallel workers
        """
        self.slack_client = slack_client
        self.message_fetcher = message_fetcher
        self.thread_reconstructor = thread_reconstructor
        self.pipeline = pipeline
        self.processor = ParallelProcessor(max_workers=max_workers)

    def process_channel(self, channel: Dict[str, Any]) -> Any:
        """
        Process a single channel.

        Args:
            channel: Channel dictionary

        Returns:
            ProcessedChannel or None on error
        """
        try:
            logger.info(f"Processing channel #{channel['name']}")

            # Fetch messages
            messages = self.message_fetcher.fetch_channel_messages(
                channel['id'],
                use_cache=True
            )

            if not messages:
                logger.warning(f"No messages in #{channel['name']}")
                return None

            # Reconstruct threads
            threads = self.thread_reconstructor.reconstruct_threads(
                messages,
                fetch_replies=True,
                message_fetcher=self.message_fetcher
            )

            if not threads:
                logger.warning(f"No threads in #{channel['name']}")
                return None

            # Process with pipeline
            processed = self.pipeline.process_channel(
                threads=threads,
                channel_info=channel,
                use_ai=True
            )

            logger.info(f"Completed #{channel['name']}: {len(threads)} threads")
            return processed

        except Exception as e:
            logger.error(f"Error processing channel {channel['name']}: {e}")
            raise

    def process_channels_parallel(
        self,
        channels: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Process multiple channels in parallel.

        Args:
            channels: List of channel dictionaries

        Returns:
            List of ProcessedChannel objects
        """
        logger.info(f"Processing {len(channels)} channels in parallel with {self.processor.max_workers} workers")

        results = self.processor.map(
            self.process_channel,
            channels,
            description="Processing channels"
        )

        # Filter successful results
        processed_channels = []
        errors = []

        for result in results:
            if result.success and result.result:
                processed_channels.append(result.result)
            elif result.error:
                errors.append(result.error)

        logger.info(
            f"Parallel processing complete: {len(processed_channels)} successful, "
            f"{len(errors)} errors"
        )

        return processed_channels


def process_items_parallel(
    items: List[Any],
    func: Callable,
    max_workers: int = 5,
    description: str = "Processing",
    show_progress: bool = True
) -> List[Any]:
    """
    Convenience function for parallel processing.

    Args:
        items: Items to process
        func: Function to apply
        max_workers: Number of workers
        description: Progress description
        show_progress: Show progress bar

    Returns:
        List of results
    """
    processor = ParallelProcessor(
        max_workers=max_workers,
        show_progress=show_progress
    )

    results = processor.map(func, items, description)

    return [r.result for r in results if r.success]

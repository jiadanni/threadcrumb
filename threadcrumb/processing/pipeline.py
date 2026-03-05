"""
Content processing pipeline for Slack data.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import logging
import json

from ..slack.messages import Thread, Message
from ..ai.processor import AIProcessor, ContentAnalysis

logger = logging.getLogger(__name__)


@dataclass
class ProcessedThread:
    """Processed thread with AI analysis."""
    thread_ts: str
    channel_id: str
    channel_name: str
    title: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    analysis: Optional[ContentAnalysis] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "thread_ts": self.thread_ts,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "title": self.title,
            "messages": self.messages,
            "metadata": self.metadata
        }

        if self.analysis:
            data["analysis"] = {
                "summary": self.analysis.summary,
                "categories": [
                    {"name": c.name, "confidence": c.confidence, "description": c.description}
                    for c in self.analysis.categories
                ],
                "topics": [
                    {"name": t.name, "keywords": t.keywords}
                    for t in self.analysis.topics
                ],
                "qa_pairs": [
                    {"question": qa.question, "answer": qa.answer, "confidence": qa.confidence}
                    for qa in self.analysis.qa_pairs
                ],
                "key_points": self.analysis.key_points,
                "sentiment": self.analysis.sentiment,
                "importance_score": self.analysis.importance_score
            }

        return data


@dataclass
class ProcessedChannel:
    """Processed channel data."""
    channel_id: str
    channel_name: str
    description: str
    threads: List[ProcessedThread] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "description": self.description,
            "threads": [t.to_dict() for t in self.threads],
            "metadata": self.metadata
        }


class ContentPipeline:
    """Main content processing pipeline."""

    def __init__(
        self,
        ai_processor: Optional[AIProcessor] = None,
        min_message_length: int = 10,
        min_thread_messages: int = 2
    ):
        """
        Initialize content pipeline.

        Args:
            ai_processor: AI processor instance
            min_message_length: Minimum message length to process
            min_thread_messages: Minimum messages in thread to process
        """
        self.ai_processor = ai_processor
        self.min_message_length = min_message_length
        self.min_thread_messages = min_thread_messages

    def process_threads(
        self,
        threads: List[Thread],
        channel_info: Dict[str, Any],
        use_ai: bool = True,
        categorize: bool = True,
        extract_topics: bool = True,
        generate_qa: bool = True,
        analyze_sentiment: bool = False
    ) -> List[ProcessedThread]:
        """
        Process threads with AI analysis.

        Args:
            threads: List of Thread objects
            channel_info: Channel information
            use_ai: Whether to use AI processing
            categorize: Perform categorization
            extract_topics: Extract topics
            generate_qa: Generate Q&A pairs
            analyze_sentiment: Analyze sentiment

        Returns:
            List of ProcessedThread objects
        """
        processed_threads = []

        for thread in threads:
            # Filter short threads
            if thread.message_count < self.min_thread_messages:
                continue

            # Filter messages
            filtered_messages = self._filter_messages([thread.parent] + thread.replies)
            if len(filtered_messages) < self.min_thread_messages:
                continue

            # Generate title
            title = self._generate_title(thread.parent.text)

            # Create processed thread
            processed = ProcessedThread(
                thread_ts=thread.thread_ts,
                channel_id=thread.channel_id,
                channel_name=channel_info.get("name", "unknown"),
                title=title,
                messages=[self._message_to_dict(msg) for msg in filtered_messages],
                metadata={
                    "created_at": thread.created_at.isoformat(),
                    "message_count": thread.message_count,
                    "participant_count": len(thread.participants)
                }
            )

            # AI analysis
            if use_ai and self.ai_processor:
                try:
                    thread_dict = thread.to_dict()
                    analysis = self.ai_processor.analyze_thread(
                        thread_dict,
                        categorize=categorize,
                        extract_topics=extract_topics,
                        generate_qa=generate_qa,
                        analyze_sentiment=analyze_sentiment
                    )
                    processed.analysis = analysis
                except Exception as e:
                    logger.error(f"Error analyzing thread {thread.thread_ts}: {e}")

            processed_threads.append(processed)

        logger.info(f"Processed {len(processed_threads)} threads")
        return processed_threads

    def process_channel(
        self,
        threads: List[Thread],
        channel_info: Dict[str, Any],
        use_ai: bool = True
    ) -> ProcessedChannel:
        """
        Process entire channel.

        Args:
            threads: List of Thread objects
            channel_info: Channel information
            use_ai: Whether to use AI processing

        Returns:
            ProcessedChannel object
        """
        processed_threads = self.process_threads(threads, channel_info, use_ai=use_ai)

        return ProcessedChannel(
            channel_id=channel_info["id"],
            channel_name=channel_info.get("name", "unknown"),
            description=channel_info.get("purpose", {}).get("value", ""),
            threads=processed_threads,
            metadata={
                "member_count": channel_info.get("num_members", 0),
                "is_private": channel_info.get("is_private", False),
                "created": channel_info.get("created", 0)
            }
        )

    def organize_by_topic(
        self,
        processed_threads: List[ProcessedThread]
    ) -> Dict[str, List[ProcessedThread]]:
        """
        Organize threads by topic.

        Args:
            processed_threads: List of processed threads

        Returns:
            Dictionary mapping topics to threads
        """
        topic_map: Dict[str, List[ProcessedThread]] = {}

        for thread in processed_threads:
            if not thread.analysis or not thread.analysis.topics:
                # Use "Uncategorized" for threads without topics
                topic_map.setdefault("Uncategorized", []).append(thread)
                continue

            # Add to each topic
            for topic in thread.analysis.topics:
                topic_map.setdefault(topic.name, []).append(thread)

        return topic_map

    def organize_by_category(
        self,
        processed_threads: List[ProcessedThread]
    ) -> Dict[str, List[ProcessedThread]]:
        """
        Organize threads by category.

        Args:
            processed_threads: List of processed threads

        Returns:
            Dictionary mapping categories to threads
        """
        category_map: Dict[str, List[ProcessedThread]] = {}

        for thread in processed_threads:
            if not thread.analysis or not thread.analysis.categories:
                category_map.setdefault("General", []).append(thread)
                continue

            # Use highest confidence category
            top_category = max(thread.analysis.categories, key=lambda c: c.confidence)
            category_map.setdefault(top_category.name, []).append(thread)

        return category_map

    def extract_all_qa_pairs(
        self,
        processed_threads: List[ProcessedThread]
    ) -> List[Dict[str, Any]]:
        """
        Extract all Q&A pairs from processed threads.

        Args:
            processed_threads: List of processed threads

        Returns:
            List of Q&A pair dictionaries
        """
        qa_pairs = []

        for thread in processed_threads:
            if not thread.analysis or not thread.analysis.qa_pairs:
                continue

            for qa in thread.analysis.qa_pairs:
                qa_pairs.append({
                    "question": qa.question,
                    "answer": qa.answer,
                    "confidence": qa.confidence,
                    "source_thread": thread.thread_ts,
                    "source_channel": thread.channel_name
                })

        # Sort by confidence
        qa_pairs.sort(key=lambda x: x["confidence"], reverse=True)

        return qa_pairs

    def _filter_messages(self, messages: List[Message]) -> List[Message]:
        """Filter messages by length and type."""
        filtered = []

        for msg in messages:
            # Skip deleted or hidden messages
            if msg.subtype in ["message_deleted", "channel_join", "channel_leave"]:
                continue

            # Skip very short messages
            if len(msg.text.strip()) < self.min_message_length:
                continue

            filtered.append(msg)

        return filtered

    def _message_to_dict(self, message: Message) -> Dict[str, Any]:
        """Convert Message to dictionary."""
        return {
            "ts": message.ts,
            "user": message.user,
            "text": message.text,
            "timestamp": message.timestamp.isoformat(),
            "reactions": message.reactions,
            "has_files": len(message.files) > 0
        }

    def _generate_title(self, text: str, max_length: int = 80) -> str:
        """Generate title from message text."""
        # Clean up text
        text = text.strip()

        # Remove URLs
        import re
        text = re.sub(r'http[s]?://\S+', '', text)

        # Take first sentence or line
        sentences = text.split('.')
        if sentences:
            title = sentences[0].strip()
        else:
            title = text

        # Truncate
        if len(title) > max_length:
            title = title[:max_length - 3] + "..."

        return title or "Untitled Thread"

    def save_processed_data(
        self,
        processed_channels: List[ProcessedChannel],
        output_path: Path
    ) -> None:
        """
        Save processed data to JSON.

        Args:
            processed_channels: List of processed channels
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "channels": [ch.to_dict() for ch in processed_channels],
            "metadata": {
                "channel_count": len(processed_channels),
                "total_threads": sum(len(ch.threads) for ch in processed_channels)
            }
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved processed data to {output_path}")

"""
AI-powered content processing for Slack messages.
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import logging

from .bedrock import BedrockClient, AIResponse

logger = logging.getLogger(__name__)


@dataclass
class Category:
    """Content category."""
    name: str
    confidence: float
    description: str = ""


@dataclass
class Topic:
    """Extracted topic."""
    name: str
    keywords: List[str] = field(default_factory=list)
    frequency: int = 0


@dataclass
class QAPair:
    """Question-answer pair."""
    question: str
    answer: str
    source_messages: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class ContentAnalysis:
    """Complete content analysis result."""
    summary: str
    categories: List[Category] = field(default_factory=list)
    topics: List[Topic] = field(default_factory=list)
    qa_pairs: List[QAPair] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)
    sentiment: Optional[str] = None
    importance_score: float = 0.0


class AIProcessor:
    """Process Slack content using AI."""

    def __init__(
        self,
        bedrock_client: BedrockClient,
        fallback_enabled: bool = True
    ):
        """
        Initialize AI processor.

        Args:
            bedrock_client: Bedrock client instance
            fallback_enabled: Use fallback when AI unavailable
        """
        self.client = bedrock_client
        self.fallback_enabled = fallback_enabled

    def analyze_thread(
        self,
        thread_data: Dict[str, Any],
        categorize: bool = True,
        extract_topics: bool = True,
        generate_qa: bool = True,
        analyze_sentiment: bool = False
    ) -> ContentAnalysis:
        """
        Perform complete analysis of a thread.

        Args:
            thread_data: Thread data dictionary
            categorize: Perform categorization
            extract_topics: Extract topics
            generate_qa: Generate Q&A pairs
            analyze_sentiment: Analyze sentiment

        Returns:
            ContentAnalysis object
        """
        # Format thread for AI
        thread_text = self._format_thread(thread_data)

        # Generate summary
        summary = self.summarize_thread(thread_text)

        analysis = ContentAnalysis(summary=summary)

        # Categorize
        if categorize:
            analysis.categories = self.categorize_content(thread_text)

        # Extract topics
        if extract_topics:
            analysis.topics = self.extract_topics(thread_text)

        # Generate Q&A
        if generate_qa:
            analysis.qa_pairs = self.generate_qa_pairs(thread_text)

        # Sentiment analysis
        if analyze_sentiment:
            analysis.sentiment = self.analyze_sentiment(thread_text)

        # Importance scoring
        analysis.importance_score = self.score_importance(thread_data)

        # Extract key points
        analysis.key_points = self.extract_key_points(thread_text)

        return analysis

    def summarize_thread(self, thread_text: str, max_length: int = 500) -> str:
        """
        Generate summary of a thread.

        Args:
            thread_text: Thread content
            max_length: Maximum summary length

        Returns:
            Summary text
        """
        prompt = f"""Analyze this Slack conversation thread and provide a concise summary.

Thread:
{thread_text}

Provide a clear, informative summary that captures:
1. Main topic/purpose of the discussion
2. Key decisions or conclusions
3. Important action items or outcomes

Summary:"""

        try:
            response = self.client.invoke(prompt, max_tokens=max_length)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            if self.fallback_enabled:
                return self._fallback_summarize(thread_text)
            raise

    def categorize_content(
        self,
        content: str,
        custom_categories: Optional[List[str]] = None
    ) -> List[Category]:
        """
        Categorize content into topics.

        Args:
            content: Content to categorize
            custom_categories: Optional custom category list

        Returns:
            List of Category objects
        """
        default_categories = [
            "Technical Discussion",
            "Bug Report",
            "Feature Request",
            "Question/Help",
            "Announcement",
            "Decision",
            "Brainstorming",
            "Documentation",
            "Meeting Notes",
            "General Discussion"
        ]

        categories = custom_categories or default_categories
        categories_str = "\n".join(f"- {c}" for c in categories)

        prompt = f"""Categorize this Slack conversation into one or more of these categories:

{categories_str}

Content:
{content}

Provide your response as JSON with this format:
{{
  "categories": [
    {{"name": "category name", "confidence": 0.95, "description": "why this category applies"}},
    ...
  ]
}}

Response:"""

        try:
            response = self.client.invoke(prompt, max_tokens=500)
            data = self._parse_json_response(response.content)

            if "categories" in data:
                return [
                    Category(
                        name=cat["name"],
                        confidence=cat.get("confidence", 1.0),
                        description=cat.get("description", "")
                    )
                    for cat in data["categories"]
                ]
            return []

        except Exception as e:
            logger.error(f"Error categorizing content: {e}")
            if self.fallback_enabled:
                return [Category(name="General Discussion", confidence=0.5, description="")]
            return []

    def extract_topics(self, content: str, max_topics: int = 10) -> List[Topic]:
        """
        Extract main topics from content.

        Args:
            content: Content to analyze
            max_topics: Maximum number of topics

        Returns:
            List of Topic objects
        """
        prompt = f"""Extract the main topics discussed in this Slack conversation.

Content:
{content}

Identify up to {max_topics} key topics with relevant keywords.

Provide your response as JSON:
{{
  "topics": [
    {{"name": "topic name", "keywords": ["keyword1", "keyword2"]}},
    ...
  ]
}}

Response:"""

        try:
            response = self.client.invoke(prompt, max_tokens=800)
            data = self._parse_json_response(response.content)

            if "topics" in data:
                return [
                    Topic(
                        name=topic["name"],
                        keywords=topic.get("keywords", [])
                    )
                    for topic in data["topics"]
                ]
            return []

        except Exception as e:
            logger.error(f"Error extracting topics: {e}")
            return []

    def generate_qa_pairs(self, content: str, max_pairs: int = 5) -> List[QAPair]:
        """
        Generate Q&A pairs from content.

        Args:
            content: Content to analyze
            max_pairs: Maximum number of Q&A pairs

        Returns:
            List of QAPair objects
        """
        prompt = f"""Extract question-answer pairs from this Slack conversation.
Look for explicit questions and their answers, or implicit Q&A patterns.

Content:
{content}

Generate up to {max_pairs} clear Q&A pairs.

Provide your response as JSON:
{{
  "qa_pairs": [
    {{"question": "question text", "answer": "answer text", "confidence": 0.9}},
    ...
  ]
}}

Response:"""

        try:
            response = self.client.invoke(prompt, max_tokens=1500)
            data = self._parse_json_response(response.content)

            if "qa_pairs" in data:
                return [
                    QAPair(
                        question=qa["question"],
                        answer=qa["answer"],
                        confidence=qa.get("confidence", 1.0)
                    )
                    for qa in data["qa_pairs"]
                ]
            return []

        except Exception as e:
            logger.error(f"Error generating Q&A pairs: {e}")
            return []

    def extract_key_points(self, content: str, max_points: int = 5) -> List[str]:
        """
        Extract key points from content.

        Args:
            content: Content to analyze
            max_points: Maximum number of points

        Returns:
            List of key points
        """
        prompt = f"""Extract the {max_points} most important key points from this conversation.

Content:
{content}

Provide concise bullet points.

Provide your response as JSON:
{{
  "key_points": ["point 1", "point 2", ...]
}}

Response:"""

        try:
            response = self.client.invoke(prompt, max_tokens=500)
            data = self._parse_json_response(response.content)
            return data.get("key_points", [])

        except Exception as e:
            logger.error(f"Error extracting key points: {e}")
            return []

    def analyze_sentiment(self, content: str) -> str:
        """
        Analyze sentiment of content.

        Args:
            content: Content to analyze

        Returns:
            Sentiment (positive, negative, neutral, mixed)
        """
        prompt = f"""Analyze the overall sentiment of this Slack conversation.

Content:
{content}

Classify as: positive, negative, neutral, or mixed

Response (one word):"""

        try:
            response = self.client.invoke(prompt, max_tokens=10)
            sentiment = response.content.strip().lower()

            if sentiment in ["positive", "negative", "neutral", "mixed"]:
                return sentiment
            return "neutral"

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return "neutral"

    def score_importance(self, thread_data: Dict[str, Any]) -> float:
        """
        Score importance of a thread.

        Args:
            thread_data: Thread data

        Returns:
            Importance score (0.0 to 1.0)
        """
        # Simple heuristic scoring
        score = 0.0

        # Message count
        message_count = thread_data.get("message_count", 0)
        score += min(message_count / 20, 0.3)

        # Participant count
        participants = thread_data.get("participants", [])
        score += min(len(participants) / 10, 0.2)

        # Reactions (if available)
        parent = thread_data.get("parent", {})
        reactions = parent.get("reactions", [])
        if reactions:
            reaction_count = sum(r.get("count", 0) for r in reactions)
            score += min(reaction_count / 20, 0.2)

        # Has files/attachments
        if parent.get("files") or parent.get("attachments"):
            score += 0.1

        # Thread age (newer = more important)
        score += 0.2  # Default for age

        return min(score, 1.0)

    def _format_thread(self, thread_data: Dict[str, Any]) -> str:
        """Format thread data for AI processing."""
        lines = []

        # Parent message
        parent = thread_data.get("parent", {})
        user = parent.get("user", "Unknown")
        text = parent.get("text", "")
        lines.append(f"[{user}]: {text}")

        # Replies
        replies = thread_data.get("replies", [])
        for reply in replies[:50]:  # Limit to prevent token overflow
            user = reply.get("user", "Unknown")
            text = reply.get("text", "")
            lines.append(f"[{user}]: {text}")

        return "\n".join(lines)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from AI response."""
        # Try to extract JSON from response
        response = response.strip()

        # Find JSON block
        start = response.find('{')
        end = response.rfind('}') + 1

        if start >= 0 and end > start:
            json_str = response[start:end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from response")
                return {}

        return {}

    def _fallback_summarize(self, text: str, max_words: int = 100) -> str:
        """Fallback summarization without AI."""
        words = text.split()[:max_words]
        return " ".join(words) + "..."

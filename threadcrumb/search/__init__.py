"""
Search functionality with full-text indexing.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result item."""
    thread_id: str
    thread_title: str
    channel_name: str
    score: float
    excerpt: str
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class SearchIndex:
    """Simple search index for ThreadCrumb content."""

    def __init__(self, index_file: Path = None):
        """
        Initialize search index.

        Args:
            index_file: Path to index file
        """
        if index_file is None:
            index_file = Path.home() / ".threadcrumb" / "search_index.json"

        self.index_file = Path(index_file)
        self.index_file.parent.mkdir(parents=True, exist_ok=True)

        self.documents: List[Dict[str, Any]] = []
        self._load_index()

    def _load_index(self) -> None:
        """Load index from file."""
        if not self.index_file.exists():
            return

        try:
            with open(self.index_file, 'r') as f:
                data = json.load(f)
                self.documents = data.get('documents', [])

            logger.info(f"Loaded {len(self.documents)} documents from search index")

        except Exception as e:
            logger.error(f"Failed to load search index: {e}")
            self.documents = []

    def _save_index(self) -> None:
        """Save index to file."""
        try:
            data = {
                'documents': self.documents,
                'doc_count': len(self.documents)
            }

            with open(self.index_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self.documents)} documents to search index")

        except Exception as e:
            logger.error(f"Failed to save search index: {e}")

    def add_thread(
        self,
        thread_id: str,
        thread_title: str,
        channel_name: str,
        content: str,
        topics: List[str] = None,
        categories: List[str] = None,
        url: Optional[str] = None
    ) -> None:
        """
        Add thread to search index.

        Args:
            thread_id: Thread timestamp/ID
            thread_title: Thread title
            channel_name: Channel name
            content: Full thread content
            topics: List of topics
            categories: List of categories
            url: Optional URL to thread
        """
        doc = {
            'id': thread_id,
            'title': thread_title,
            'channel': channel_name,
            'content': content.lower(),  # For case-insensitive search
            'topics': topics or [],
            'categories': categories or [],
            'url': url
        }

        self.documents.append(doc)

    def build_from_channels(
        self,
        processed_channels: List[Any],
        base_url: Optional[str] = None
    ) -> None:
        """
        Build index from processed channels.

        Args:
            processed_channels: List of ProcessedChannel objects
            base_url: Optional base URL for generating links
        """
        self.documents = []

        for channel in processed_channels:
            for thread in channel.threads:
                # Extract content
                content_parts = [thread.title]

                if thread.analysis and thread.analysis.summary:
                    content_parts.append(thread.analysis.summary)

                for msg in thread.messages:
                    content_parts.append(msg.get('text', ''))

                content = ' '.join(content_parts)

                # Extract topics and categories
                topics = []
                categories = []

                if thread.analysis:
                    topics = [t.name for t in thread.analysis.topics]
                    categories = [c.name for c in thread.analysis.categories]

                # Generate URL if base provided
                url = None
                if base_url:
                    url = f"{base_url}/{channel.channel_name}/{thread.thread_ts}.html"

                self.add_thread(
                    thread_id=thread.thread_ts,
                    thread_title=thread.title,
                    channel_name=channel.channel_name,
                    content=content,
                    topics=topics,
                    categories=categories,
                    url=url
                )

        self._save_index()
        logger.info(f"Built search index with {len(self.documents)} threads")

    def search(
        self,
        query: str,
        channel: Optional[str] = None,
        topic: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """
        Search the index.

        Args:
            query: Search query
            channel: Filter by channel
            topic: Filter by topic
            category: Filter by category
            limit: Maximum results

        Returns:
            List of SearchResult objects
        """
        query_lower = query.lower()
        results = []

        for doc in self.documents:
            # Apply filters
            if channel and doc['channel'] != channel:
                continue

            if topic and topic not in doc['topics']:
                continue

            if category and category not in doc['categories']:
                continue

            # Simple scoring (count occurrences)
            score = 0.0

            # Title match (higher weight)
            if query_lower in doc['title'].lower():
                score += 10.0 * doc['title'].lower().count(query_lower)

            # Content match
            score += doc['content'].count(query_lower)

            # Topic/category match
            for t in doc['topics']:
                if query_lower in t.lower():
                    score += 5.0

            for c in doc['categories']:
                if query_lower in c.lower():
                    score += 5.0

            if score > 0:
                # Generate excerpt
                excerpt = self._generate_excerpt(doc['content'], query_lower)

                results.append(SearchResult(
                    thread_id=doc['id'],
                    thread_title=doc['title'],
                    channel_name=doc['channel'],
                    score=score,
                    excerpt=excerpt,
                    url=doc.get('url')
                ))

        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:limit]

    def _generate_excerpt(self, content: str, query: str, context_chars: int = 100) -> str:
        """
        Generate excerpt around query match.

        Args:
            content: Full content
            query: Search query
            context_chars: Characters of context

        Returns:
            Excerpt string
        """
        idx = content.find(query)
        if idx == -1:
            return content[:context_chars] + "..."

        start = max(0, idx - context_chars // 2)
        end = min(len(content), idx + len(query) + context_chars // 2)

        excerpt = content[start:end]

        if start > 0:
            excerpt = "..." + excerpt
        if end < len(content):
            excerpt = excerpt + "..."

        return excerpt

    def get_stats(self) -> Dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Statistics dictionary
        """
        channels = set(doc['channel'] for doc in self.documents)
        topics = set()
        categories = set()

        for doc in self.documents:
            topics.update(doc['topics'])
            categories.update(doc['categories'])

        return {
            'total_documents': len(self.documents),
            'channels': len(channels),
            'topics': len(topics),
            'categories': len(categories)
        }

    def clear(self) -> None:
        """Clear the search index."""
        self.documents = []
        self._save_index()
        logger.info("Cleared search index")


# Whoosh integration (optional, more powerful)
try:
    from whoosh.index import create_in, open_dir, exists_in
    from whoosh.fields import Schema, TEXT, ID, KEYWORD
    from whoosh.qparser import QueryParser, MultifieldParser
    from whoosh import scoring

    WHOOSH_AVAILABLE = True

    class WhooshSearchIndex:
        """Advanced search using Whoosh library."""

        def __init__(self, index_dir: Path = None):
            """
            Initialize Whoosh search index.

            Args:
                index_dir: Directory for index files
            """
            if index_dir is None:
                index_dir = Path.home() / ".threadcrumb" / "whoosh_index"

            self.index_dir = Path(index_dir)
            self.index_dir.mkdir(parents=True, exist_ok=True)

            # Define schema
            self.schema = Schema(
                id=ID(stored=True, unique=True),
                title=TEXT(stored=True, field_boost=2.0),
                channel=TEXT(stored=True),
                content=TEXT,
                topics=KEYWORD(stored=True, commas=True),
                categories=KEYWORD(stored=True, commas=True),
                url=ID(stored=True)
            )

            # Create or open index
            if exists_in(str(self.index_dir)):
                self.ix = open_dir(str(self.index_dir))
            else:
                self.ix = create_in(str(self.index_dir), self.schema)

        def build_from_channels(self, processed_channels: List[Any], base_url: Optional[str] = None):
            """Build index from processed channels."""
            writer = self.ix.writer()

            for channel in processed_channels:
                for thread in channel.threads:
                    content_parts = [thread.title]

                    if thread.analysis and thread.analysis.summary:
                        content_parts.append(thread.analysis.summary)

                    for msg in thread.messages:
                        content_parts.append(msg.get('text', ''))

                    content = ' '.join(content_parts)

                    topics = categories = ""
                    if thread.analysis:
                        topics = ','.join(t.name for t in thread.analysis.topics)
                        categories = ','.join(c.name for c in thread.analysis.categories)

                    url = f"{base_url}/{channel.channel_name}/{thread.thread_ts}.html" if base_url else ""

                    writer.add_document(
                        id=thread.thread_ts,
                        title=thread.title,
                        channel=channel.channel_name,
                        content=content,
                        topics=topics,
                        categories=categories,
                        url=url
                    )

            writer.commit()
            logger.info("Built Whoosh search index")

        def search(self, query: str, limit: int = 10) -> List[SearchResult]:
            """Search using Whoosh."""
            results = []

            with self.ix.searcher(weighting=scoring.BM25F()) as searcher:
                parser = MultifieldParser(
                    ["title", "content", "topics", "categories"],
                    schema=self.schema
                )

                q = parser.parse(query)
                search_results = searcher.search(q, limit=limit)

                for hit in search_results:
                    results.append(SearchResult(
                        thread_id=hit['id'],
                        thread_title=hit['title'],
                        channel_name=hit['channel'],
                        score=hit.score,
                        excerpt=hit.highlights('content', text=hit['content'][:200]),
                        url=hit.get('url')
                    ))

            return results

except ImportError:
    WHOOSH_AVAILABLE = False
    WhooshSearchIndex = None

"""
Confluence formatter - export processed content directly to Confluence.
"""

from typing import List, Dict, Optional
import logging

from ..processing.pipeline import ProcessedChannel, ProcessedThread
from .client import ConfluenceClient
from .storage_format import StorageFormatConverter, ConfluencePageBuilder

logger = logging.getLogger(__name__)


class ConfluenceFormatter:
    """Format and export processed content to Confluence."""

    def __init__(
        self,
        client: ConfluenceClient,
        root_page_title: str = "Slack Wiki",
        create_index: bool = True,
        add_labels: bool = True,
        dry_run: bool = False
    ):
        """
        Initialize Confluence formatter.

        Args:
            client: Confluence client instance
            root_page_title: Title for root wiki page
            create_index: Create index pages
            add_labels: Add labels to pages
            dry_run: Don't actually create pages (for testing)
        """
        self.client = client
        self.root_page_title = root_page_title
        self.create_index = create_index
        self.add_labels = add_labels
        self.dry_run = dry_run

        self.converter = StorageFormatConverter()
        self.page_builder = ConfluencePageBuilder(self.converter)

        # Track created pages
        self.page_map: Dict[str, str] = {}  # title -> page_id

    def format_channels(
        self,
        channels: List[ProcessedChannel],
        parent_page_id: Optional[str] = None,
        slack_token: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Format and upload all channels to Confluence.

        Args:
            channels: List of processed channels
            parent_page_id: Optional parent page ID

        Returns:
            Dictionary mapping page titles to page IDs
        """
        logger.info(f"Exporting {len(channels)} channels to Confluence...")

        # Create root page
        if self.create_index:
            root_page_id = self._create_root_page(channels, parent_page_id)
        else:
            root_page_id = parent_page_id

        # Create channel pages
        for channel in channels:
            try:
                self._create_channel_pages(channel, root_page_id)
            except Exception as e:
                logger.error(f"Error creating pages for channel {channel.channel_name}: {e}")

        # Create index pages
        if self.create_index:
            self._create_category_index(channels, root_page_id)
            self._create_topic_index(channels, root_page_id)
            self._create_faq(channels, root_page_id)

        logger.info(f"✓ Created {len(self.page_map)} pages in Confluence")
        return self.page_map

    def _create_root_page(
        self,
        channels: List[ProcessedChannel],
        parent_id: Optional[str]
    ) -> str:
        """Create root wiki page."""
        total_threads = sum(len(ch.threads) for ch in channels)

        stats = {
            "Channels": len(channels),
            "Threads": total_threads
        }

        child_pages = [
            f"{ch.channel_name} Channel" for ch in channels
        ]
        child_pages.extend(["Categories", "Topics", "FAQ"])

        content = self.page_builder.build_index_page(
            title=self.root_page_title,
            summary="This wiki contains organized content from Slack channels, processed and analyzed with AI.",
            stats=stats,
            child_pages=child_pages
        )

        if self.dry_run:
            logger.info(f"[DRY RUN] Would create root page: {self.root_page_title}")
            return "dry-run-root-id"

        page = self.client.create_or_update_page(
            title=self.root_page_title,
            body=content,
            parent_id=parent_id,
            labels=["slack-wiki", "generated"] if self.add_labels else None
        )

        self.page_map[self.root_page_title] = page['id']
        logger.info(f"Created root page: {self.root_page_title}")

        return page['id']

    def _create_channel_pages(
        self,
        channel: ProcessedChannel,
        parent_id: str
    ) -> None:
        """Create pages for a channel and its threads."""
        # Create channel overview page
        channel_page_title = f"{channel.channel_name} Channel"

        channel_content = self._build_channel_overview(channel)

        if self.dry_run:
            logger.info(f"[DRY RUN] Would create channel page: {channel_page_title}")
            channel_page_id = f"dry-run-{channel.channel_id}"
        else:
            channel_page = self.client.create_or_update_page(
                title=channel_page_title,
                body=channel_content,
                parent_id=parent_id,
                labels=[f"channel-{channel.channel_name}", "slack-channel"] if self.add_labels else None
            )
            channel_page_id = channel_page['id']
            self.page_map[channel_page_title] = channel_page_id

        logger.info(f"Created channel page: {channel_page_title}")

        # Create thread pages (pass slack_token to parent method)
        for thread in channel.threads:
            slack_token = getattr(self, '_slack_token', None)
            self._create_thread_page(thread, channel_page_id, slack_token)

    def _build_channel_overview(self, channel: ProcessedChannel) -> str:
        """Build channel overview page content."""
        content = f'<h1>#{self.converter.escape_special_chars(channel.channel_name)}</h1>'

        if channel.description:
            content += f'<p>{self.converter.escape_special_chars(channel.description)}</p>'

        # Metadata
        metadata = channel.metadata
        meta_content = f'''
Member Count: {metadata.get('member_count', 0)}<br/>
Private: {metadata.get('is_private', False)}<br/>
Threads: {len(channel.threads)}
'''
        content += self.converter.create_info_panel("Channel Information", meta_content, "info")

        # Table of contents
        content += '<h2>Threads</h2>'
        content += self.converter.create_children_display()

        return content

    def _create_thread_page(
        self,
        thread: ProcessedThread,
        parent_id: str,
        slack_token: Optional[str] = None
    ) -> None:
        """Create page for a thread."""
        # Sanitize title for Confluence (max 255 chars)
        title = thread.title[:250]

        content = self.page_builder.build_thread_page(thread.to_dict())

        if self.dry_run:
            logger.info(f"[DRY RUN] Would create thread page: {title}")
            return

        # Generate labels
        labels = []
        if self.add_labels:
            labels.append("slack-thread")

            if thread.analysis and thread.analysis.categories:
                for cat in thread.analysis.categories[:3]:  # Max 3 category labels
                    label = cat.name.lower().replace(' ', '-')
                    labels.append(label)

        page = self.client.create_or_update_page(
            title=title,
            body=content,
            parent_id=parent_id,
            labels=labels if labels else None
        )

        page_id = page['id']
        self.page_map[title] = page_id
        logger.debug(f"Created thread page: {title}")

        # Upload attachments if available
        if slack_token:
            self._upload_attachments(thread, page_id, slack_token)

    def _upload_attachments(
        self,
        thread: ProcessedThread,
        page_id: str,
        slack_token: str
    ) -> None:
        """
        Upload Slack attachments to Confluence page.

        Args:
            thread: Processed thread
            page_id: Confluence page ID
            slack_token: Slack access token
        """
        import tempfile
        import requests

        for msg in thread.messages:
            files = msg.get('files', [])
            for file_info in files:
                try:
                    # Download from Slack
                    file_url = file_info.get('url_private_download') or file_info.get('url_private')
                    if not file_url:
                        continue

                    file_name = file_info.get('name', 'attachment')

                    logger.debug(f"Downloading attachment: {file_name}")

                    headers = {"Authorization": f"Bearer {slack_token}"}
                    response = requests.get(file_url, headers=headers)
                    response.raise_for_status()

                    # Save temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}") as tmp:
                        tmp.write(response.content)
                        tmp_path = tmp.name

                    # Upload to Confluence
                    logger.debug(f"Uploading to Confluence: {file_name}")
                    self.client.add_attachment(
                        page_id=page_id,
                        file_path=tmp_path,
                        comment="From Slack message"
                    )

                    # Clean up
                    import os
                    os.unlink(tmp_path)

                    logger.info(f"Uploaded attachment: {file_name}")

                except Exception as e:
                    logger.warning(f"Failed to upload attachment {file_name}: {e}")

    def _create_category_index(
        self,
        channels: List[ProcessedChannel],
        parent_id: str
    ) -> None:
        """Create category index page."""
        categories: Dict[str, List[str]] = {}

        # Collect threads by category
        for channel in channels:
            for thread in channel.threads:
                if thread.analysis and thread.analysis.categories:
                    for cat in thread.analysis.categories:
                        thread_title = thread.title[:250]
                        categories.setdefault(cat.name, []).append(thread_title)
                else:
                    categories.setdefault("Uncategorized", []).append(thread.title[:250])

        content = self.page_builder.build_category_index(categories)

        if self.dry_run:
            logger.info("[DRY RUN] Would create Categories page")
            return

        page = self.client.create_or_update_page(
            title="Categories",
            body=content,
            parent_id=parent_id,
            labels=["slack-wiki", "index"] if self.add_labels else None
        )

        self.page_map["Categories"] = page['id']
        logger.info("Created Categories index page")

    def _create_topic_index(
        self,
        channels: List[ProcessedChannel],
        parent_id: str
    ) -> None:
        """Create topic index page."""
        topics: Dict[str, List[str]] = {}

        # Collect threads by topic
        for channel in channels:
            for thread in channel.threads:
                if thread.analysis and thread.analysis.topics:
                    for topic in thread.analysis.topics:
                        thread_title = thread.title[:250]
                        topics.setdefault(topic.name, []).append(thread_title)

        content = self.page_builder.build_category_index(topics)  # Reuse category builder
        content = content.replace('<h1>Categories</h1>', '<h1>Topics</h1>')

        if self.dry_run:
            logger.info("[DRY RUN] Would create Topics page")
            return

        page = self.client.create_or_update_page(
            title="Topics",
            body=content,
            parent_id=parent_id,
            labels=["slack-wiki", "index"] if self.add_labels else None
        )

        self.page_map["Topics"] = page['id']
        logger.info("Created Topics index page")

    def _create_faq(
        self,
        channels: List[ProcessedChannel],
        parent_id: str
    ) -> None:
        """Create FAQ page."""
        qa_pairs = []

        # Collect all Q&A pairs
        for channel in channels:
            for thread in channel.threads:
                if thread.analysis and thread.analysis.qa_pairs:
                    for qa in thread.analysis.qa_pairs:
                        qa_pairs.append({
                            'question': qa.question,
                            'answer': qa.answer,
                            'confidence': qa.confidence,
                            'source_thread': thread.title[:250]
                        })

        # Sort by confidence
        qa_pairs.sort(key=lambda x: x['confidence'], reverse=True)

        content = self.page_builder.build_faq_page(qa_pairs)

        if self.dry_run:
            logger.info("[DRY RUN] Would create FAQ page")
            return

        page = self.client.create_or_update_page(
            title="FAQ",
            body=content,
            parent_id=parent_id,
            labels=["slack-wiki", "faq", "questions"] if self.add_labels else None
        )

        self.page_map["FAQ"] = page['id']
        logger.info("Created FAQ page")

    def export_with_structure(
        self,
        channels: List[ProcessedChannel],
        structure: str = "flat",
        parent_page_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Export with different page structures.

        Args:
            channels: List of processed channels
            structure: Page structure (flat, hierarchical, by-category)
            parent_page_id: Optional parent page ID

        Returns:
            Dictionary mapping page titles to page IDs
        """
        if structure == "flat":
            return self.format_channels(channels, parent_page_id)

        elif structure == "hierarchical":
            # Create deeper hierarchy: Root > Channels > Threads
            return self.format_channels(channels, parent_page_id)

        elif structure == "by-category":
            # Organize by categories instead of channels
            return self._export_by_category(channels, parent_page_id)

        else:
            raise ValueError(f"Unknown structure: {structure}")

    def _export_by_category(
        self,
        channels: List[ProcessedChannel],
        parent_id: Optional[str]
    ) -> Dict[str, str]:
        """Export organized by category."""
        # Create root
        root_id = self._create_root_page(channels, parent_id)

        # Collect all threads by category
        by_category: Dict[str, List[ProcessedThread]] = {}

        for channel in channels:
            for thread in channel.threads:
                if thread.analysis and thread.analysis.categories:
                    cat_name = thread.analysis.categories[0].name
                else:
                    cat_name = "General"

                by_category.setdefault(cat_name, []).append(thread)

        # Create category pages, then thread pages under each
        for category, threads in by_category.items():
            cat_content = f'<h1>{self.converter.escape_special_chars(category)}</h1>'
            cat_content += f'<p>{len(threads)} threads in this category</p>'
            cat_content += self.converter.create_children_display()

            if not self.dry_run:
                cat_page = self.client.create_or_update_page(
                    title=f"Category: {category}",
                    body=cat_content,
                    parent_id=root_id
                )
                cat_page_id = cat_page['id']
            else:
                cat_page_id = f"dry-run-cat-{category}"

            # Create threads under category
            for thread in threads:
                self._create_thread_page(thread, cat_page_id)

        return self.page_map


def export_to_confluence(
    channels: List[ProcessedChannel],
    confluence_url: str,
    username: str,
    api_token: str,
    space_key: str,
    root_page_title: str = "Slack Wiki",
    parent_page_id: Optional[str] = None,
    structure: str = "flat",
    dry_run: bool = False,
    use_cloud: bool = True
) -> Dict[str, str]:
    """
    Convenience function to export to Confluence.

    Args:
        channels: List of processed channels
        confluence_url: Confluence base URL
        username: Confluence username
        api_token: API token
        space_key: Space key
        root_page_title: Root page title
        parent_page_id: Optional parent page ID
        structure: Page structure
        dry_run: Don't actually create pages
        use_cloud: True for Cloud, False for Server

    Returns:
        Dictionary mapping page titles to page IDs
    """
    client = ConfluenceClient(
        base_url=confluence_url,
        username=username,
        api_token=api_token,
        space_key=space_key,
        use_cloud=use_cloud
    )

    # Test connection
    if not dry_run and not client.test_connection():
        raise ConnectionError("Failed to connect to Confluence")

    formatter = ConfluenceFormatter(
        client=client,
        root_page_title=root_page_title,
        create_index=True,
        add_labels=True,
        dry_run=dry_run
    )

    return formatter.export_with_structure(
        channels=channels,
        structure=structure,
        parent_page_id=parent_page_id
    )

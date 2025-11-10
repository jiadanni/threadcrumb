"""
Confluence Storage Format converter.

Converts Markdown and structured content to Confluence Storage Format (XHTML-based).
"""

import re
from typing import List, Dict, Any
from html import escape
import logging

logger = logging.getLogger(__name__)


class StorageFormatConverter:
    """Convert content to Confluence Storage Format."""

    @staticmethod
    def markdown_to_storage(markdown: str) -> str:
        """
        Convert Markdown to Confluence Storage Format.

        Args:
            markdown: Markdown text

        Returns:
            Confluence Storage Format (XHTML)
        """
        # Start with escaped HTML
        html = markdown

        # Headers
        html = re.sub(r'^######\s+(.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
        html = re.sub(r'^#####\s+(.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
        html = re.sub(r'^####\s+(.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Bold
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'__(.+?)__', r'<strong>\1</strong>', html)

        # Italic
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        html = re.sub(r'_(.+?)_', r'<em>\1</em>', html)

        # Code inline
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

        # Links
        html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<ac:link><ri:url ri:value="\2"/><ac:plain-text-link-body><![CDATA[\1]]></ac:plain-text-link-body></ac:link>', html)

        # Unordered lists
        html = re.sub(r'^\s*[-*+]\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*?</li>\n?)+', r'<ul>\g<0></ul>', html, flags=re.DOTALL)

        # Ordered lists
        html = re.sub(r'^\s*\d+\.\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

        # Paragraphs
        html = re.sub(r'\n\n+', '</p><p>', html)
        html = f'<p>{html}</p>'

        # Clean up
        html = html.replace('<p></p>', '')
        html = html.replace('<p><h', '<h').replace('</h1></p>', '</h1>')
        html = html.replace('</h2></p>', '</h2>').replace('</h3></p>', '</h3>')
        html = html.replace('</h4></p>', '</h4>').replace('</h5></p>', '</h5>')
        html = html.replace('</h6></p>', '</h6>')
        html = html.replace('<p><ul>', '<ul>').replace('</ul></p>', '</ul>')
        html = html.replace('<p><ol>', '<ol>').replace('</ol></p>', '</ol>')

        return html

    @staticmethod
    def create_info_panel(title: str, content: str, panel_type: str = "info") -> str:
        """
        Create Confluence info panel.

        Args:
            title: Panel title
            content: Panel content
            panel_type: Panel type (info, note, warning, tip)

        Returns:
            Confluence panel markup
        """
        return f'''
<ac:structured-macro ac:name="{panel_type}">
    <ac:parameter ac:name="title">{escape(title)}</ac:parameter>
    <ac:rich-text-body>
        <p>{escape(content)}</p>
    </ac:rich-text-body>
</ac:structured-macro>
'''

    @staticmethod
    def create_code_block(code: str, language: str = "none") -> str:
        """
        Create Confluence code block.

        Args:
            code: Code content
            language: Programming language

        Returns:
            Confluence code block markup
        """
        return f'''
<ac:structured-macro ac:name="code">
    <ac:parameter ac:name="language">{language}</ac:parameter>
    <ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>
</ac:structured-macro>
'''

    @staticmethod
    def create_expand(title: str, content: str) -> str:
        """
        Create Confluence expand macro.

        Args:
            title: Expand title
            content: Content to hide

        Returns:
            Confluence expand markup
        """
        return f'''
<ac:structured-macro ac:name="expand">
    <ac:parameter ac:name="title">{escape(title)}</ac:parameter>
    <ac:rich-text-body>
        {content}
    </ac:rich-text-body>
</ac:structured-macro>
'''

    @staticmethod
    def create_table(headers: List[str], rows: List[List[str]]) -> str:
        """
        Create Confluence table.

        Args:
            headers: Table headers
            rows: Table rows

        Returns:
            Confluence table markup
        """
        table = '<table><thead><tr>'

        for header in headers:
            table += f'<th>{escape(header)}</th>'

        table += '</tr></thead><tbody>'

        for row in rows:
            table += '<tr>'
            for cell in row:
                table += f'<td>{escape(cell)}</td>'
            table += '</tr>'

        table += '</tbody></table>'
        return table

    @staticmethod
    def create_toc(levels: int = 3) -> str:
        """
        Create table of contents macro.

        Args:
            levels: Number of heading levels to include

        Returns:
            Confluence TOC markup
        """
        return f'''
<ac:structured-macro ac:name="toc">
    <ac:parameter ac:name="maxLevel">{levels}</ac:parameter>
</ac:structured-macro>
'''

    @staticmethod
    def create_page_link(page_title: str, link_text: Optional[str] = None) -> str:
        """
        Create link to another Confluence page.

        Args:
            page_title: Target page title
            link_text: Link text (defaults to page title)

        Returns:
            Confluence page link markup
        """
        link_text = link_text or page_title
        return f'''
<ac:link>
    <ri:page ri:content-title="{escape(page_title)}"/>
    <ac:plain-text-link-body><![CDATA[{link_text}]]></ac:plain-text-link-body>
</ac:link>
'''

    @staticmethod
    def create_status_macro(text: str, color: str = "Blue") -> str:
        """
        Create status lozenge.

        Args:
            text: Status text
            color: Status color (Blue, Green, Yellow, Red, Grey)

        Returns:
            Confluence status macro
        """
        return f'''
<ac:structured-macro ac:name="status">
    <ac:parameter ac:name="colour">{color}</ac:parameter>
    <ac:parameter ac:name="title">{escape(text)}</ac:parameter>
</ac:structured-macro>
'''

    @staticmethod
    def create_children_display() -> str:
        """
        Create children display macro.

        Returns:
            Confluence children display markup
        """
        return '''
<ac:structured-macro ac:name="children">
    <ac:parameter ac:name="all">true</ac:parameter>
</ac:structured-macro>
'''

    @staticmethod
    def create_section(content: str, columns: int = 1) -> str:
        """
        Create section layout.

        Args:
            content: Section content
            columns: Number of columns

        Returns:
            Confluence section markup
        """
        if columns == 1:
            return f'<div>{content}</div>'

        sections = content.split('|||')  # Split marker
        column_width = 100 // columns

        markup = '<ac:layout><ac:layout-section ac:type="two_equal">'
        for section in sections:
            markup += f'<ac:layout-cell><p>{section}</p></ac:layout-cell>'
        markup += '</ac:layout-section></ac:layout>'

        return markup

    @staticmethod
    def escape_special_chars(text: str) -> str:
        """
        Escape special characters for Confluence.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        return escape(text)


class ConfluencePageBuilder:
    """Build complete Confluence pages with proper structure."""

    def __init__(self, converter: Optional[StorageFormatConverter] = None):
        """
        Initialize page builder.

        Args:
            converter: Storage format converter instance
        """
        self.converter = converter or StorageFormatConverter()

    def build_index_page(
        self,
        title: str,
        summary: str,
        stats: Dict[str, Any],
        child_pages: List[str]
    ) -> str:
        """
        Build index/home page.

        Args:
            title: Page title
            summary: Summary text
            stats: Statistics dictionary
            child_pages: List of child page titles

        Returns:
            Confluence Storage Format content
        """
        content = f'<h1>{self.converter.escape_special_chars(title)}</h1>'
        content += f'<p>{self.converter.escape_special_chars(summary)}</p>'

        # Statistics panel
        stats_content = '<table><tbody>'
        for key, value in stats.items():
            stats_content += f'<tr><th>{self.converter.escape_special_chars(key)}</th><td>{value}</td></tr>'
        stats_content += '</tbody></table>'

        content += self.converter.create_info_panel("Statistics", stats_content, "info")

        # Table of contents
        content += '<h2>Contents</h2>'
        content += self.converter.create_children_display()

        # Child page links
        if child_pages:
            content += '<h2>Pages</h2><ul>'
            for page_title in child_pages:
                content += f'<li>{self.converter.create_page_link(page_title)}</li>'
            content += '</ul>'

        return content

    def build_thread_page(self, thread_data: Dict[str, Any]) -> str:
        """
        Build thread detail page.

        Args:
            thread_data: Thread data dictionary

        Returns:
            Confluence Storage Format content
        """
        title = thread_data.get('title', 'Untitled Thread')
        content = f'<h1>{self.converter.escape_special_chars(title)}</h1>'

        # Metadata panel
        metadata = thread_data.get('metadata', {})
        meta_content = f'''
Created: {metadata.get('created_at', 'Unknown')}<br/>
Messages: {metadata.get('message_count', 0)}<br/>
Participants: {metadata.get('participant_count', 0)}
'''
        content += self.converter.create_info_panel("Thread Information", meta_content, "note")

        # Summary
        if thread_data.get('analysis', {}).get('summary'):
            content += '<h2>Summary</h2>'
            summary = thread_data['analysis']['summary']
            content += f'<p>{self.converter.escape_special_chars(summary)}</p>'

        # Categories
        categories = thread_data.get('analysis', {}).get('categories', [])
        if categories:
            content += '<h2>Categories</h2><p>'
            for cat in categories:
                cat_name = cat.get('name', 'Unknown')
                content += self.converter.create_status_macro(cat_name, "Blue") + ' '
            content += '</p>'

        # Topics
        topics = thread_data.get('analysis', {}).get('topics', [])
        if topics:
            content += '<h2>Topics</h2><p>'
            for topic in topics:
                topic_name = topic.get('name', 'Unknown')
                content += self.converter.create_status_macro(topic_name, "Green") + ' '
            content += '</p>'

        # Key Points
        key_points = thread_data.get('analysis', {}).get('key_points', [])
        if key_points:
            content += '<h2>Key Points</h2><ul>'
            for point in key_points:
                content += f'<li>{self.converter.escape_special_chars(point)}</li>'
            content += '</ul>'

        # Q&A Pairs
        qa_pairs = thread_data.get('analysis', {}).get('qa_pairs', [])
        if qa_pairs:
            content += '<h2>Questions &amp; Answers</h2>'
            for qa in qa_pairs:
                question = qa.get('question', '')
                answer = qa.get('answer', '')
                qa_content = f'''
<p><strong>Q:</strong> {self.converter.escape_special_chars(question)}</p>
<p><strong>A:</strong> {self.converter.escape_special_chars(answer)}</p>
'''
                content += self.converter.create_expand(question, qa_content)

        # Messages
        messages = thread_data.get('messages', [])
        if messages:
            content += '<h2>Conversation</h2>'

            for msg in messages:
                user = msg.get('user', 'Unknown')
                text = msg.get('text', '')
                timestamp = msg.get('timestamp', '')

                msg_content = f'''
<p><strong>{self.converter.escape_special_chars(user)}</strong> - <em>{timestamp}</em></p>
<p>{self.converter.escape_special_chars(text)}</p>
'''
                content += f'<div style="border-left: 3px solid #0052CC; padding-left: 10px; margin-bottom: 15px;">{msg_content}</div>'

        return content

    def build_category_index(
        self,
        categories: Dict[str, List[str]]
    ) -> str:
        """
        Build category index page.

        Args:
            categories: Dictionary mapping category names to page titles

        Returns:
            Confluence Storage Format content
        """
        content = '<h1>Categories</h1>'
        content += self.converter.create_toc(2)

        for category, pages in sorted(categories.items()):
            content += f'<h2>{self.converter.escape_special_chars(category)}</h2>'
            content += f'<p>{len(pages)} threads</p><ul>'

            for page_title in pages[:50]:  # Limit to 50
                content += f'<li>{self.converter.create_page_link(page_title)}</li>'

            content += '</ul>'

        return content

    def build_faq_page(self, qa_pairs: List[Dict[str, Any]]) -> str:
        """
        Build FAQ page.

        Args:
            qa_pairs: List of Q&A dictionaries

        Returns:
            Confluence Storage Format content
        """
        content = '<h1>Frequently Asked Questions</h1>'
        content += self.converter.create_toc(2)

        for i, qa in enumerate(qa_pairs[:50], 1):  # Top 50
            question = qa.get('question', '')
            answer = qa.get('answer', '')
            source = qa.get('source_thread', '')

            content += f'<h2>{i}. {self.converter.escape_special_chars(question)}</h2>'
            content += f'<p>{self.converter.escape_special_chars(answer)}</p>'

            if source:
                content += f'<p><em>Source: {self.converter.create_page_link(source)}</em></p>'

        return content

"""
Tests for Confluence Storage Format converter.
"""

import pytest
from threadcrumb.confluence.storage_format import StorageFormatConverter, ConfluencePageBuilder


@pytest.mark.unit
@pytest.mark.confluence
class TestStorageFormatConverter:
    """Test StorageFormatConverter class."""

    def test_markdown_headers_conversion(self):
        """Test converting Markdown headers to Confluence format."""
        converter = StorageFormatConverter()

        markdown = "# Header 1\n## Header 2\n### Header 3"
        result = converter.markdown_to_storage(markdown)

        assert "<h1>Header 1</h1>" in result
        assert "<h2>Header 2</h2>" in result
        assert "<h3>Header 3</h3>" in result

    def test_markdown_bold_conversion(self):
        """Test converting bold text."""
        converter = StorageFormatConverter()

        markdown = "This is **bold** and __also bold__"
        result = converter.markdown_to_storage(markdown)

        assert "<strong>bold</strong>" in result
        assert "<strong>also bold</strong>" in result

    def test_markdown_italic_conversion(self):
        """Test converting italic text."""
        converter = StorageFormatConverter()

        markdown = "This is *italic* text"
        result = converter.markdown_to_storage(markdown)

        assert "<em>italic</em>" in result

    def test_markdown_code_inline(self):
        """Test converting inline code."""
        converter = StorageFormatConverter()

        markdown = "Use `code` here"
        result = converter.markdown_to_storage(markdown)

        assert "<code>code</code>" in result

    def test_create_info_panel(self):
        """Test creating info panel."""
        converter = StorageFormatConverter()

        panel = converter.create_info_panel("Test Title", "Test content", "info")

        assert 'ac:name="info"' in panel
        assert "Test Title" in panel
        assert "Test content" in panel

    def test_create_code_block(self):
        """Test creating code block."""
        converter = StorageFormatConverter()

        code_block = converter.create_code_block("print('hello')", "python")

        assert 'ac:name="code"' in code_block
        assert 'ac:parameter ac:name="language">python' in code_block
        assert "print('hello')" in code_block

    def test_create_expand(self):
        """Test creating expand macro."""
        converter = StorageFormatConverter()

        expand = converter.create_expand("Click to expand", "<p>Hidden content</p>")

        assert 'ac:name="expand"' in expand
        assert "Click to expand" in expand
        assert "Hidden content" in expand

    def test_create_table(self):
        """Test creating table."""
        converter = StorageFormatConverter()

        headers = ["Column 1", "Column 2"]
        rows = [["A", "B"], ["C", "D"]]

        table = converter.create_table(headers, rows)

        assert "<table>" in table
        assert "<thead>" in table
        assert "<th>Column 1</th>" in table
        assert "<td>A</td>" in table

    def test_create_toc(self):
        """Test creating table of contents."""
        converter = StorageFormatConverter()

        toc = converter.create_toc(3)

        assert 'ac:name="toc"' in toc
        assert 'ac:parameter ac:name="maxLevel">3' in toc

    def test_create_page_link(self):
        """Test creating page link."""
        converter = StorageFormatConverter()

        link = converter.create_page_link("Target Page", "Link Text")

        assert 'ri:page ri:content-title="Target Page"' in link
        assert "Link Text" in link

    def test_create_status_macro(self):
        """Test creating status macro."""
        converter = StorageFormatConverter()

        status = converter.create_status_macro("In Progress", "Yellow")

        assert 'ac:name="status"' in status
        assert 'ac:parameter ac:name="colour">Yellow' in status
        assert "In Progress" in status

    def test_escape_special_chars(self):
        """Test escaping special characters."""
        converter = StorageFormatConverter()

        text = "<script>alert('xss')</script>"
        escaped = converter.escape_special_chars(text)

        assert "&lt;script&gt;" in escaped
        assert "&lt;/script&gt;" in escaped


@pytest.mark.unit
@pytest.mark.confluence
class TestConfluencePageBuilder:
    """Test ConfluencePageBuilder class."""

    def test_build_index_page(self, sample_processed_channel):
        """Test building index page."""
        builder = ConfluencePageBuilder()

        content = builder.build_index_page(
            title="Test Wiki",
            summary="Test summary",
            stats={"Channels": 5, "Threads": 100},
            child_pages=["Page 1", "Page 2"]
        )

        assert "Test Wiki" in content
        assert "Test summary" in content
        assert "Channels" in content
        assert "Page 1" in content

    def test_build_thread_page(self, sample_processed_thread):
        """Test building thread page."""
        builder = ConfluencePageBuilder()

        content = builder.build_thread_page(sample_processed_thread.to_dict())

        assert sample_processed_thread.title in content
        assert sample_processed_thread.analysis.summary in content
        assert "OAuth" in content  # Topic
        assert "Technical Discussion" in content  # Category

    def test_build_faq_page(self):
        """Test building FAQ page."""
        builder = ConfluencePageBuilder()

        qa_pairs = [
            {
                "question": "What is OAuth?",
                "answer": "OAuth is an authorization framework",
                "confidence": 0.9,
                "source_thread": "thread-123"
            }
        ]

        content = builder.build_faq_page(qa_pairs)

        assert "Frequently Asked Questions" in content
        assert "What is OAuth?" in content
        assert "OAuth is an authorization framework" in content

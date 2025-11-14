"""
Tests for Confluence client.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from threadcrumb.confluence.client import ConfluenceClient, ConfluencePage


@pytest.mark.unit
@pytest.mark.confluence
class TestConfluenceClient:
    """Test ConfluenceClient class."""

    def test_init_cloud(self):
        """Test initialization for Confluence Cloud."""
        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token="token123",
            space_key="TEST",
            use_cloud=True
        )

        assert client.base_url == "https://test.atlassian.net"
        assert client.username == "test@example.com"
        assert client.api_token == "token123"
        assert client.space_key == "TEST"
        assert client.use_cloud == True
        assert client.api_base == "https://test.atlassian.net/wiki/rest/api"

    def test_init_server(self):
        """Test initialization for Confluence Server."""
        client = ConfluenceClient(
            base_url="http://confluence.example.com",
            username="testuser",
            api_token="password123",
            space_key="TEST",
            use_cloud=False
        )

        assert client.api_base == "http://confluence.example.com/rest/api"

    @patch('threadcrumb.confluence.client.requests.Session')
    def test_test_connection_success(self, mock_session):
        """Test successful connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.return_value.request.return_value = mock_response

        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token="token",
            space_key="TEST"
        )

        assert client.test_connection() == True

    @patch('threadcrumb.confluence.client.requests.Session')
    def test_test_connection_failure(self, mock_session):
        """Test failed connection test."""
        mock_session.return_value.request.side_effect = Exception("Connection failed")

        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token="token",
            space_key="TEST"
        )

        assert client.test_connection() == False

    @patch('threadcrumb.confluence.client.requests.Session')
    def test_get_space(self, mock_session):
        """Test getting space information."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "key": "TEST",
            "name": "Test Space",
            "type": "global"
        }
        mock_session.return_value.request.return_value = mock_response

        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token="token",
            space_key="TEST"
        )

        space = client.get_space()
        assert space["key"] == "TEST"
        assert space["name"] == "Test Space"

    @patch('threadcrumb.confluence.client.requests.Session')
    def test_create_page(self, mock_session):
        """Test creating a page."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456",
            "title": "Test Page",
            "type": "page"
        }
        mock_session.return_value.request.return_value = mock_response

        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token="token",
            space_key="TEST"
        )

        page = client.create_page(
            title="Test Page",
            body="<p>Test content</p>"
        )

        assert page["id"] == "123456"
        assert page["title"] == "Test Page"

    @patch('threadcrumb.confluence.client.requests.Session')
    def test_update_page(self, mock_session):
        """Test updating a page."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456",
            "title": "Updated Page",
            "version": {"number": 2}
        }
        mock_session.return_value.request.return_value = mock_response

        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token="token",
            space_key="TEST"
        )

        page = client.update_page(
            page_id="123456",
            title="Updated Page",
            body="<p>Updated content</p>",
            version=1
        )

        assert page["version"]["number"] == 2

    @patch('threadcrumb.confluence.client.requests.Session')
    def test_search_pages(self, mock_session):
        """Test searching for pages."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": "123", "title": "Page 1"},
                {"id": "456", "title": "Page 2"}
            ]
        }
        mock_session.return_value.request.return_value = mock_response

        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token="token",
            space_key="TEST"
        )

        results = client.search_pages("Test")
        assert len(results) == 2
        assert results[0]["title"] == "Page 1"

    @patch('threadcrumb.confluence.client.requests.Session')
    def test_create_or_update_page_create(self, mock_session):
        """Test create_or_update when page doesn't exist."""
        # First call: search returns empty
        search_response = Mock()
        search_response.status_code = 200
        search_response.json.return_value = {"results": []}

        # Second call: create page
        create_response = Mock()
        create_response.status_code = 200
        create_response.json.return_value = {"id": "123", "title": "New Page"}

        mock_session.return_value.request.side_effect = [search_response, create_response]

        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token="token",
            space_key="TEST"
        )

        page = client.create_or_update_page("New Page", "<p>Content</p>")
        assert page["id"] == "123"

    @patch('threadcrumb.confluence.client.requests.Session')
    def test_add_labels(self, mock_session):
        """Test adding labels to a page."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.return_value.request.return_value = mock_response

        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token="token",
            space_key="TEST"
        )

        # Should not raise exception
        client.add_labels("123456", ["label1", "label2"])

    @patch('threadcrumb.confluence.client.requests.Session')
    def test_error_handling(self, mock_session):
        """Test error handling for API failures."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.HTTPError("Unauthorized")
        mock_response.text = "Unauthorized"
        mock_session.return_value.request.return_value = mock_response

        client = ConfluenceClient(
            base_url="https://test.atlassian.net",
            username="test@example.com",
            api_token="wrong-token",
            space_key="TEST"
        )

        with pytest.raises(requests.HTTPError):
            client.get_space()


@pytest.mark.unit
@pytest.mark.confluence
class TestConfluencePage:
    """Test ConfluencePage dataclass."""

    def test_confluence_page_creation(self):
        """Test creating a ConfluencePage."""
        page = ConfluencePage(
            title="Test Page",
            body="<p>Content</p>",
            space_key="TEST",
            parent_id="123",
            page_id="456",
            version=1
        )

        assert page.title == "Test Page"
        assert page.body == "<p>Content</p>"
        assert page.space_key == "TEST"
        assert page.parent_id == "123"
        assert page.page_id == "456"
        assert page.version == 1

    def test_confluence_page_defaults(self):
        """Test ConfluencePage default values."""
        page = ConfluencePage(
            title="Test",
            body="<p>Test</p>",
            space_key="TEST"
        )

        assert page.parent_id is None
        assert page.page_id is None
        assert page.version is None

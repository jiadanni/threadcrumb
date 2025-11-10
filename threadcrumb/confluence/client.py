"""
Confluence API client for direct page creation and updates.
"""

import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


@dataclass
class ConfluencePage:
    """Represents a Confluence page."""
    title: str
    body: str
    space_key: str
    parent_id: Optional[str] = None
    page_id: Optional[str] = None
    version: Optional[int] = None


class ConfluenceClient:
    """Client for Confluence REST API."""

    def __init__(
        self,
        base_url: str,
        username: str,
        api_token: str,
        space_key: str,
        use_cloud: bool = True
    ):
        """
        Initialize Confluence client.

        Args:
            base_url: Confluence base URL (e.g., https://yoursite.atlassian.net)
            username: Confluence username (email for Cloud)
            api_token: API token (for Cloud) or password (for Server)
            space_key: Default space key
            use_cloud: True for Confluence Cloud, False for Server/Data Center
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.space_key = space_key
        self.use_cloud = use_cloud

        # API endpoints differ between Cloud and Server
        if use_cloud:
            self.api_base = f"{self.base_url}/wiki/rest/api"
        else:
            self.api_base = f"{self.base_url}/rest/api"

        self.session = requests.Session()
        self.session.auth = (username, api_token)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> requests.Response:
        """
        Make API request with error handling.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            Response object

        Raises:
            requests.HTTPError: If request fails
        """
        url = urljoin(self.api_base + '/', endpoint.lstrip('/'))

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            logger.error(f"Confluence API error: {e}")
            logger.error(f"Response: {response.text}")
            raise

    def test_connection(self) -> bool:
        """
        Test connection to Confluence.

        Returns:
            True if connection successful
        """
        try:
            response = self._make_request('GET', '/space')
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_space(self, space_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get space information.

        Args:
            space_key: Space key (defaults to instance space_key)

        Returns:
            Space information
        """
        space_key = space_key or self.space_key
        response = self._make_request('GET', f'/space/{space_key}')
        return response.json()

    def search_pages(
        self,
        title: str,
        space_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for pages by title.

        Args:
            title: Page title to search
            space_key: Space key to search in

        Returns:
            List of matching pages
        """
        space_key = space_key or self.space_key
        params = {
            'cql': f'space={space_key} AND title="{title}"',
            'limit': 25
        }
        response = self._make_request('GET', '/content/search', params=params)
        return response.json().get('results', [])

    def get_page(self, page_id: str, expand: str = 'body.storage,version') -> Dict[str, Any]:
        """
        Get page by ID.

        Args:
            page_id: Page ID
            expand: Fields to expand

        Returns:
            Page information
        """
        params = {'expand': expand}
        response = self._make_request('GET', f'/content/{page_id}', params=params)
        return response.json()

    def create_page(
        self,
        title: str,
        body: str,
        space_key: Optional[str] = None,
        parent_id: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new page.

        Args:
            title: Page title
            body: Page body in Confluence Storage Format
            space_key: Space key
            parent_id: Parent page ID (optional)
            labels: List of labels to add

        Returns:
            Created page information
        """
        space_key = space_key or self.space_key

        page_data = {
            'type': 'page',
            'title': title,
            'space': {'key': space_key},
            'body': {
                'storage': {
                    'value': body,
                    'representation': 'storage'
                }
            }
        }

        # Add parent if specified
        if parent_id:
            page_data['ancestors'] = [{'id': parent_id}]

        # Create page
        response = self._make_request('POST', '/content', json=page_data)
        page = response.json()

        # Add labels if specified
        if labels:
            self.add_labels(page['id'], labels)

        logger.info(f"Created page: {title} (ID: {page['id']})")
        return page

    def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
        version: int,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing page.

        Args:
            page_id: Page ID
            title: Page title
            body: Page body in Confluence Storage Format
            version: Current version number
            parent_id: Parent page ID (optional)

        Returns:
            Updated page information
        """
        page_data = {
            'type': 'page',
            'title': title,
            'version': {'number': version + 1},
            'body': {
                'storage': {
                    'value': body,
                    'representation': 'storage'
                }
            }
        }

        # Update parent if specified
        if parent_id:
            page_data['ancestors'] = [{'id': parent_id}]

        response = self._make_request('PUT', f'/content/{page_id}', json=page_data)
        logger.info(f"Updated page: {title} (ID: {page_id})")
        return response.json()

    def create_or_update_page(
        self,
        title: str,
        body: str,
        space_key: Optional[str] = None,
        parent_id: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create page if it doesn't exist, otherwise update it.

        Args:
            title: Page title
            body: Page body in Confluence Storage Format
            space_key: Space key
            parent_id: Parent page ID
            labels: List of labels

        Returns:
            Page information
        """
        space_key = space_key or self.space_key

        # Search for existing page
        existing = self.search_pages(title, space_key)

        if existing:
            # Update existing page
            page = existing[0]
            page_id = page['id']

            # Get current version
            full_page = self.get_page(page_id)
            version = full_page['version']['number']

            return self.update_page(page_id, title, body, version, parent_id)
        else:
            # Create new page
            return self.create_page(title, body, space_key, parent_id, labels)

    def add_labels(self, page_id: str, labels: List[str]) -> None:
        """
        Add labels to a page.

        Args:
            page_id: Page ID
            labels: List of label names
        """
        label_data = [{'name': label} for label in labels]
        self._make_request('POST', f'/content/{page_id}/label', json=label_data)
        logger.info(f"Added labels to page {page_id}: {', '.join(labels)}")

    def delete_page(self, page_id: str) -> None:
        """
        Delete a page.

        Args:
            page_id: Page ID
        """
        self._make_request('DELETE', f'/content/{page_id}')
        logger.info(f"Deleted page: {page_id}")

    def get_page_children(
        self,
        page_id: str,
        expand: str = 'page'
    ) -> List[Dict[str, Any]]:
        """
        Get child pages of a page.

        Args:
            page_id: Parent page ID
            expand: Fields to expand

        Returns:
            List of child pages
        """
        params = {'expand': expand}
        response = self._make_request(
            'GET',
            f'/content/{page_id}/child/page',
            params=params
        )
        return response.json().get('results', [])

    def create_page_hierarchy(
        self,
        pages: List[ConfluencePage],
        parent_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create a hierarchy of pages.

        Args:
            pages: List of ConfluencePage objects
            parent_id: Root parent page ID

        Returns:
            Dictionary mapping page titles to page IDs
        """
        page_map = {}

        for page in pages:
            # Use specified parent or hierarchy parent
            effective_parent = page.parent_id or parent_id

            created_page = self.create_or_update_page(
                title=page.title,
                body=page.body,
                space_key=page.space_key or self.space_key,
                parent_id=effective_parent
            )

            page_map[page.title] = created_page['id']
            logger.info(f"Created/updated: {page.title}")

        return page_map

    def add_attachment(
        self,
        page_id: str,
        file_path: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add file attachment to a page.

        Args:
            page_id: Page ID
            file_path: Path to file
            comment: Optional comment

        Returns:
            Attachment information
        """
        import os

        filename = os.path.basename(file_path)

        with open(file_path, 'rb') as f:
            files = {
                'file': (filename, f, 'application/octet-stream')
            }

            data = {}
            if comment:
                data['comment'] = comment

            # Remove Content-Type header for multipart
            headers = self.session.headers.copy()
            headers.pop('Content-Type', None)

            response = self._make_request(
                'POST',
                f'/content/{page_id}/child/attachment',
                files=files,
                data=data,
                headers=headers
            )

        logger.info(f"Added attachment: {filename} to page {page_id}")
        return response.json()

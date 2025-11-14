"""
Test fixtures and configuration.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime

from threadcrumb.config import Config, SlackConfig, AIConfig, ConfluenceConfig
from threadcrumb.slack.messages import Message, Thread
from threadcrumb.processing.pipeline import ProcessedThread, ProcessedChannel


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def mock_slack_config():
    """Provide a mock Slack configuration."""
    return SlackConfig(
        access_token="xoxb-test-token",
        workspace_id="T12345678",
        rate_limit_delay=0.1,
        max_retries=1,
        cache_enabled=False
    )


@pytest.fixture
def mock_ai_config():
    """Provide a mock AI configuration."""
    return AIConfig(
        provider="bedrock",
        model_name="anthropic.claude-3-haiku-20240307-v1:0",
        region="us-east-1",
        max_tokens=1000,
        temperature=0.7,
        fallback_enabled=True
    )


@pytest.fixture
def mock_confluence_config():
    """Provide a mock Confluence configuration."""
    return ConfluenceConfig(
        base_url="https://test.atlassian.net",
        username="test@example.com",
        api_token="test-token",
        space_key="TEST",
        use_cloud=True,
        root_page_title="Test Wiki",
        structure="flat",
        add_labels=True,
        dry_run=False
    )


@pytest.fixture
def mock_config(mock_slack_config, mock_ai_config, mock_confluence_config):
    """Provide a complete mock configuration."""
    return Config(
        slack=mock_slack_config,
        ai=mock_ai_config,
        confluence=mock_confluence_config
    )


@pytest.fixture
def sample_message():
    """Provide a sample Slack message."""
    return Message(
        ts="1234567890.123456",
        user="U12345678",
        text="This is a test message",
        channel_id="C12345678",
        thread_ts=None,
        reply_count=0,
        reactions=[],
        attachments=[],
        files=[],
        type="message"
    )


@pytest.fixture
def sample_thread(sample_message):
    """Provide a sample Slack thread."""
    parent = sample_message
    reply1 = Message(
        ts="1234567890.123457",
        user="U87654321",
        text="This is a reply",
        channel_id="C12345678",
        thread_ts=parent.ts,
        reply_count=0
    )
    reply2 = Message(
        ts="1234567890.123458",
        user="U12345678",
        text="Another reply",
        channel_id="C12345678",
        thread_ts=parent.ts,
        reply_count=0
    )

    return Thread(
        thread_ts=parent.ts,
        channel_id="C12345678",
        parent=parent,
        replies=[reply1, reply2],
        participants={"U12345678", "U87654321"}
    )


@pytest.fixture
def sample_processed_thread():
    """Provide a sample processed thread."""
    from threadcrumb.ai.processor import ContentAnalysis, Category, Topic, QAPair

    analysis = ContentAnalysis(
        summary="This is a test discussion about authentication",
        categories=[
            Category(name="Technical Discussion", confidence=0.9, description="Technical topic"),
            Category(name="Authentication", confidence=0.8, description="Auth related")
        ],
        topics=[
            Topic(name="OAuth", keywords=["oauth", "authentication", "token"]),
            Topic(name="Security", keywords=["security", "encryption"])
        ],
        qa_pairs=[
            QAPair(
                question="How does OAuth work?",
                answer="OAuth is an authorization framework...",
                confidence=0.85
            )
        ],
        key_points=[
            "OAuth provides secure authentication",
            "Token-based authentication is recommended"
        ],
        sentiment="neutral",
        importance_score=0.75
    )

    return ProcessedThread(
        thread_ts="1234567890.123456",
        channel_id="C12345678",
        channel_name="engineering",
        title="OAuth Authentication Discussion",
        messages=[
            {
                "ts": "1234567890.123456",
                "user": "U12345678",
                "text": "How does OAuth work?",
                "timestamp": datetime.now().isoformat()
            },
            {
                "ts": "1234567890.123457",
                "user": "U87654321",
                "text": "OAuth is an authorization framework...",
                "timestamp": datetime.now().isoformat()
            }
        ],
        analysis=analysis,
        metadata={
            "created_at": datetime.now().isoformat(),
            "message_count": 2,
            "participant_count": 2
        }
    )


@pytest.fixture
def sample_processed_channel(sample_processed_thread):
    """Provide a sample processed channel."""
    return ProcessedChannel(
        channel_id="C12345678",
        channel_name="engineering",
        description="Engineering team discussions",
        threads=[sample_processed_thread],
        metadata={
            "member_count": 50,
            "is_private": False
        }
    )


@pytest.fixture
def mock_slack_client():
    """Provide a mock Slack client."""
    client = Mock()
    client.get_workspace_info.return_value = {
        "name": "Test Workspace",
        "id": "T12345678"
    }
    client.list_channels.return_value = [
        {
            "id": "C12345678",
            "name": "general",
            "is_private": False,
            "num_members": 100
        },
        {
            "id": "C87654321",
            "name": "engineering",
            "is_private": False,
            "num_members": 50
        }
    ]
    client.get_channel_history.return_value = []
    client.get_users.return_value = {
        "U12345678": {"id": "U12345678", "name": "testuser", "real_name": "Test User"},
        "U87654321": {"id": "U87654321", "name": "otheruser", "real_name": "Other User"}
    }
    return client


@pytest.fixture
def mock_confluence_client():
    """Provide a mock Confluence client."""
    client = Mock()
    client.test_connection.return_value = True
    client.get_space.return_value = {"key": "TEST", "name": "Test Space"}
    client.create_page.return_value = {"id": "123456", "title": "Test Page"}
    client.update_page.return_value = {"id": "123456", "title": "Test Page"}
    client.search_pages.return_value = []
    return client


@pytest.fixture
def mock_bedrock_client():
    """Provide a mock Bedrock client."""
    from threadcrumb.ai.bedrock import AIResponse

    client = Mock()
    client.test_connection.return_value = True
    client.invoke.return_value = AIResponse(
        content='{"summary": "Test summary", "categories": [{"name": "Test", "confidence": 0.9}]}',
        model="test-model",
        usage={"input_tokens": 100, "output_tokens": 50},
        raw_response={}
    )
    return client

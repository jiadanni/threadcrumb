"""Tests for multi-provider AI support."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock external dependencies before importing modules that use them
sys.modules['openai'] = MagicMock()
sys.modules['anthropic'] = MagicMock()

from threadcrumb.ai.providers import (
    BaseAIProvider,
    OpenAIProvider,
    AnthropicProvider,
    create_ai_provider,
    get_ai_provider,
    AIResponse
)


class TestAIResponse:
    """Test AIResponse dataclass."""

    def test_create_response(self):
        """Test creating AI response."""
        response = AIResponse(
            content="Test response",
            model="gpt-4",
            usage={"input_tokens": 10, "output_tokens": 20},
            raw_response={}
        )

        assert response.content == "Test response"
        assert response.model == "gpt-4"
        assert response.usage["input_tokens"] == 10


class TestBaseAIProvider:
    """Test base AI provider."""

    def test_base_provider_invoke_not_implemented(self):
        """Test that base provider invoke raises NotImplementedError."""
        provider = BaseAIProvider()

        with pytest.raises(NotImplementedError):
            provider.invoke("test prompt")


class TestOpenAIProvider:
    """Test OpenAI provider."""

    def test_create_openai_provider(self):
        """Test OpenAI provider initialization."""
        provider = OpenAIProvider(
            api_key="test-key",
            model="gpt-4"
        )

        assert provider.model == "gpt-4"
        assert provider.max_tokens == 4096

    def test_openai_invoke(self):
        """Test OpenAI provider invocation."""
        # Mock OpenAI client
        mock_client = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.model_dump.return_value = {"test": "data"}

        mock_client.chat.completions.create.return_value = mock_response

        # Create provider and inject client
        provider = OpenAIProvider(api_key="test-key")
        provider.client = mock_client

        response = provider.invoke("test prompt", system="You are helpful")

        assert response.content == "Test response"
        assert response.usage["input_tokens"] == 10
        assert response.usage["output_tokens"] == 20

        # Verify API was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "gpt-4-turbo-preview"
        assert len(call_args["messages"]) == 2  # System + user


class TestAnthropicProvider:
    """Test Anthropic provider."""

    def test_create_anthropic_provider(self):
        """Test Anthropic provider initialization."""
        provider = AnthropicProvider(
            api_key="test-key",
            model="claude-3-sonnet-20240229"
        )

        assert provider.model == "claude-3-sonnet-20240229"
        assert provider.max_tokens == 4096

    def test_anthropic_invoke(self):
        """Test Anthropic provider invocation."""
        # Mock Anthropic client
        mock_client = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Test response"
        mock_response.usage.input_tokens = 15
        mock_response.usage.output_tokens = 25
        mock_response.model_dump.return_value = {"test": "data"}

        mock_client.messages.create.return_value = mock_response

        # Create provider and inject client
        provider = AnthropicProvider(api_key="test-key")
        provider.client = mock_client

        response = provider.invoke(
            "test prompt",
            system="You are helpful",
            max_tokens=1000
        )

        assert response.content == "Test response"
        assert response.usage["input_tokens"] == 15
        assert response.usage["output_tokens"] == 25

        # Verify API was called correctly
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args[1]
        assert call_args["model"] == "claude-3-sonnet-20240229"
        assert call_args["system"] == "You are helpful"
        assert call_args["max_tokens"] == 1000


class TestProviderFactory:
    """Test provider factory functions."""

    def test_create_openai_provider(self):
        """Test creating OpenAI provider via factory."""
        provider = create_ai_provider(
            "openai",
            api_key="test-key",
            model="gpt-4"
        )

        assert isinstance(provider, OpenAIProvider)

    def test_create_anthropic_provider(self):
        """Test creating Anthropic provider via factory."""
        provider = create_ai_provider(
            "anthropic",
            api_key="test-key",
            model="claude-3-opus-20240229"
        )

        assert isinstance(provider, AnthropicProvider)

    @patch('threadcrumb.ai.bedrock.BedrockClient')
    def test_create_bedrock_provider(self, mock_bedrock):
        """Test creating Bedrock provider via factory."""
        from threadcrumb.ai.providers import create_ai_provider

        provider = create_ai_provider(
            "bedrock",
            region="us-east-1",
            model_name="anthropic.claude-3-sonnet"
        )

        # Bedrock client should be created
        mock_bedrock.assert_called_once()

    def test_create_unknown_provider(self):
        """Test creating unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown provider"):
            create_ai_provider("unknown")


class TestGetAIProvider:
    """Test get_ai_provider configuration function."""

    @patch('threadcrumb.ai.bedrock.BedrockClient')
    def test_get_bedrock_provider(self, mock_bedrock):
        """Test getting Bedrock provider from config."""
        # Mock config
        config = Mock()
        config.ai.region = "us-east-1"
        config.ai.model_name = "anthropic.claude-3-sonnet"
        config.ai.max_tokens = 4096
        config.ai.temperature = 0.7
        config.ai.aws_profile = None

        provider = get_ai_provider("bedrock", config)

        # Should create Bedrock client
        mock_bedrock.assert_called_once_with(
            region="us-east-1",
            model_name="anthropic.claude-3-sonnet",
            max_tokens=4096,
            temperature=0.7,
            aws_profile=None
        )

    @patch('os.getenv')
    def test_get_openai_provider_from_env(self, mock_getenv):
        """Test getting OpenAI provider from environment variable."""
        def side_effect(key, default=None):
            if key == 'OPENAI_API_KEY':
                return 'test-api-key'
            return default
        mock_getenv.side_effect = side_effect

        config = Mock()
        config.ai.max_tokens = 4096
        config.ai.temperature = 0.7
        # Ensure config doesn't have the key
        del config.ai.openai_api_key

        provider = get_ai_provider("openai", config)

        assert provider is not None
        # Environment variable should be checked
        mock_getenv.assert_any_call('OPENAI_API_KEY')

    def test_get_openai_provider_from_config(self):
        """Test getting OpenAI provider from config."""
        config = Mock()
        config.ai.openai_api_key = "config-api-key"
        config.ai.openai_model = "gpt-4"
        config.ai.max_tokens = 4096
        config.ai.temperature = 0.7

        provider = get_ai_provider("openai", config)

        assert provider is not None

    @patch('os.getenv', return_value=None)
    def test_get_openai_provider_no_key(self, mock_getenv):
        """Test OpenAI provider returns None without API key."""
        config = Mock()
        config.ai.max_tokens = 4096
        config.ai.temperature = 0.7

        # No key in config
        if hasattr(config.ai, 'openai_api_key'):
            del config.ai.openai_api_key

        provider = get_ai_provider("openai", config)

        assert provider is None

    @patch('os.getenv')
    def test_get_anthropic_provider_from_env(self, mock_getenv):
        """Test getting Anthropic provider from environment."""
        def side_effect(key, default=None):
            if key == 'ANTHROPIC_API_KEY':
                return 'test-anthropic-key'
            return default
        mock_getenv.side_effect = side_effect

        config = Mock()
        config.ai.max_tokens = 4096
        config.ai.temperature = 0.7
        # Ensure config doesn't have the key
        del config.ai.anthropic_api_key

        provider = get_ai_provider("anthropic", config)

        assert provider is not None
        mock_getenv.assert_any_call('ANTHROPIC_API_KEY')

    def test_get_unknown_provider(self):
        """Test getting unknown provider returns None."""
        config = Mock()
        provider = get_ai_provider("invalid", config)

        assert provider is None

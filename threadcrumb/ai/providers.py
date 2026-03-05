"""
Multiple AI provider support (OpenAI, Anthropic, AWS Bedrock).
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """Unified AI response."""
    content: str
    model: str
    usage: Dict[str, int]
    raw_response: Dict[str, Any]


class BaseAIProvider:
    """Base class for AI providers."""

    def invoke(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AIResponse:
        """Invoke the AI model."""
        raise NotImplementedError

    def test_connection(self) -> bool:
        """Test connection to AI service."""
        try:
            response = self.invoke("Hello", max_tokens=10)
            return bool(response.content)
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model name
            max_tokens: Maximum tokens
            temperature: Sampling temperature
        """
        try:
            import openai
            self.openai = openai
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def invoke(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AIResponse:
        """Invoke OpenAI model."""
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )

        return AIResponse(
            content=response.choices[0].message.content,
            model=self.model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            },
            raw_response=response.model_dump()
        )


class AnthropicProvider(BaseAIProvider):
    """Anthropic API provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-sonnet-20240229",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model name
            max_tokens: Maximum tokens
            temperature: Sampling temperature
        """
        try:
            import anthropic
            self.anthropic = anthropic
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def invoke(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AIResponse:
        """Invoke Anthropic model."""
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)

        return AIResponse(
            content=response.content[0].text,
            model=self.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            raw_response=response.model_dump()
        )


def create_ai_provider(
    provider: str,
    **kwargs
) -> BaseAIProvider:
    """
    Factory function to create AI provider.

    Args:
        provider: Provider name (bedrock, openai, anthropic)
        **kwargs: Provider-specific arguments

    Returns:
        AIProvider instance
    """
    if provider == "openai":
        return OpenAIProvider(**kwargs)
    elif provider == "anthropic":
        return AnthropicProvider(**kwargs)
    elif provider == "bedrock":
        from .bedrock import BedrockClient
        return BedrockClient(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_ai_provider(provider_name: str, config):
    """
    Get AI provider from config.

    Args:
        provider_name: Provider name (bedrock, openai, anthropic)
        config: Configuration object

    Returns:
        AI provider instance or None
    """
    import os

    try:
        if provider_name == "bedrock":
            from .bedrock import BedrockClient
            return BedrockClient(
                region=config.ai.region,
                model_name=config.ai.model_name,
                max_tokens=config.ai.max_tokens,
                temperature=config.ai.temperature,
                aws_profile=config.ai.aws_profile
            )

        elif provider_name == "openai":
            # Get API key from config or environment
            api_key = getattr(config.ai, 'openai_api_key', None) or os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.error("OpenAI API key not found in config or OPENAI_API_KEY environment variable")
                return None

            model = getattr(config.ai, 'openai_model', 'gpt-4-turbo-preview')

            return OpenAIProvider(
                api_key=api_key,
                model=model,
                max_tokens=config.ai.max_tokens,
                temperature=config.ai.temperature
            )

        elif provider_name == "anthropic":
            # Get API key from config or environment
            api_key = getattr(config.ai, 'anthropic_api_key', None) or os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                logger.error("Anthropic API key not found in config or ANTHROPIC_API_KEY environment variable")
                return None

            model = getattr(config.ai, 'anthropic_model', 'claude-3-sonnet-20240229')

            return AnthropicProvider(
                api_key=api_key,
                model=model,
                max_tokens=config.ai.max_tokens,
                temperature=config.ai.temperature
            )

        else:
            logger.error(f"Unknown AI provider: {provider_name}")
            return None

    except Exception as e:
        logger.error(f"Failed to initialize {provider_name} provider: {e}")
        return None

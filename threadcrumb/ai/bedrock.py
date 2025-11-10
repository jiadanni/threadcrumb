"""
AWS Bedrock integration for AI-powered content processing.
"""

import json
import boto3
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """AI model response."""
    content: str
    model: str
    usage: Dict[str, int]
    raw_response: Dict[str, Any]


class BedrockClient:
    """Client for AWS Bedrock AI services."""

    # Supported models
    CLAUDE_3_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"
    CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
    CLAUDE_3_OPUS = "anthropic.claude-3-opus-20240229-v1:0"
    CLAUDE_2_1 = "anthropic.claude-v2:1"

    def __init__(
        self,
        region: str = "us-east-1",
        model_name: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        aws_profile: Optional[str] = None
    ):
        """
        Initialize Bedrock client.

        Args:
            region: AWS region
            model_name: Model identifier
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            aws_profile: AWS profile name
        """
        self.region = region
        self.model_name = model_name or self.CLAUDE_3_SONNET
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Initialize boto3 client
        session_kwargs = {"region_name": region}
        if aws_profile:
            session_kwargs["profile_name"] = aws_profile

        session = boto3.Session(**session_kwargs)
        self.client = session.client("bedrock-runtime", region_name=region)

    def invoke(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AIResponse:
        """
        Invoke the AI model.

        Args:
            prompt: User prompt
            system: System prompt
            max_tokens: Override max tokens
            temperature: Override temperature

        Returns:
            AIResponse object
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        # Build request based on model
        if self.model_name.startswith("anthropic.claude-3"):
            body = self._build_claude3_request(prompt, system, max_tokens, temperature)
        elif self.model_name.startswith("anthropic.claude"):
            body = self._build_claude2_request(prompt, system, max_tokens, temperature)
        else:
            raise ValueError(f"Unsupported model: {self.model_name}")

        # Invoke model
        try:
            response = self.client.invoke_model(
                modelId=self.model_name,
                body=json.dumps(body)
            )

            response_body = json.loads(response["body"].read())

            # Extract content based on model
            if self.model_name.startswith("anthropic.claude-3"):
                content = response_body["content"][0]["text"]
                usage = response_body.get("usage", {})
            else:
                content = response_body["completion"]
                usage = {
                    "input_tokens": response_body.get("stop_reason"),
                    "output_tokens": len(content.split())
                }

            return AIResponse(
                content=content,
                model=self.model_name,
                usage=usage,
                raw_response=response_body
            )

        except Exception as e:
            logger.error(f"Error invoking model: {e}")
            raise

    def _build_claude3_request(
        self,
        prompt: str,
        system: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Build request for Claude 3 models."""
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        if system:
            body["system"] = system

        return body

    def _build_claude2_request(
        self,
        prompt: str,
        system: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Build request for Claude 2 models."""
        full_prompt = f"\n\nHuman: {prompt}\n\nAssistant:"
        if system:
            full_prompt = f"{system}\n{full_prompt}"

        return {
            "prompt": full_prompt,
            "max_tokens_to_sample": max_tokens,
            "temperature": temperature,
            "stop_sequences": ["\n\nHuman:"]
        }

    def batch_invoke(
        self,
        prompts: List[str],
        system: Optional[str] = None
    ) -> List[AIResponse]:
        """
        Invoke model with multiple prompts.

        Args:
            prompts: List of prompts
            system: System prompt

        Returns:
            List of AIResponse objects
        """
        responses = []
        for prompt in prompts:
            try:
                response = self.invoke(prompt, system)
                responses.append(response)
            except Exception as e:
                logger.error(f"Error in batch invoke: {e}")
                # Create error response
                responses.append(AIResponse(
                    content=f"Error: {str(e)}",
                    model=self.model_name,
                    usage={},
                    raw_response={}
                ))

        return responses

    def test_connection(self) -> bool:
        """
        Test connection to Bedrock.

        Returns:
            True if connection successful
        """
        try:
            response = self.invoke("Hello", max_tokens=10)
            return bool(response.content)
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

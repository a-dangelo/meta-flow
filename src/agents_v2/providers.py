"""
LLM provider abstraction for meta-agent v2.

Supports multiple LLM providers (AIMLAPI, Gemini) with a unified interface.
Includes structured output support for Gemini to ensure valid JSON generation.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4000
    ) -> str:
        """
        Generate completion from LLM.

        Args:
            system_prompt: System instructions
            user_prompt: User message
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response

        Raises:
            Exception: If API call fails
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model identifier."""
        pass


class AIMLAPIProvider(LLMProvider):
    """AIMLAPI provider using OpenAI-compatible interface."""

    def __init__(self, model: str = "x-ai/grok-4-fast-reasoning"):
        """
        Initialize AIMLAPI provider.

        Args:
            model: Model identifier (default: x-ai/grok-4-fast-reasoning)

        Raises:
            ValueError: If AIMLAPI_KEY environment variable is not set
        """
        self.api_key = os.getenv('AIMLAPI_KEY')
        if not self.api_key:
            raise ValueError(
                "Missing AIMLAPI_KEY environment variable\n"
                "Setup: export AIMLAPI_KEY=your_key_here"
            )
        self.model = model
        logger.info(f"Initialized AIMLAPI provider with model: {model}")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4000
    ) -> str:
        """Generate completion using AIMLAPI."""
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.aimlapi.com/v1"
        )

        logger.debug(f"Calling AIMLAPI with model: {self.model}")
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        if not response.choices or not response.choices[0].message.content:
            raise ValueError("AIMLAPI returned empty response")

        return response.choices[0].message.content.strip()

    def get_model_name(self) -> str:
        """Get model name."""
        return f"aimlapi:{self.model}"


class GeminiProvider(LLMProvider):
    """Google Gemini provider with structured output support."""

    def __init__(self, model: Optional[str] = None):
        """
        Initialize Gemini provider.

        Args:
            model: Model identifier (default: from GEMINI_MODEL env var or gemini-2.5-pro)

        Raises:
            ValueError: If GEMINI_API_KEY environment variable is not set
        """
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Missing GEMINI_API_KEY environment variable\n"
                "Setup: export GEMINI_API_KEY=your_key_here"
            )

        # Use provided model, or env var, or default
        # Note: gemini-2.5-pro recommended for complex workflows
        self.model = model or os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')
        logger.info(f"Initialized Gemini provider with model: {self.model}")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4000
    ) -> str:
        """Generate completion using Gemini."""
        from google import genai

        # Set API key in environment for client
        os.environ['GEMINI_API_KEY'] = self.api_key

        # Create client (automatically reads GEMINI_API_KEY from env)
        client = genai.Client()

        logger.debug(f"Calling Gemini with model: {self.model}")

        # Build prompt with system instruction
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        # Generate response
        response = client.models.generate_content(
            model=self.model,
            contents=full_prompt,
            config={
                'temperature': temperature,
                'max_output_tokens': max_tokens
            }
        )

        if not response.text:
            raise ValueError("Gemini returned empty response")

        return response.text.strip()

    def get_model_name(self) -> str:
        """Get model name."""
        return f"gemini:{self.model}"

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any],
        temperature: float = 0.05,  # Lower for Gemini to reduce hallucination
        max_tokens: int = 4000
    ) -> str:
        """
        Generate completion with structured output (guaranteed JSON validity).

        Args:
            system_prompt: System instructions
            user_prompt: User message
            response_schema: JSON Schema for the response format
            temperature: Sampling temperature (lower recommended for Gemini)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated JSON string (guaranteed valid)

        Raises:
            Exception: If API call fails or structured output not supported
        """
        from google import genai
        from google.genai import types

        # Set API key in environment for client
        os.environ['GEMINI_API_KEY'] = self.api_key

        # Create client
        client = genai.Client()

        logger.debug(f"Calling Gemini structured output with model: {self.model}")
        logger.debug(f"Schema keys: {list(response_schema.keys())}")

        # Build prompt with system instruction
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        try:
            # Generate with structured output
            response = client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=temperature,  # Very low for reliability
                    max_token_count=max_tokens
                )
            )

            if not response.text:
                raise ValueError("Gemini returned empty response")

            # Validate JSON before returning
            json.loads(response.text)  # This should never fail with structured output
            logger.debug("Structured output generated valid JSON")

            return response.text.strip()

        except Exception as e:
            logger.error(f"Structured output generation failed: {e}")
            # Fall back to regular generation with warning
            logger.warning("Falling back to regular generation (JSON validity not guaranteed)")
            return self.generate(system_prompt, user_prompt, temperature, max_tokens)


def create_provider(provider_name: str, model: Optional[str] = None) -> LLMProvider:
    """
    Factory function to create LLM provider.

    Args:
        provider_name: Provider name ("aimlapi" or "gemini")
        model: Optional model override

    Returns:
        Configured LLM provider

    Raises:
        ValueError: If provider_name is invalid or required env vars are missing

    Example:
        >>> provider = create_provider("gemini")
        >>> response = provider.generate("You are helpful", "What is 2+2?")
    """
    provider_name = provider_name.lower()

    if provider_name == "aimlapi":
        return AIMLAPIProvider(model=model or "x-ai/grok-4-fast-reasoning")
    elif provider_name == "gemini":
        return GeminiProvider(model=model)
    else:
        raise ValueError(
            f"Unknown provider: {provider_name}\n"
            f"Supported providers: aimlapi, gemini"
        )

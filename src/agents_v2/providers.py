"""
LLM provider abstraction for meta-agent v2.

Supports multiple LLM providers (AIMLAPI, Gemini, Anthropic Claude) with a unified interface.
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

        # Initialize client once (cache it)
        from openai import OpenAI
        self._client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.aimlapi.com/v1"
        )

        logger.info(f"Initialized AIMLAPI provider with model: {model}")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4000
    ) -> str:
        """Generate completion using AIMLAPI."""
        logger.debug(f"Calling AIMLAPI with model: {self.model}")

        # Use cached client
        response = self._client.chat.completions.create(
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

        # Initialize client once (cache it)
        from google import genai
        self._client = genai.Client(api_key=self.api_key)

        logger.info(f"Initialized Gemini provider with model: {self.model}")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4000
    ) -> str:
        """Generate completion using Gemini."""
        logger.debug(f"Calling Gemini with model: {self.model}")

        # Build prompt with system instruction
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        # Generate response using cached client
        response = self._client.models.generate_content(
            model=self.model,
            contents=full_prompt,
            config={
                'temperature': temperature,
                'max_output_tokens': max_tokens
            }
        )

        if not response or not response.text:
            error_msg = "Gemini returned empty response"
            logger.error(error_msg)
            raise ValueError(error_msg)

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
        from google.genai import types

        logger.debug(f"Calling Gemini structured output with model: {self.model}")
        logger.debug(f"Schema keys: {list(response_schema.keys())}")

        # Build prompt with system instruction
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        try:
            # Generate with structured output using cached client
            # GenerateContentConfig does not support max_token_count parameter
            response = self._client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=temperature
                )
            )

            if not response or not response.text:
                error_msg = f"Gemini structured output returned empty response"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Validate JSON before returning
            try:
                json.loads(response.text)  # This should never fail with structured output
                logger.debug("Structured output generated valid JSON")
            except json.JSONDecodeError as e:
                error_msg = f"Gemini returned invalid JSON despite structured output: {e}"
                logger.error(error_msg)
                raise ValueError(error_msg) from e

            return response.text.strip()

        except Exception as e:
            logger.error(f"Structured output generation failed: {e}")
            # Don't fall back silently - raise the error so caller knows
            raise


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider with excellent JSON generation reliability."""

    def __init__(self, model: Optional[str] = None):
        """
        Initialize Claude provider.

        Args:
            model: Model identifier (default: from ANTHROPIC_MODEL env var or claude-3-5-sonnet-20241022)

        Raises:
            ValueError: If ANTHROPIC_API_KEY environment variable is not set
        """
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Missing ANTHROPIC_API_KEY environment variable\n"
                "Setup: export ANTHROPIC_API_KEY=your_key_here"
            )

        # Use provided model, or env var, or default to Haiku 4.5
        self.model = model or os.getenv('ANTHROPIC_MODEL', 'claude-haiku-4-5')

        # Initialize client once (cache it)
        try:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "anthropic package not installed\n"
                "Install: pip install anthropic"
            )

        logger.info(f"Initialized Claude provider with model: {self.model}")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4000
    ) -> str:
        """Generate completion using Claude."""
        logger.debug(f"Calling Claude with model: {self.model}")

        try:
            # Use cached client to create message
            response = self._client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            if not response.content or not response.content[0].text:
                error_msg = "Claude returned empty response"
                logger.error(error_msg)
                raise ValueError(error_msg)

            return response.content[0].text.strip()

        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise

    def get_model_name(self) -> str:
        """Get model name."""
        return f"claude:{self.model}"

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 4000,
        retry_on_invalid: bool = True
    ) -> str:
        """
        Generate JSON with Claude's natural JSON generation capability.

        Claude has excellent JSON generation without needing structured output mode.
        This method ensures the output is valid JSON, with optional retry.

        Args:
            system_prompt: System instructions
            user_prompt: User message
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            retry_on_invalid: Whether to retry once if JSON is invalid

        Returns:
            Generated JSON string (validated)

        Raises:
            ValueError: If JSON generation fails after retry
        """
        logger.debug(f"Generating JSON with Claude model: {self.model}")

        # Enhance prompts for JSON generation
        json_system = f"""{system_prompt}

IMPORTANT: You MUST respond with valid JSON only. Do not include any explanatory text, markdown formatting, or code blocks. Just the raw JSON object."""

        json_user = f"""{user_prompt}

Remember: Respond ONLY with a valid JSON object. No other text."""

        # First attempt
        response = self.generate(json_system, json_user, temperature, max_tokens)

        # Try to parse the JSON
        try:
            # Clean up common issues
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            # Validate JSON
            json.loads(cleaned)
            logger.debug("Claude generated valid JSON on first attempt")
            return cleaned

        except json.JSONDecodeError as e:
            logger.warning(f"First JSON generation attempt failed: {e}")

            if not retry_on_invalid:
                raise ValueError(f"Claude generated invalid JSON: {e}") from e

            # Retry with error feedback
            logger.debug("Retrying with error feedback")
            retry_prompt = f"""The previous JSON generation failed with error:
{str(e)}

Original request:
{user_prompt}

Please generate the correct JSON object. Remember: ONLY valid JSON, no other text."""

            retry_response = self.generate(json_system, retry_prompt, temperature, max_tokens)

            # Clean and validate retry
            cleaned_retry = retry_response.strip()
            if cleaned_retry.startswith("```json"):
                cleaned_retry = cleaned_retry[7:]
            if cleaned_retry.startswith("```"):
                cleaned_retry = cleaned_retry[3:]
            if cleaned_retry.endswith("```"):
                cleaned_retry = cleaned_retry[:-3]
            cleaned_retry = cleaned_retry.strip()

            try:
                json.loads(cleaned_retry)
                logger.debug("Claude generated valid JSON on retry")
                return cleaned_retry
            except json.JSONDecodeError as e2:
                error_msg = f"Claude failed to generate valid JSON after retry: {e2}"
                logger.error(error_msg)
                raise ValueError(error_msg) from e2


def create_provider(provider_name: str, model: Optional[str] = None) -> LLMProvider:
    """
    Factory function to create LLM provider.

    Args:
        provider_name: Provider name ("aimlapi", "gemini", or "claude")
        model: Optional model override

    Returns:
        Configured LLM provider

    Raises:
        ValueError: If provider_name is invalid or required env vars are missing

    Example:
        >>> provider = create_provider("claude")
        >>> response = provider.generate("You are helpful", "What is 2+2?")
    """
    provider_name = provider_name.lower()

    if provider_name == "aimlapi":
        return AIMLAPIProvider(model=model or "x-ai/grok-4-fast-reasoning")
    elif provider_name == "gemini":
        return GeminiProvider(model=model)
    elif provider_name in ("claude", "anthropic"):
        return ClaudeProvider(model=model)
    else:
        raise ValueError(
            f"Unknown provider: {provider_name}\n"
            f"Supported providers: aimlapi, gemini, claude (or anthropic)"
        )

"""
Claude API Handler

Handles Claude API calls with response caching for cost control.
Supports multiple Claude models and rate limiting.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import anthropic
from anthropic import RateLimitError
import logging
import json

logger = logging.getLogger(__name__)


class ClaudeHandler:
    """Handler for Claude API interactions with caching"""

    # Model name mapping
    MODEL_MAP = {
        "sonnet-4": "claude-sonnet-4-20250514",
        "opus-4.5": "claude-opus-4-5-20251101",
        "haiku": "claude-3-5-haiku-20241022",
        "claude-sonnet-4-20250514": "claude-sonnet-4-20250514",
        "claude-opus-4-5-20251101": "claude-opus-4-5-20251101",
        "claude-3-5-haiku-20241022": "claude-3-5-haiku-20241022"
    }

    def __init__(self, api_key: str, default_model: str = "sonnet-4"):
        """
        Initialize Claude API handler.

        Args:
            api_key: Anthropic API key
            default_model: Default Claude model to use
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.default_model = self._resolve_model_name(default_model)

    def _resolve_model_name(self, model_name: str) -> str:
        """
        Resolve model name to full API model identifier.

        Args:
            model_name: Short name or full model ID

        Returns:
            Full model ID
        """
        return self.MODEL_MAP.get(model_name, model_name)

    def call_api(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call Claude API and return response.

        Args:
            prompt: User prompt
            model: Claude model to use (None = default)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            system_prompt: Optional system prompt

        Returns:
            Dictionary with:
                - response: Text response from Claude
                - model: Model used
                - tokens_used: Total tokens consumed
                - input_tokens: Input tokens
                - output_tokens: Output tokens
                - timestamp: When the call was made

        Raises:
            RateLimitError: If rate limited
            Exception: For other API errors
        """
        # Resolve model name
        if model is None:
            model = self.default_model
        else:
            model = self._resolve_model_name(model)

        try:
            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Make API call
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = self.client.messages.create(**kwargs)

            # Extract response text
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text

            # Calculate tokens
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens

            result = {
                "response": response_text,
                "model": model,
                "tokens_used": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "timestamp": datetime.now().isoformat(),
                "stop_reason": response.stop_reason,
                "raw_response": {
                    "id": response.id,
                    "type": response.type,
                    "role": response.role
                }
            }

            logger.info(
                f"Claude API call successful: model={model}, "
                f"tokens={total_tokens} (in={input_tokens}, out={output_tokens})"
            )

            return result

        except RateLimitError as e:
            logger.error(f"Rate limit error: {e}")
            raise

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    def call_with_cache(
        self,
        prompt: str,
        cached_response: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Call Claude API with caching support.

        If cached_response is provided and force_refresh is False,
        return the cached response instead of making a new API call.

        Args:
            prompt: User prompt
            cached_response: Previously cached response
            model: Claude model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: Optional system prompt
            force_refresh: Force new API call even if cached

        Returns:
            API response dictionary (same as call_api)
        """
        # Return cached response if available and not forcing refresh
        if cached_response and not force_refresh:
            logger.info("Using cached Claude response (skipping API call)")
            return cached_response

        # Make fresh API call
        return self.call_api(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt
        )

    def extract_response_text(self, api_response: Dict[str, Any]) -> str:
        """
        Extract text from API response dictionary.

        Args:
            api_response: Response from call_api() or call_with_cache()

        Returns:
            Response text
        """
        return api_response.get("response", "")

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "sonnet-4"
    ) -> float:
        """
        Estimate API call cost in USD.

        Pricing as of Jan 2025 (approximate):
        - Sonnet 4: $3/MTok input, $15/MTok output
        - Opus 4.5: $15/MTok input, $75/MTok output
        - Haiku: $0.80/MTok input, $4/MTok output

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name

        Returns:
            Estimated cost in USD
        """
        model = self._resolve_model_name(model)

        # Pricing per million tokens (MTok)
        pricing = {
            "claude-sonnet-4-20250514": (3.0, 15.0),
            "claude-opus-4-5-20251101": (15.0, 75.0),
            "claude-3-5-haiku-20241022": (0.80, 4.0)
        }

        if model not in pricing:
            logger.warning(f"Unknown model for cost estimation: {model}")
            return 0.0

        input_price, output_price = pricing[model]

        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price

        return input_cost + output_cost

    def validate_model(self, model_name: str) -> bool:
        """
        Check if model name is valid.

        Args:
            model_name: Model name to validate

        Returns:
            True if valid
        """
        resolved = self._resolve_model_name(model_name)
        return resolved in self.MODEL_MAP.values()

    def test_api_connection(self) -> bool:
        """
        Test if API is accessible and not rate limited.

        Returns:
            True if API is accessible
        """
        try:
            # Simple test call with minimal tokens
            self.call_api(
                prompt="Hello",
                model="haiku",
                max_tokens=10,
                temperature=0
            )
            return True

        except RateLimitError:
            logger.warning("API is rate limited")
            return False

        except Exception as e:
            logger.error(f"API test failed: {e}")
            return False

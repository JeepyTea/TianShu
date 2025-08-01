import os
from typing import List, Dict, Any
from .base_http_client import BaseHttpLLMClient
from tianshu_core.config import Config

# Default model to use if not specified in config or environment variable
_DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"


class OpenRouterClient(BaseHttpLLMClient):
    """
    LLM client for OpenRouter API, compatible with OpenAI's Chat Completions format.
    """

    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, local_config: dict):
        """
        Initialize the OpenRouter client.

        Args:
            config: A dictionary containing configuration like:
                    'api_key': (Required) Your OpenRouter API key. Can also be set via
                               OPENROUTER_API_KEY environment variable.
                    'model': (Required) The model identifier to use (e.g., "anthropic/claude-3.5-sonnet").
                    'base_url': (Optional) The API endpoint URL (defaults to OpenRouter's v1 API).
                    'timeout': (Optional) Request timeout in seconds (default: 120).
                    'headers': (Optional) Additional custom headers dictionary.
                    'site_url': (Optional) Your site URL for OpenRouter analytics.
                    'site_name': (Optional) Your site name for OpenRouter analytics.
        """
        # Prioritize config value, then env var, then default for base_url
        local_config.setdefault(
            "base_url", os.environ.get("OPENROUTER_BASE_URL", self.DEFAULT_BASE_URL)
        )
        # Prioritize config value, then env var, then the hardcoded default for api_key
        local_config.setdefault("api_key", Config.OPENROUTER_API_KEY)
        # Prioritize config value, then env var, then the hardcoded default for model
        local_config.setdefault("model", os.environ.get("OPENROUTER_MODEL", _DEFAULT_MODEL))

        super().__init__(local_config)

        self.api_key = self.config.get("api_key")
        # Check if the resolved API key is the placeholder
        if self.api_key == "YOUR_API_KEY_HERE":
            # If it's still the placeholder, treat it as missing for validation/header purposes
            self.api_key = None
        self.model = self.config.get("model")

        # Add authorization header if API key is provided
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            # Validation will catch this, but good practice
            print("Warning: OpenRouter API key not provided in config or OPENROUTER_API_KEY env var.")

        # Add OpenRouter-specific headers for analytics if provided
        site_url = self.config.get("site_url")
        site_name = self.config.get("site_name")
        if site_url:
            self.headers["HTTP-Referer"] = site_url
        if site_name:
            self.headers["X-Title"] = site_name

    def _validate_config(self):
        """Validate required configuration."""
        # Check if api_key is set either in config, env, or the (modified) constant
        resolved_api_key = self.config.get(
            "api_key"
        )  # Already incorporates env/constant via __init__
        if not resolved_api_key or resolved_api_key == "YOUR_API_KEY_HERE":
            raise ValueError(
                "OpenRouter API key is not configured. Provide it via 'api_key' in config, "
                "the OPENROUTER_API_KEY environment variable, or by replacing the "
                "placeholder in Config.OPENROUTER_API_KEY."
            )
        # Model should always be resolved by __init__ (config, env, or default constant)
        if not self.config.get("model"):
            # This case should theoretically not be reachable if __init__ logic is correct
            raise ValueError("Model configuration is missing.")
        if not self.config.get("base_url"):
            # Should have been set by default, but check anyway
            raise ValueError("Configuration must include 'base_url'")

    def _extract_response(self, response_data: dict) -> str:
        """Extracts the response text from the JSON data (OpenAI format)."""
        try:
            # Following OpenAI structure: choices -> 0 -> message -> content
            content = response_data["choices"][0]["message"]["content"]
            if isinstance(content, str):
                return content
            else:
                raise ValueError(f"Expected string content, but got {type(content)}")
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(
                f"Could not extract response using standard OpenAI path ('choices[0].message.content'): {e}. Response keys: {list(response_data.keys())}"
            ) from e

    def send_chat(self, messages: List[Dict[str, Any]], num_retries: int = 0, **kwargs) -> str:
        """
        Sends a chat completion request to the OpenRouter API.

        Args:
            messages: A list of message dictionaries, e.g.,
                      [{"role": "user", "content": "Hello!"},
                       {"role": "assistant", "content": "Hi there!"}]
                      or including image URLs:
                      [{"role":"user", "content": [
                          {"type": "text", "text": "What's in this image?"},
                          {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
                      ]}]
            num_retries: Number of times to retry on network failures or timeouts.
            **kwargs: Additional parameters for the API call (e.g., temperature, top_p, max_tokens).

        Returns:
            The response text from the LLM assistant.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails after all retries.
            ValueError: If the response format is unexpected or configuration is invalid.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs,
        }

        # Make the HTTP request with retry logic
        endpoint = self._get_endpoint("chat/completions")
        response_data = self._make_http_request(endpoint, payload, num_retries=num_retries)

        # Extract and return the response
        return self._extract_response(response_data)

    def send_prompt(self, prompt: str, num_retries: int = 0, **kwargs) -> str:
        """
        Sends a simple text prompt as a single user message using the chat completion endpoint.

        Args:
            prompt: The text prompt to send.
            num_retries: Number of times to retry on network failures or timeouts.
            **kwargs: Additional parameters for the API call (e.g., temperature, top_p, max_tokens).

        Returns:
            The response text from the LLM assistant.
        """
        # Handle system prompt if provided
        system_prompt = kwargs.pop("system_prompt", None)

        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self.send_chat(messages=messages, num_retries=num_retries, **kwargs)

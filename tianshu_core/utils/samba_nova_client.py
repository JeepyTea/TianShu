import os
from typing import List, Dict, Any
from .base_http_client import BaseHttpLLMClient
from tianshu_core.config import Config

# --- WARNING ---
# Hardcoding API keys is insecure. Prefer environment variables (SAMBANOVA_API_KEY)
# or a secure configuration method over modifying this constant.
_DEFAULT_API_KEY = os.environ.get("SAMBANOVA_API_KEY", "")

# Default model to use if not specified in config or environment variable
_DEFAULT_MODEL = "DeepSeek-R1-Distill-Llama-70B"


class SambaNovaClient(BaseHttpLLMClient):
    """
    LLM client for SambaNova API, compatible with OpenAI's Chat Completions format.
    """

    DEFAULT_BASE_URL = "https://api.sambanova.ai/v1"

    def __init__(self, local_config: dict):
        """
        Initialize the SambaNova client.

        Args:
            config: A dictionary containing configuration like:
                    'api_key': (Required) Your SambaNova API key. Can also be set via
                               SAMBANOVA_API_KEY environment variable.
                    'model': (Required) The model identifier to use (e.g., "Llama-4-Maverick-17B-128E-Instruct").
                    'base_url': (Optional) The API endpoint URL (defaults to SambaNova's v1 API).
                    'timeout': (Optional) Request timeout in seconds (default: 120).
                    'headers': (Optional) Additional custom headers dictionary.
        """
        # Prioritize config value, then env var, then default for base_url
        local_config.setdefault(
            "base_url", os.environ.get("SAMBANOVA_BASE_URL", self.DEFAULT_BASE_URL)
        )
        # Prioritize config value, then env var, then the hardcoded default for api_key
        local_config.setdefault("api_key", Config.SAMBANOVA_API_KEY)
        # Prioritize config value, then env var, then the hardcoded default for model
        local_config.setdefault("model", os.environ.get("SAMBANOVA_MODEL", _DEFAULT_MODEL))

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
            print("Warning: SambaNova API key not provided in config or SAMBANOVA_API_KEY env var.")

    def _validate_config(self):
        """Validate required configuration."""
        # Check if api_key is set either in config, env, or the (modified) constant
        resolved_api_key = self.config.get(
            "api_key"
        )  # Already incorporates env/constant via __init__
        if not resolved_api_key or resolved_api_key == "YOUR_API_KEY_HERE":
            raise ValueError(
                "SambaNova API key is not configured. Provide it via 'api_key' in config, "
                "the SAMBANOVA_API_KEY environment variable, or by replacing the "
                "placeholder in _DEFAULT_API_KEY within samba_nova_client.py."
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
        Sends a chat completion request to the SambaNova API.

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

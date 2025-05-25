import os
from typing import List, Dict
from .base_http_client import BaseHttpLLMClient
from tianshu_core.config import Config

# Default model to use if not specified in config or environment variable
_DEFAULT_MODEL = "deepseek-ai/DeepSeek-R1"


class ChutesClient(BaseHttpLLMClient):
    """
    LLM client for Chutes API, compatible with the BaseLLMClient interface.
    """

    DEFAULT_BASE_URL = "https://llm.chutes.ai/v1"

    def __init__(self, local_config: dict):
        """
        Initialize the Chutes client.

        Args:
            config: A dictionary containing configuration like:
                    'api_token': (Required) Your Chutes API token. Can also be set via
                                CHUTES_API_KEY environment variable.
                    'model': (Optional) The model identifier to use (defaults to DeepSeek-R1).
                    'base_url': (Optional) The API endpoint URL (defaults to Chutes API endpoint).
                    'timeout': (Optional) Request timeout in seconds (default: 120).
                    'headers': (Optional) Additional custom headers dictionary.
        """
        # Prioritize config value, then env var, then default for base_url
        local_config.setdefault(
            "base_url", os.environ.get("CHUTES_BASE_URL", self.DEFAULT_BASE_URL)
        )
        # Prioritize config value, then env var, then the hardcoded default for model
        local_config.setdefault("model", os.environ.get("CHUTES_MODEL", _DEFAULT_MODEL))
        local_config.setdefault("api_token", Config.CHUTES_API_KEY)

        super().__init__(local_config)

        self.api_token = self.config.get("api_token")
        self.model = self.config.get("model")

        # Add authorization header if token is provided
        if self.api_token:
            self.headers["Authorization"] = f"Bearer {self.api_token}"

    def _validate_config(self):
        """Validate required configuration."""
        if not self.config.get("api_token"):
            raise ValueError(
                "Chutes API token is not configured. Provide it via 'api_token' in config "
                "or the CHUTES_API_KEY environment variable."
            )
        if not self.config.get("model"):
            raise ValueError("Model configuration is missing.")
        if not self.config.get("base_url"):
            raise ValueError("Configuration must include 'base_url'")

    def send_prompt(self, prompt: str, num_retries: int = 0, **kwargs) -> str:
        """
        Sends a prompt to the Chutes API and returns the response.

        Args:
            prompt: The text prompt to send.
            num_retries: Number of times to retry on network failures or timeouts.
            **kwargs: Additional parameters for the API call (e.g., temperature, top_p, max_tokens).

        Returns:
            The response text from the LLM.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails after all retries.
            ValueError: If the response format is unexpected or configuration is invalid.
        """
        # Handle system prompt if provided
        system_prompt = kwargs.pop("system_prompt", None)

        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Map common parameters to Chutes's expected format
        chutes_params = {
            "model": self.model,
            "messages": messages,
            # Map common parameters with appropriate defaults
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 50000),
            "stream": False,  # We want the complete response, not streaming
        }

        # Add top_p if provided
        if "top_p" in kwargs:
            chutes_params["top_p"] = kwargs["top_p"]

        # Add any additional parameters from kwargs that match Chutes's API
        for key, value in kwargs.items():
            if key not in chutes_params and key not in [
                "temperature",
                "top_p",
                "max_tokens",
                "system_prompt",
            ]:
                chutes_params[key] = value

        # Make the HTTP request with retry logic
        endpoint = self._get_endpoint("chat/completions")
        response_data = self._make_http_request(endpoint, chutes_params, num_retries=num_retries)

        # Extract the response content from the completion
        try:
            return response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ValueError(
                f"Could not extract response from Chutes API: {e}. Response keys: {list(response_data.keys())}"
            ) from e

    def send_chat(self, messages: List[Dict[str, str]], num_retries: int = 0, **kwargs) -> str:
        """
        Sends a conversation history to the Chutes API and returns the response.

        Args:
            messages: A list of message dictionaries with 'role' and 'content' keys.
            num_retries: Number of times to retry on network failures or timeouts.
            **kwargs: Additional parameters for the API call.

        Returns:
            The response text from the LLM.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails after all retries.
            ValueError: If the response format is unexpected or configuration is invalid.
        """
        # Prepare the request payload
        chutes_params = {
            "model": self.model,
            "messages": messages,
            # Map common parameters with appropriate defaults
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 30000),
            "stream": False,  # We want the complete response, not streaming
        }

        # Add top_p if provided
        if "top_p" in kwargs:
            chutes_params["top_p"] = kwargs["top_p"]

        # Add any additional parameters from kwargs
        for key, value in kwargs.items():
            if key not in chutes_params and key not in ["temperature", "top_p", "max_tokens"]:
                chutes_params[key] = value

        # Make the HTTP request with retry logic
        endpoint = self._get_endpoint("chat/completions")
        response_data = self._make_http_request(endpoint, chutes_params, num_retries=num_retries)

        # Extract the response content from the completion
        try:
            return response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ValueError(
                f"Could not extract response from Chutes API: {e}. Response keys: {list(response_data.keys())}"
            ) from e

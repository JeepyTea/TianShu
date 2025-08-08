import os
from typing import List, Dict, Any
from .base_http_client import BaseHttpLLMClient
from tianshu_core.config import Config

# Default model to use if not specified in config or environment variable
_DEFAULT_MODEL = "gpt-4o"


class OpenAIClient(BaseHttpLLMClient):
    """
    LLM client for OpenAI API, compatible with the BaseLLMClient interface.
    """

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_TIMEOUT = 360

    def __init__(self, local_config: dict):
        """
        Initialize the OpenAI client.

        Args:
            config: A dictionary containing configuration like:
                    'api_token': (Required) Your OpenAI API token. Can also be set via
                                OPENAI_API_KEY environment variable.
                    'model': (Optional) The model identifier to use (defaults to gpt-4o).
                    'base_url': (Optional) The API endpoint URL (defaults to OpenAI API endpoint).
                    'timeout': (Optional) Request timeout in seconds (default: 360).
                    'headers': (Optional) Additional custom headers dictionary.
                    'temperature': (Optional) Temperature setting for the model (default: 0.7).
                    'max_tokens': (Optional) Maximum number of tokens to generate (default: 4096).
                    'top_p': (Optional) Top-p sampling parameter (default: 1.0).
                    'frequency_penalty': (Optional) Frequency penalty (default: 0.0).
                    'presence_penalty': (Optional) Presence penalty (default: 0.0).
                    'response_format': (Optional) Dictionary for response format, e.g., {"type": "json_object"}.
        """
        # Prioritize config value, then env var, then default for base_url
        local_config.setdefault(
            "base_url", os.environ.get("OPENAI_BASE_URL", self.DEFAULT_BASE_URL)
        )
        # Prioritize config value, then env var, then the hardcoded default for model
        local_config.setdefault("model", os.environ.get("OPENAI_MODEL", _DEFAULT_MODEL))
        local_config.setdefault("api_token", Config.OPENAI_API_KEY)
        # Set default timeout
        local_config.setdefault("timeout", self.DEFAULT_TIMEOUT)

        # Set default generation parameters
        local_config.setdefault("temperature", 0.7)
        local_config.setdefault("max_tokens", 4096)
        local_config.setdefault("top_p", 1.0)
        local_config.setdefault("frequency_penalty", 0.0)
        local_config.setdefault("presence_penalty", 0.0)
        
        # Store response_format if provided in config
        self.response_format = local_config.pop("response_format", None)

        super().__init__(local_config)

        self.api_token = self.config.get("api_token")
        self.model = self.config.get("model")
        self.temperature = self.config.get("temperature")
        self.max_tokens = self.config.get("max_tokens")
        self.top_p = self.config.get("top_p")
        self.frequency_penalty = self.config.get("frequency_penalty")
        self.presence_penalty = self.config.get("presence_penalty")

        # Add authorization header if token is provided
        if self.api_token:
            self.headers["Authorization"] = f"Bearer {self.api_token}"
        self.headers["OpenAI-Beta"] = "assistants=v2" # For potential future use with assistants API

    def _validate_config(self):
        """Validate required configuration."""
        if not self.config.get("api_token"):
            raise ValueError(
                "OpenAI API token is not configured. Provide it via 'api_token' in config "
                "or the OPENAI_API_KEY environment variable."
            )
        if not self.config.get("model"):
            raise ValueError("Model configuration is missing.")
        if not self.config.get("base_url"):
            raise ValueError("Configuration must include 'base_url'")

    def _extract_response(self, response_data: dict) -> str:
        """Extracts the response text from the OpenAI API JSON data."""
        try:
            return response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ValueError(
                f"Could not extract response from OpenAI API: {e}. Response keys: {list(response_data.keys())}"
            ) from e

    def send_prompt(self, prompt: str, num_retries: int = 0, **kwargs) -> str:
        """
        Sends a prompt to the OpenAI API and returns the response.

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

        # Delegate to send_chat for consistency
        return self.send_chat(messages, num_retries=num_retries, **kwargs)

    def send_chat(self, messages: List[Dict[str, str]], num_retries: int = 0, **kwargs) -> str:
        """
        Sends a conversation history to the OpenAI API and returns the response.

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
        openai_params = {
            "model": self.model,
            "messages": messages,
            # Use configured parameters if not overridden in kwargs
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "top_p": kwargs.get("top_p", self.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
            "presence_penalty": kwargs.get("presence_penalty", self.presence_penalty),
            "stream": False,  # We want the complete response, not streaming
        }

        # Add response_format if specified
        if kwargs.get("response_format", self.response_format):
            openai_params["response_format"] = kwargs.get("response_format", self.response_format)

        # Add any additional parameters from kwargs that match OpenAI's API
        for key, value in kwargs.items():
            if key not in openai_params and key not in [
                "temperature",
                "max_tokens",
                "top_p",
                "frequency_penalty",
                "presence_penalty",
                "response_format",
            ]:
                openai_params[key] = value

        # Make the HTTP request with retry logic
        endpoint = self._get_endpoint("chat/completions")
        response_data = self._make_http_request(endpoint, openai_params, num_retries=num_retries)

        # Extract the response content from the completion
        return self._extract_response(response_data)

import os
from typing import List, Dict, Any
from .base_http_client import BaseHttpLLMClient
from tianshu_core.config import Config

# Default model to use if not specified in config or environment variable
_DEFAULT_MODEL = "claude-3-5-sonnet-20241022"


class AnthropicClient(BaseHttpLLMClient):
    """
    LLM client for Anthropic Claude API, compatible with the BaseLLMClient interface.
    """

    DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_TIMEOUT = 120

    def __init__(self, local_config: dict):
        """
        Initialize the Anthropic client.

        Args:
            config: A dictionary containing configuration like:
                    'api_token': (Required) Your Anthropic API token. Can also be set via
                                ANTHROPIC_API_KEY environment variable.
                    'model': (Optional) The model identifier to use (defaults to claude-3-5-sonnet-20241022).
                    'base_url': (Optional) The API endpoint URL (defaults to Anthropic API endpoint).
                    'timeout': (Optional) Request timeout in seconds (default: 120).
                    'headers': (Optional) Additional custom headers dictionary.
                    'temperature': (Optional) Temperature setting for the model (default: 0.7).
                    'max_tokens': (Optional) Maximum number of tokens to generate (default: 4096).
                    'top_p': (Optional) Top-p sampling parameter (default: 1.0).
        """
        # Prioritize config value, then env var, then default for base_url
        local_config.setdefault(
            "base_url", os.environ.get("ANTHROPIC_BASE_URL", self.DEFAULT_BASE_URL)
        )
        # Prioritize config value, then env var, then the hardcoded default for model
        local_config.setdefault("model", os.environ.get("ANTHROPIC_MODEL", _DEFAULT_MODEL))
        local_config.setdefault("api_token", Config.ANTHROPIC_API_KEY)
        # Set default timeout
        local_config.setdefault("timeout", self.DEFAULT_TIMEOUT)

        # Set default generation parameters
        local_config.setdefault("temperature", 0.7)
        local_config.setdefault("max_tokens", 4096)
        local_config.setdefault("top_p", 1.0)

        super().__init__(local_config)

        self.api_token = self.config.get("api_token")
        self.model = self.config.get("model")
        self.temperature = self.config.get("temperature")
        self.max_tokens = self.config.get("max_tokens")
        self.top_p = self.config.get("top_p")

        # Add required Anthropic headers
        if self.api_token:
            self.headers["x-api-key"] = self.api_token
        self.headers["anthropic-version"] = "2023-06-01"

    def _validate_config(self):
        """Validate required configuration."""
        if not self.config.get("api_token"):
            raise ValueError(
                "Anthropic API token is not configured. Provide it via 'api_token' in config "
                "or the ANTHROPIC_API_KEY environment variable."
            )
        if not self.config.get("model"):
            raise ValueError("Model configuration is missing.")
        if not self.config.get("base_url"):
            raise ValueError("Configuration must include 'base_url'")

    def _extract_response(self, response_data: dict) -> str:
        """Extracts the response text from the Anthropic API JSON data."""
        try:
            # Anthropic API response format
            return response_data["content"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(
                f"Could not extract response from Anthropic API: {e}. Response keys: {list(response_data.keys())}"
            ) from e

    def _convert_messages_to_anthropic_format(self, messages: List[Dict[str, str]]) -> tuple:
        """
        Converts OpenAI-style messages to Anthropic format.
        
        Returns:
            tuple: (system_prompt, anthropic_messages)
        """
        system_prompt = None
        anthropic_messages = []
        
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                # Anthropic handles system prompts separately
                system_prompt = content
            elif role in ["user", "assistant"]:
                anthropic_messages.append({
                    "role": role,
                    "content": content
                })
            else:
                # Convert other roles to user for compatibility
                anthropic_messages.append({
                    "role": "user",
                    "content": content
                })
        
        return system_prompt, anthropic_messages

    def send_prompt(self, prompt: str, num_retries: int = 0, **kwargs) -> str:
        """
        Sends a prompt to the Anthropic API and returns the response.

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
        Sends a conversation history to the Anthropic API and returns the response.

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
        # Convert messages to Anthropic format
        system_prompt, anthropic_messages = self._convert_messages_to_anthropic_format(messages)

        # Prepare the request payload
        anthropic_params = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            # Use configured parameters if not overridden in kwargs
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
        }

        # Add system prompt if present
        if system_prompt:
            anthropic_params["system"] = system_prompt

        # Add any additional parameters from kwargs that match Anthropic's API
        for key, value in kwargs.items():
            if key not in anthropic_params and key not in [
                "temperature",
                "max_tokens",
                "top_p",
                "system_prompt",
            ]:
                anthropic_params[key] = value

        # Make the HTTP request with retry logic
        endpoint = self._get_endpoint("messages")
        response_data = self._make_http_request(endpoint, anthropic_params, num_retries=num_retries)

        # Extract the response content from the completion
        return self._extract_response(response_data)

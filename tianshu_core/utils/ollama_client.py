import os
from typing import List, Dict
from .base_http_client import BaseHttpLLMClient
from tianshu_core.config import Config

# Default model to use if not specified in config or environment variable
_DEFAULT_MODEL = "llama3"


class OllamaClient(BaseHttpLLMClient):
    """
    LLM client for Ollama API, compatible with the BaseLLMClient interface.
    """

    DEFAULT_BASE_URL = "http://192.168.1.99:11434"
    DEFAULT_TIMEOUT = 180

    def __init__(self, local_config: dict):
        """
        Initialize the Ollama client.

        Args:
            config: A dictionary containing configuration like:
                    'model': (Required) The model identifier to use (e.g., "llama3", "mistral").
                    'base_url': (Optional) The API endpoint URL (defaults to Ollama's local endpoint).
                    'timeout': (Optional) Request timeout in seconds (default: 360).
                    'headers': (Optional) Additional custom headers dictionary.
        """
        # Prioritize config value, then env var, then default for base_url
        local_config.setdefault("base_url", Config.OLLAMA_BASE_URL)
        # Prioritize config value, then env var, then the hardcoded default for model
        local_config.setdefault("model", os.environ.get("OLLAMA_MODEL", _DEFAULT_MODEL))
        # Set default timeout
        local_config.setdefault("timeout", self.DEFAULT_TIMEOUT)

        super().__init__(local_config)
        self.model = self.config.get("model")

    def _validate_config(self):
        """Validate required configuration."""
        # Model should always be resolved by __init__ (config, env, or default constant)
        if not self.config.get("model"):
            # This case should theoretically not be reachable if __init__ logic is correct
            raise ValueError("Model configuration is missing.")
        if not self.config.get("base_url"):
            # Should have been set by default, but check anyway
            raise ValueError("Configuration must include 'base_url'. Set OLLAMA_BASE_URL in your environment or .env.")

    def _extract_generate_response(self, response_data: dict) -> str:
        """Extracts the response text from the generate API JSON data."""
        try:
            # Ollama API returns the response in the 'response' field
            content = response_data.get("response")
            if isinstance(content, str):
                return content
            else:
                raise ValueError(f"Expected string content, but got {type(content)}")
        except (KeyError, TypeError) as e:
            raise ValueError(
                f"Could not extract response from Ollama API: {e}. Response keys: {list(response_data.keys())}"
            ) from e

    def _extract_chat_response(self, response_data: dict) -> str:
        """Extracts the response text from the chat API JSON data."""
        try:
            # The chat API returns a message object with content
            return response_data["message"]["content"]
        except (KeyError, TypeError) as e:
            raise ValueError(
                f"Could not extract response from Ollama Chat API: {e}. Response keys: {list(response_data.keys())}"
            ) from e

    def send_prompt(self, prompt: str, num_retries: int = 0, **kwargs) -> str:
        """
        Sends a prompt to the Ollama API and returns the response.

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
        if system_prompt:
            # If system prompt is provided, use it in the prompt format that Ollama expects
            formatted_prompt = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{prompt} [/INST]"
        else:
            formatted_prompt = prompt

        # Map common parameters to Ollama's expected format
        ollama_params = {
            "model": self.model,
            "prompt": formatted_prompt,
            # Map common parameters with appropriate defaults
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
            "num_predict": kwargs.get("max_tokens", 2048),
            # Add any other parameters that Ollama supports
            "stream": False,  # We want the complete response, not streaming
        }

        # Add options from config if present
        if "options" in self.config:
            ollama_params["options"] = self.config.get("options", {})

        # Add any additional parameters from kwargs that match Ollama's API
        for key, value in kwargs.items():
            if key not in ollama_params and key not in [
                "temperature",
                "top_p",
                "max_tokens",
                "system_prompt",
            ]:
                ollama_params[key] = value

        # Make the HTTP request with retry logic
        endpoint = self._get_endpoint("api/generate")
        response_data = self._make_http_request(endpoint, ollama_params, num_retries=num_retries)

        # Extract and return the response
        return self._extract_generate_response(response_data)

    def send_chat(self, messages: List[Dict[str, str]], num_retries: int = 0, **kwargs) -> str:
        """
        Sends a conversation history to the Ollama API and returns the response.

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
        # Extract system message if present
        system_message = None
        chat_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append({"role": msg["role"], "content": msg["content"]})

        # Prepare the request payload
        ollama_params = {
            "model": self.model,
            "messages": chat_messages,
            # Map common parameters with appropriate defaults
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
            "num_predict": kwargs.get("max_tokens", 2048),
            "stream": False,  # We want the complete response, not streaming
        }

        # Add system message if present
        if system_message:
            ollama_params["system"] = system_message

        # Add options from config if present
        if "options" in self.config:
            ollama_params["options"] = self.config.get("options", {})

        # Add any additional parameters from kwargs
        for key, value in kwargs.items():
            if key not in ollama_params and key not in ["temperature", "top_p", "max_tokens"]:
                ollama_params[key] = value

        # Make the HTTP request with retry logic
        endpoint = self._get_endpoint("api/chat")
        response_data = self._make_http_request(endpoint, ollama_params, num_retries=num_retries)

        # Extract and return the response
        return self._extract_chat_response(response_data)

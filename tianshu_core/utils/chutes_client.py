import os
import logging
import time
from typing import List, Dict, Any
from .base_http_client import BaseHttpLLMClient
from tianshu_core.config import Config

# Default model to use if not specified in config or environment variable
_DEFAULT_MODEL = "deepseek-ai/DeepSeek-R1"

# Configure logging (consider moving this to a central configuration if your project has one)
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')


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
                    'temperature': (Optional) Temperature setting for the model.
                    'context_length': (Optional) Maximum context length for the model.
        """
        # Prioritize config value, then env var, then default for base_url
        local_config.setdefault(
            "base_url", os.environ.get("CHUTES_BASE_URL", self.DEFAULT_BASE_URL)
        )
        # Prioritize config value, then env var, then the hardcoded default for model
        local_config.setdefault("model", os.environ.get("CHUTES_MODEL", _DEFAULT_MODEL))
        local_config.setdefault("api_token", Config.CHUTES_API_KEY)
        
        # Set default temperature and context length if not provided
        local_config.setdefault("temperature", 0.7)
        local_config.setdefault("context_length", 32000)

        super().__init__(local_config)

        self.api_token = self.config.get("api_token")
        self.model = self.config.get("model")
        self.temperature = self.config.get("temperature")
        self.context_length = self.config.get("context_length")

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
            # Use configured temperature if not overridden in kwargs
            "temperature": kwargs.get("temperature", self.temperature),
            # Use configured context length for max_tokens if not overridden
            "max_tokens": kwargs.get("max_tokens", self.context_length),
            "stream": False,  # We want the complete response, not streaming
        }

        # Add top_p if provided
        if "top_p" in kwargs:
            chutes_params["top_p"] = kwargs["top_p"] # Corrected from chutes_params["top_p"] = chutes_params["top_p"]

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
            num_retries: Number of times to retry on network failures or timeouts
                         within the HTTP request itself. Defaults to 0 (1 attempt).
            **kwargs: Additional parameters for the API call.

        Returns:
            The response text from the LLM.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails after all network retries.
            ValueError: If the response format is unexpected after all parsing retries.
        """
        # Constant for parsing retries
        MAX_PARSING_RETRIES = 3

        # Prepare the request payload
        chutes_params = {
            "model": self.model,
            "messages": messages,
            # Use configured temperature if not overridden in kwargs
            "temperature": kwargs.get("temperature", self.temperature),
            # Use configured context length for max_tokens if not overridden
            "max_tokens": kwargs.get("max_tokens", self.context_length),
            "stream": False,  # We want the complete response, not streaming
        }

        # Add top_p if provided
        if "top_p" in kwargs:
            chutes_params["top_p"] = kwargs["top_p"]

        # Add any additional parameters from kwargs
        for key, value in kwargs.items():
            if key not in chutes_params and key not in ["temperature", "top_p", "max_tokens"]:
                chutes_params[key] = value

        endpoint = self._get_endpoint("chat/completions")

        # Loop for retries specifically for response parsing errors
        for attempt in range(MAX_PARSING_RETRIES + 1):
            response_data: Dict[str, Any] = {} # Initialize to ensure it's always defined
            try:
                # _make_http_request handles its own network retries based on 'num_retries' parameter
                response_data = self._make_http_request(endpoint, chutes_params, num_retries=num_retries)

                # Attempt to extract the response content from the completion
                return response_data["choices"][0]["message"]["content"]

            except (KeyError, IndexError) as e:
                # This block handles the specific ValueError (from KeyError/IndexError)
                # when the response structure is unexpected.
                log_message = (
                    f"Parsing error (attempt {attempt + 1}/{MAX_PARSING_RETRIES + 1}): Could not extract response from Chutes API: {e}. "
                    f"Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'N/A'}\n"
                    f"response_data: {response_data}"
                )
                logging.warning(log_message)

                if attempt < MAX_PARSING_RETRIES:
                    # If there are parsing retries left, wait and then continue to the next attempt
                    time.sleep(1) # Simple linear backoff to avoid overwhelming the API
                    continue
                else:
                    # No parsing retries left, re-raise the ValueError
                    raise ValueError(
                        f"ECC001 Could not extract response from Chutes API after {MAX_PARSING_RETRIES + 1} parsing attempts: {e}. "
                        f"Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'N/A'}\n"
                        f"response_data: {response_data}"
                    ) from e
            except Exception as e:
                # This block catches any other exceptions that might occur,
                # e.g., network errors from _make_http_request if it raises directly
                # after exhausting its own 'num_retries', or other unexpected runtime issues.
                # These are not parsing errors, so we re-raise immediately as _make_http_request
                # should have handled its retries for network issues.
                logging.error(f"An unexpected error occurred during Chutes API call: {e}")
                raise # Re-raises the caught exception

        # This line should theoretically not be reached if the loop either returns or raises an exception.
        raise RuntimeError("send_chat retry loop completed without returning or raising an exception.")

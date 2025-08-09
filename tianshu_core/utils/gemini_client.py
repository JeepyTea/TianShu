import os
from typing import List, Dict, Any
from .base_http_client import BaseHttpLLMClient
from tianshu_core.config import Config

# Default model to use if not specified in config or environment variable
_DEFAULT_MODEL = "gemini-pro"


class GeminiClient(BaseHttpLLMClient):
    """
    LLM client for Google Gemini API, compatible with the BaseLLMClient interface.
    """

    DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    DEFAULT_TIMEOUT = 360

    def __init__(self, local_config: dict):
        """
        Initialize the Gemini client.

        Args:
            config: A dictionary containing configuration like:
                    'api_token': (Required) Your Google API token. Can also be set via
                                GEMINI_API_KEY environment variable.
                    'model': (Optional) The model identifier to use (defaults to gemini-pro).
                    'base_url': (Optional) The API endpoint URL (defaults to Google Gemini API endpoint).
                    'timeout': (Optional) Request timeout in seconds (default: 360).
                    'headers': (Optional) Additional custom headers dictionary.
                    'temperature': (Optional) Temperature setting for the model.
                    'max_tokens': (Optional) Maximum number of tokens to generate.
                    'top_p': (Optional) Top-p sampling parameter.
                    'top_k': (Optional) Top-k sampling parameter.
                    'extra_body': (Optional) Dictionary of additional parameters to include in the request body.
        """
        # Prioritize config value, then env var, then default for base_url
        local_config.setdefault(
            "base_url", os.environ.get("GEMINI_BASE_URL", self.DEFAULT_BASE_URL)
        )
        # Prioritize config value, then env var, then the hardcoded default for model
        local_config.setdefault("model", os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL))
        local_config.setdefault("api_token", Config.GEMINI_API_KEY)
        # Set default timeout
        local_config.setdefault("timeout", self.DEFAULT_TIMEOUT)

        # Set default generation parameters

        # Store extra_body if provided in config
        self.extra_body = local_config.pop("extra_body", None)

        super().__init__(local_config)

        self.api_token = self.config.get("api_token")
        self.model = self.config.get("model")
        self.temperature = self.config.get("temperature")
        self.max_output_tokens = self.config.get("max_tokens")
        self.top_p = self.config.get("top_p")
        self.top_k = self.config.get("top_k")

        # Gemini API key is typically passed as a query parameter or x-goog-api-key header
        # Using x-goog-api-key header for consistency with other API key headers
        if self.api_token:
            self.headers["x-goog-api-key"] = self.api_token

    def _validate_config(self):
        """Validate required configuration."""
        if not self.config.get("api_token"):
            raise ValueError(
                "Gemini API token is not configured. Provide it via 'api_token' in config "
                "or the GEMINI_API_KEY environment variable."
            )
        if not self.config.get("model"):
            raise ValueError("Model configuration is missing.")
        if not self.config.get("base_url"):
            raise ValueError("Configuration must include 'base_url'")

    def _extract_response(self, response_data: dict) -> str:
        """Extracts the response text from the Gemini API JSON data."""
        try:
            # Gemini responses have 'candidates' which is a list
            # We take the first candidate's content, then its parts, then the text of the first part
            return response_data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(
                f"Could not extract response from Gemini API: {e}. Response keys: {list(response_data.keys())}"
            ) from e

    def _convert_messages_to_gemini_format(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Converts OpenAI-style messages to Gemini's 'contents' format.
        Handles system messages by prepending them to the first user message.
        """
        gemini_messages = []
        system_prompt_content = []

        for message in messages:
            role = message["role"]
            content = message["content"]

            if role == "system":
                system_prompt_content.append(content)
            elif role == "user":
                # If there's a system prompt, prepend it to the first user message
                if system_prompt_content:
                    full_content = "\n".join(system_prompt_content + [content])
                    gemini_messages.append({"role": "user", "parts": [{"text": full_content}]})
                    system_prompt_content = []  # Clear system prompt after use
                else:
                    gemini_messages.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                # Gemini uses 'model' role for its responses
                gemini_messages.append({"role": "model", "parts": [{"text": content}]})
            else:
                # For any other unexpected role, treat as user
                gemini_messages.append({"role": "user", "parts": [{"text": content}]})

        # If there's a system prompt but no user message, create a user message with just the system prompt
        if system_prompt_content and not any(m.get('role') == 'user' for m in gemini_messages):
            gemini_messages.insert(0, {"role": "user", "parts": [{"text": "\n".join(system_prompt_content)}]})

        return gemini_messages

    def send_prompt(self, prompt: str, num_retries: int = 0, **kwargs) -> str:
        """
        Sends a prompt to the Gemini API and returns the response.

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
        Sends a conversation history to the Gemini API and returns the response.

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
        gemini_formatted_messages = self._convert_messages_to_gemini_format(messages)
        api_model_name = self.model
        if api_model_name.startswith("thinking/"):
            api_model_name = api_model_name.replace("thinking/", "", 1) # Remove only the first occurrence

        generation_config_with_none = {
            "temperature": kwargs.get("temperature", self.temperature),
            "maxOutputTokens": kwargs.get("max_tokens", self.max_output_tokens),
            "topP": kwargs.get("top_p", self.top_p),
            "topK": kwargs.get("top_k", self.top_k),
        }
        generation_config = {k: v for k, v in generation_config_with_none.items() if v is not None}

        gemini_params = {
            "contents": gemini_formatted_messages,
            "generationConfig": generation_config,
        }

        # Add extra_body from instance attribute if it exists
        if self.extra_body:
            gemini_params.update(self.extra_body)

        # Add any additional parameters from kwargs that match Gemini's API
        # Ensure we don't overwrite parameters already set from defaults or explicit kwargs
        for key, value in kwargs.items():
            if key not in gemini_params["generationConfig"] and key not in [
                "temperature",
                "max_tokens",
                "top_p",
                "top_k",
                "system_prompt",  # Handled in _convert_messages_to_gemini_format
            ]:
                gemini_params[key] = value

        endpoint = self._get_endpoint(f"models/{api_model_name}:generateContent")
        response_data = self._make_http_request(endpoint, gemini_params, num_retries=num_retries)
        return self._extract_response(response_data)


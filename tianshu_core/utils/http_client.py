import requests
import json
from .base import BaseLLMClient


class SimpleHttpClient(BaseLLMClient):
    """
    A simple LLM client that communicates via HTTP POST requests.
    Assumes a JSON request/response format.
    """

    def __init__(self, config: dict):
        """
        Initialize the HTTP client.

        Args:
            config: A dictionary containing configuration like:
                    'url': (Required) The API endpoint URL.
                    'api_key': (Optional) API key for authentication.
                    'auth_header': (Optional) Name of the auth header (default: 'Authorization').
                    'auth_scheme': (Optional) Scheme for auth header (default: 'Bearer').
                    'headers': (Optional) Custom headers dictionary.
                    'timeout': (Optional) Request timeout in seconds (default: 60).
                    'prompt_field': (Optional) Key for the prompt in the JSON payload (default: 'prompt').
                    'response_path': (Optional) Path to extract response text from JSON,
                                     e.g., 'choices/0/message/content' or ['choices', 0, 'message', 'content']
                                     (default attempts common paths: 'response', 'text', OpenAI structure).
        """
        super().__init__(config)
        self.url = self.config.get("url")
        self.api_key = self.config.get("api_key")
        self.auth_header = self.config.get("auth_header", "Authorization")
        self.auth_scheme = self.config.get("auth_scheme", "Bearer")
        self.headers = self.config.get(
            "headers", {}
        ).copy()  # Use copy to avoid modifying original dict
        self.timeout = self.config.get("timeout", 60)
        self.prompt_field = self.config.get("prompt_field", "prompt")
        self.response_path = self.config.get("response_path")

        # Set default content type if not provided
        self.headers.setdefault("Content-Type", "application/json")
        self.headers.setdefault("Accept", "application/json")

        # Add authentication header if API key is provided
        if self.api_key:
            self.headers[self.auth_header] = f"{self.auth_scheme} {self.api_key}".strip()

    def _validate_config(self):
        """Validate required configuration."""
        if not self.config.get("url"):
            raise ValueError("Configuration must include 'url'")

    def _extract_response(self, response_data: dict) -> str:
        """Extracts the response text from the JSON data based on configured path or defaults."""
        if self.response_path:
            path_keys = (
                self.response_path.split("/")
                if isinstance(self.response_path, str)
                else self.response_path
            )
            value = response_data
            try:
                for key in path_keys:
                    if isinstance(value, list) and key.isdigit():
                        value = value[int(key)]
                    else:
                        value = value[key]
                if isinstance(value, str):
                    return value
                else:
                    raise ValueError(
                        f"Extracted value at path '{self.response_path}' is not a string: {value}"
                    )
            except (KeyError, IndexError, TypeError) as e:
                raise ValueError(
                    f"Could not extract response using path '{self.response_path}': {e}"
                ) from e

        # Default extraction logic if response_path is not set
        if "response" in response_data and isinstance(response_data["response"], str):
            return response_data["response"]
        if "text" in response_data and isinstance(response_data["text"], str):
            return response_data["text"]
        # Handle OpenAI-like structure
        if (
            "choices" in response_data
            and isinstance(response_data["choices"], list)
            and response_data["choices"]
        ):
            first_choice = response_data["choices"][0]
            if "text" in first_choice and isinstance(first_choice["text"], str):
                return first_choice["text"]
            if (
                "message" in first_choice
                and isinstance(first_choice["message"], dict)
                and "content" in first_choice["message"]
                and isinstance(first_choice["message"]["content"], str)
            ):
                return first_choice["message"]["content"]

        # If no known response field is found
        raise ValueError(
            f"Unexpected response format or missing text field. Response keys: {list(response_data.keys())}"
        )

    def send_prompt(self, prompt: str, **kwargs) -> str:
        """
        Sends a prompt to the configured HTTP endpoint.

        Args:
            prompt: The text prompt.
            **kwargs: Additional parameters to include in the JSON payload
                      (e.g., temperature, max_tokens). These will be merged
                      with the prompt under the configured `prompt_field`.

        Returns:
            The response text from the LLM.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails.
            ValueError: If the response format is unexpected or configuration is invalid.
        """
        payload = {self.prompt_field: prompt, **kwargs}

        try:
            response = requests.post(
                self.url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Failed to decode JSON response from LLM server: {e}. Response text: {response.text[:200]}..."
                ) from e

            return self._extract_response(response_data)

        except requests.exceptions.RequestException as e:
            # Log or handle more gracefully if needed
            print(f"HTTP request failed: {e}")
            # Attempt to include response body in error if available
            error_detail = ""
            if e.response is not None:
                error_detail = (
                    f" Status Code: {e.response.status_code}. Response: {e.response.text[:200]}..."
                )
            raise requests.exceptions.RequestException(f"{e}{error_detail}") from e
        except ValueError as e:
            print(f"Error processing LLM response: {e}")
            # Re-raise the ValueError which includes specific details
            raise

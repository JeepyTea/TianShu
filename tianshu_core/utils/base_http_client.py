from datetime import datetime
import random
import requests
import json
import time
from typing import Dict, Any, Optional
from .base import BaseLLMClient


class BaseHttpLLMClient(BaseLLMClient):
    """Base implementation for HTTP-based LLM clients with common functionality."""

    DEFAULT_TIMEOUT = 300  # Default timeout in seconds

    def __init__(self, local_config: dict):
        """
        Initialize the HTTP client with common configuration.

        Args:
            config: A dictionary containing configuration like:
                    'base_url': The API endpoint URL.
                    'timeout': Request timeout in seconds.
                    'headers': Additional custom headers dictionary.
        """
        super().__init__(local_config)

        self.base_url = self.config.get("base_url")
        self.timeout = self.config.get("timeout", self.DEFAULT_TIMEOUT)
        self.headers = self.config.get("headers", {}).copy()

        # Prepare default headers
        self.headers.setdefault("Content-Type", "application/json")
        self.headers.setdefault("Accept", "application/json")

    def _make_http_request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        num_retries: int = 0,
    ) -> Dict[str, Any]:
        """
        Makes an HTTP POST request with error handling and retry logic.

        Args:
            endpoint: The full URL endpoint to send the request to.
            payload: The JSON payload to send.
            headers: Optional headers to use instead of self.headers.
            num_retries: Number of times to retry on network failures or timeouts.

        Returns:
            The parsed JSON response.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails after all retries.
            ValueError: If the response cannot be parsed as JSON.
        """
        current_max_retries = num_retries  # we may get more retries under certain circumstances
        headers = headers or self.headers
        retry_count = 0
        delay = 1  # Start with 1 second delay
        got_too_many_requests = False

        while True:
            try:
                print(
                    "🔴_make_http_request about to make request retry " f"#{retry_count}: {payload}"
                )
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=(self.timeout,self.timeout)
                )
                print(
                    f"🔴_make_http_request Response text: {response.text[:1200]}..."
                )
                response.raise_for_status()

                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Failed to decode JSON response: {e}. Response text: {response.text[:200]}..."
                    ) from e

            except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                print(f"_make_http_request about got request/timeout {e}")
                # Check for error code 429, too many requests.
                if (
                    isinstance(e, requests.exceptions.HTTPError)
                    and e.response.status_code == 429
                    and not got_too_many_requests
                ):
                    #  Too Many Requests, back off, restart request cycle
                    got_too_many_requests = True
                    print(
                        f"‼‼‼_make_http_request got 429 error, retrying. Retry count: {retry_count}, allowing more retries."
                    )
                    # We may have forced the random seed in the Mamba language
                    # interpreter, so set the seed to the system time.
                    random.seed(datetime.now().timestamp())
                    time.sleep(10 + 30*random.random())
                    current_max_retries += 4
                    delay = 20
                retry_count += 1
                if retry_count > current_max_retries:
                    error_detail = ""
                    if hasattr(e, "response") and e.response is not None:
                        try:
                            error_json = e.response.json()
                            print(
                                f"_make_http_request got error : Status Code: {e.response.status_code}. Response: {error_json}"
                            )
                            error_detail = (
                                f" Status Code: {e.response.status_code}. Response: {error_json}"
                            )
                        except json.JSONDecodeError:
                            print(
                                f"_make_http_request got decode error : Status Code: {e.response.status_code}. Response: {e.response.text[:200]}..."
                            )
                            error_detail = f" Status Code: {e.response.status_code}. Response: {e.response.text[:200]}..."
                    print(
                        f" _make_http_request HTTP request failed after {current_max_retries} retries: {e}{error_detail}"
                    )
                    raise requests.exceptions.RequestException(
                        f"EH001 HTTP request (timeout: {self.timeout}) failed after {current_max_retries} retries: {e}{error_detail}"
                    ) from e

                # Exponential backoff with tripling delay
                time.sleep(delay)
                delay *= 3

    def _get_endpoint(self, path: str) -> str:
        """
        Constructs a full endpoint URL from the base URL and path.

        Args:
            path: The API path to append to the base URL.

        Returns:
            The full endpoint URL.
        """
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def __init__(self, config: dict):
        """
        Initialize the client with necessary configuration.

        Args:
            config: A dictionary containing client-specific settings
                    (e.g., API endpoint, keys).
        """
        self.config = config
        self._validate_config()

    def _validate_config(self):
        """Optional method for subclasses to validate configuration."""
        pass

    @abstractmethod
    def send_prompt(self, prompt: str, num_retries: int = 0, **kwargs) -> str:
        """
        Sends a prompt to the LLM server and returns the response.

        Args:
            prompt: The text prompt to send to the LLM.
            num_retries: Number of times to retry on network failures or timeouts.
            **kwargs: Additional parameters specific to the LLM provider
                      (e.g., temperature, max_tokens).

        Returns:
            The response text from the LLM.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
            Exception: Depending on the implementation (e.g., network errors).
        """
        pass

    @abstractmethod
    def send_chat(self, messages: List[Dict[str, str]], num_retries: int = 0, **kwargs) -> str:
        """
        Sends a conversation history to the LLM server and returns the response.

        Args:
            messages: A list of message dictionaries with 'role' and 'content' keys.
            num_retries: Number of times to retry on network failures or timeouts.
            **kwargs: Additional parameters specific to the LLM provider.

        Returns:
            The response text from the LLM.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("This client does not support chat-based interactions")

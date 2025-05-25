"""
Mamba LLM Client Package

Provides classes for interacting with various Large Language Model APIs.
"""

from .base import BaseLLMClient
from .base_http_client import BaseHttpLLMClient
from .http_client import SimpleHttpClient
from .samba_nova_client import SambaNovaClient
from .ollama_client import OllamaClient
from .chutes_client import ChutesClient
from .registry import LLMRegistry

__all__ = [
    "BaseLLMClient",
    "BaseHttpLLMClient",
    "SimpleHttpClient",
    "SambaNovaClient",
    "OllamaClient",
    "ChutesClient",
    "LLMRegistry",
]

__version__ = "0.1.2"  # Bump version

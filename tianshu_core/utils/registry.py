from typing import Dict, Tuple, Any
from .base import BaseLLMClient
from .ollama_client import OllamaClient
from .samba_nova_client import SambaNovaClient
from .chutes_client import ChutesClient


class LLMRegistry:
    """
    Registry for LLM clients that allows accessing models by string identifiers.
    Format: "clienttype/modelname"
    """

    def __init__(self):
        """Initialize the registry with predefined models."""
        self._registry: Dict[str, Tuple[type, Dict[str, Any]]] = {}

        # Register Ollama models
        self._register_ollama_models()

        # Register SambaNova models
        self._register_sambanova_models()

        # Register Chutes models
        self._register_chutes_models()

    def _register_ollama_models(self):
        """Register predefined Ollama models."""
        ollama_models = [
            # ("phi4:14b-q4_K_M", {"options": {"num_ctx": 16000}}),
            # ("deepseek-r1:14b", {"options": {"num_ctx": 128000}}),
            # ("qwen3:14b", {"options": {"num_ctx": 40000}}),
            # ("qwen2.5:0.5b", {"options": {"num_ctx": 32000}}),
            # ("glm4:9b", {"options": {"num_ctx": 128000}}),
            ("phi4:14b-q4_K_M", {"options": {"num_ctx": 1000}}),
            ("deepseek-r1:14b", {"options": {"num_ctx": 1000}}),
            ("qwen3:14b", {"options": {"num_ctx": 1000}}),
            ("qwen2.5:0.5b", {"options": {"num_ctx": 1000}}),
            ("glm4:9b", {"options": {"num_ctx": 1000}}),
        ]

        for model, extra_config in ollama_models:
            key = f"ollama/{model}"
            self._registry[key] = (OllamaClient, {"model": model, **extra_config})

    def _register_sambanova_models(self):
        """Register predefined SambaNova models."""
        sambanova_models = [
            "DeepSeek-R1",
            "DeepSeek-V3-0324",
            "Llama-4-Maverick-17B-128E-Instruct",
            "Llama-4-Scout-17B-16E-Instruct",
            "QwQ-32B",
            "Qwen3-32B",
        ]

        for model in sambanova_models:
            key = f"sambanova/{model}"
            self._registry[key] = (SambaNovaClient, {"model": model})

    def _register_chutes_models(self):
        """Register predefined Chutes models."""
        chutes_models = [
            ("deepseek-ai/DeepSeek-R1", {"context_length": 128000, "temperature": 0.7}),
            ("deepseek-ai/DeepSeek-V3-0324", {"context_length": 128000, "temperature": 0.7}),
            ("deepseek-ai/DeepSeek-R1-0528", {"context_length": 128000, "temperature": 0.7}),
            ("ddeepseek-ai/DeepSeek-R1-0528-Qwen3-8B", {"context_length": 128000, "temperature": 0.7}),
            ("Qwen/Qwen3-235B-A22B", {"context_length": 32000, "temperature": 0.7}),
            ("Qwen/Qwen3-30B-A3B", {"context_length": 32000, "temperature": 0.7}),
            ("Qwen/Qwen3-14B", {"context_length": 32000, "temperature": 0.7}),
            ("THUDM/GLM-4-32B-0414", {"context_length": 32000, "temperature": 0.7}),
            ("chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8", {"context_length": 128000, "temperature": 0.0}),
            ("chutesai/Llama-4-Scout-17B-16E-Instruct", {"context_length": 32000, "temperature": 0.0}),
            ("unsloth/gemma-3-27b-it", {"context_length": 32000, "temperature": 0.7}),
            ("meta-llama/Llama-3-70B-Instruct", {"context_length": 32000, "temperature": 0.7}),
            ("mistralai/Mistral-7B-Instruct-v0.2", {"context_length": 32000, "temperature": 0.7}),
        ]

        for model_info in chutes_models:
            if isinstance(model_info, tuple):
                model, config = model_info
            else:
                model = model_info
                config = {}
                
            key = f"chutes/{model}"
            self._registry[key] = (ChutesClient, {"model": model, **config})

    def get_client(self, model_id: str, **additional_config) -> BaseLLMClient:
        """
        Get an LLM client instance for the specified model ID.

        Args:
            model_id: String identifier in format "clienttype/modelname"
            **additional_config: Additional configuration to pass to the client

        Returns:
            An initialized LLM client

        Raises:
            ValueError: If the model ID is not found in the registry
        """
        if model_id not in self._registry:
            raise ValueError(
                f"Model '{model_id}' not found in registry. Available models: {list(self._registry.keys())}"
            )

        client_class, base_config = self._registry[model_id]

        # Merge the base config with any additional config
        config = {**base_config, **additional_config}

        return client_class(local_config=config)

    def register_model(self, model_id: str, client_class: type, config: Dict[str, Any]) -> None:
        """
        Register a new model in the registry.

        Args:
            model_id: String identifier in format "clienttype/modelname"
            client_class: The client class to instantiate
            config: Configuration dictionary for the client
        """
        self._registry[model_id] = (client_class, config)

    def list_models(self) -> list:
        """
        List all available models in the registry.

        Returns:
            List of model IDs
        """
        return list(self._registry.keys())

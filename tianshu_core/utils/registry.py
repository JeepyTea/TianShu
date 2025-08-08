from typing import Dict, Tuple, Any
from .base import BaseLLMClient
from .ollama_client import OllamaClient
from .samba_nova_client import SambaNovaClient
from .chutes_client import ChutesClient
from .nvidia_client import NvidiaClient
from .openrouter_client import OpenRouterClient
from .anthropic_client import AnthropicClient
from .openai_client import OpenAIClient
from .gemini_client import GeminiClient # Add this import


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

        # Register NVIDIA models
        self._register_nvidia_models()

        # Register OpenRouter models
        self._register_openrouter_models()

        # Register Anthropic models
        self._register_anthropic_models()

        # Register OpenAI models
        self._register_openai_models()

        # Register Gemini models # Add this line
        self._register_gemini_models()

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
            ("zai-org/GLM-4.5-Air", {"context_length": 58000, "temperature": 0.7}),
            ("moonshotai/Kimi-K2-Instruct", {"context_length": 31000, "temperature": 0.7}),
            ("deepseek-ai/DeepSeek-R1-0528", {"context_length": 128000, "temperature": 0.7}),
            ("deepseek-ai/DeepSeek-R1", {"context_length": 128000, "temperature": 0.6, "top_p": 0.7}),
            ("deepseek-ai/DeepSeek-V3-0324", {"context_length": 128000, "temperature": 0.7}),
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

    def _register_nvidia_models(self):
        """Register predefined NVIDIA models."""
        nvidia_models = [
            ("meta/llama-4-maverick-17b-128e-instruct", {"context_length": 128000, "max_tokens": 32000, "temperature": 0.7}),
            ("meta/llama-4-scout-17b-16e-instruct", {"context_length": 128000, "max_tokens": 32000, "temperature": 0.7}),
            ("qwen/qwen3-235b-a22b", {"context_length": 128000, "max_tokens": 32000, "temperature": 0.2, "top_p":0.7, "extra_body": {"chat_template_kwargs": {"thinking":True}}}),
            ("qwen/qwq-32b", {"context_length": 32000, "max_tokens": 32000, "temperature": 0.6, "top_p": 0.7}),
            ("deepseek-ai/deepseek-r1-0528", {"context_length": 128000, "max_tokens": 32000, "temperature": 0.7}),
            ("deepseek-ai/deepseek-r1-distill-qwen-32b", {"context_length": 32000, "max_tokens": 32000, "temperature": 0.6, "top_p": 0.7}),
            ("deepseek-ai/deepseek-r1", {"context_length": 128000, "max_tokens": 32000, "temperature": 0.6, "top_p": 0.7}),
            ("openai/gpt-oss-20b", {"context_length": 128000, "max_tokens": 32000, "temperature": 1, "top_p": 1}),
            ("openai/gpt-oss-120b", {"context_length": 128000, "max_tokens": 32000, "temperature": 1, "top_p": 1}),
            ("moonshotai/kimi-k2-instruct", {"context_length": 31000, "max_tokens": 25000, "temperature": 0.6, "top_p": 0.9}),
            ("microsoft/phi-4-mini-instruct", {"context_length": 128000, "max_tokens": 32000, "temperature": 0.1, "top_p": 0.6}),
            
        ]

        for model_info in nvidia_models:
            if isinstance(model_info, tuple):
                model, config = model_info
            else:
                model = model_info
                config = {}
            key = f"nvidia/{model}"
            self._registry[key] = (NvidiaClient, {"model": model, **config})

    def _register_openrouter_models(self):
        """Register predefined OpenRouter models."""
        openrouter_models = [
            ("openrouter/horizon-alpha", {"temperature": 0.7, "max_tokens": 32000}),            
        ]

        for model_info in openrouter_models:
            if isinstance(model_info, tuple):
                model, config = model_info
            else:
                model = model_info
                config = {}
                
            key = f"openrouter/{model}"
            self._registry[key] = (OpenRouterClient, {"model": model, **config})

    def _register_anthropic_models(self):
        """Register predefined Anthropic models."""
        anthropic_models = [
            ("claude-opus-4-20250514", {"temperature": 0.7, "max_tokens": 31000}),
            ("claude-sonnet-4-20250514", {"temperature": 0.7, "max_tokens": 32000}),
            ("claude-opus-4-1-20250805", {"temperature": 0.7, "max_tokens": 32000}),
            ("claude-3-7-sonnet-20250219", {"temperature": 0.7, "max_tokens": 32000}),
            ("claude-3-5-sonnet-20241022", {"temperature": 0.7, "max_tokens": 8000}),
            ("claude-3-5-haiku-20241022", {"temperature": 0.7, "max_tokens": 8000}),
            # New entries for "thinking" versions
            ("thinking/claude-opus-4-20250514", {"temperature": 1, "max_tokens": 31000, "extra_body": {"thinking": {"type": "enabled", "budget_tokens": 10000},}}),
            ("thinking/claude-sonnet-4-20250514", {"temperature": 1, "max_tokens": 32000, "extra_body": {"thinking": {"type": "enabled", "budget_tokens": 10000},}}),
            ("thinking/claude-opus-4-1-20250805", {"temperature": 1, "max_tokens": 32000, "extra_body": {"thinking": {"type": "enabled", "budget_tokens": 10000},}}),
            ("thinking/claude-3-7-sonnet-20250219", {"temperature": 1, "max_tokens": 32000, "extra_body": {"thinking": {"type": "enabled", "budget_tokens": 10000},}}),
        ]

        for model_info in anthropic_models:
            if isinstance(model_info, tuple):
                model, config = model_info
            else:
                model = model_info
                config = {}
                
            key = f"anthropic/{model}"
            self._registry[key] = (AnthropicClient, {"model": model, **config})

    def _register_openai_models(self):
        """Register predefined OpenAI models."""
        openai_models = [
            ("gpt-4o", {"temperature": 0.7, "max_tokens": 4096}),
            ("gpt-4o-mini", {"temperature": 0.7, "max_tokens": 4096}),
            ("gpt-4-turbo", {"temperature": 0.7, "max_tokens": 4096}),
            ("gpt-3.5-turbo", {"temperature": 0.7, "max_tokens": 4096}),
            # Example for JSON mode
            # ("gpt-4o-json", {"temperature": 0.7, "max_tokens": 4096, "response_format": {"type": "json_object"}}),
        ]

        for model_info in openai_models:
            if isinstance(model_info, tuple):
                model, config = model_info
            else:
                model = model_info
                config = {}
                
            key = f"openai/{model}"
            self._registry[key] = (OpenAIClient, {"model": model, **config})

    def _register_gemini_models(self): # Add this new method
        """Register predefined Google Gemini models."""
        gemini_models = [
            ("gemini-pro", {"temperature": 0.7, "max_tokens": 4096, "top_k": 32}),
            ("gemini-1.5-pro-latest", {"temperature": 0.7, "max_tokens": 8192, "top_k": 32}),
            ("gemini-1.5-flash-latest", {"temperature": 0.7, "max_tokens": 8192, "top_k": 32}),
        ]

        for model_info in gemini_models:
            if isinstance(model_info, tuple):
                model, config = model_info
            else:
                model = model_info
                config = {}
                
            key = f"gemini/{model}"
            self._registry[key] = (GeminiClient, {"model": model, **config})

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

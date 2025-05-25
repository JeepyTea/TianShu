import pytest
from tianshu_core.utils import LLMRegistry
from tianshu_core.utils import OllamaClient
from tianshu_core.utils import SambaNovaClient
from tianshu_core.utils import BaseLLMClient


def test_registry_initialization():
    """Test that the registry initializes with the expected models."""
    registry = LLMRegistry()

    # Check that we have the expected number of models
    models = registry.list_models()
    assert len(models) > 0, "Registry should contain models"

    # Check for specific models
    assert "ollama/phi4:14b-q4_K_M" in models
    assert "ollama/deepseek-r1:14b" in models
    assert "ollama/qwen3:14b" in models

    assert "sambanova/DeepSeek-R1" in models
    assert "sambanova/Llama-4-Maverick-17B-128E-Instruct" in models


def test_get_client():
    """Test that we can get clients from the registry."""
    registry = LLMRegistry()

    # Get an Ollama client
    ollama_client = registry.get_client("ollama/phi4:14b-q4_K_M")
    assert isinstance(ollama_client, OllamaClient)
    assert ollama_client.model == "phi4:14b-q4_K_M"

    # Get a SambaNova client
    sambanova_client = registry.get_client("sambanova/DeepSeek-R1")
    assert isinstance(sambanova_client, SambaNovaClient)
    assert sambanova_client.model == "DeepSeek-R1"


def test_register_custom_model():
    """Test that we can register and retrieve a custom model."""
    registry = LLMRegistry()

    # Register a custom model
    registry.register_model("ollama/custom-model", OllamaClient, {"model": "custom-model"})

    # Check it's in the list
    assert "ollama/custom-model" in registry.list_models()

    # Get the client
    client = registry.get_client("ollama/custom-model")
    assert isinstance(client, OllamaClient)
    assert client.model == "custom-model"


def test_additional_config():
    """Test that additional config is passed to the client."""
    registry = LLMRegistry()

    # Get a client with additional config
    client = registry.get_client(
        "ollama/phi4:14b-q4_K_M", base_url="http://custom-url:11434", timeout=300
    )

    assert client.base_url == "http://custom-url:11434"
    assert client.timeout == 300


def test_invalid_model():
    """Test that requesting an invalid model raises an error."""
    registry = LLMRegistry()

    with pytest.raises(ValueError):
        registry.get_client("invalid/model")

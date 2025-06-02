from tianshu_core.utils.registry import LLMRegistry
import pytest
from tianshu_core.config import Config


# Define LLM model identifiers to test
LLM_IDENTIFIERS = [
    "ollama/qwen2.5:0.5b",
    "ollama/phi4:14b-q4_K_M",
    "ollama/deepseek-r1:14b",
    "ollama/qwen3:14b",
    "chutes/chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8",
]

# Add SambaNova models if API key is available
if Config.SAMBANOVA_API_KEY:
    LLM_IDENTIFIERS.extend(
        [
            "sambanova/DeepSeek-R1",
            "sambanova/DeepSeek-V3-0324",
            "sambanova/Llama-4-Maverick-17B-128E-Instruct",
        ]
    )

# Default parameters for LLM requests
LLM_PARAMS = {
    "temperature": 0.1,
    "top_p": 0.1,
}


@pytest.fixture(scope="session", params=LLM_IDENTIFIERS)
def llm_identifier(request):
    """Fixture that provides each LLM identifier to test."""
    return request.param


@pytest.fixture(scope="session")
def llm_registry():
    """Fixture that provides the LLM registry."""
    return LLMRegistry()


@pytest.fixture(scope="function")
def configured_llm_service(llm_registry, llm_identifier):
    """
    Fixture that instantiates and returns an LLM client and its send_prompt parameters
    based on the current llm_identifier.
    Returns:
        tuple: (initialized_llm_client, send_prompt_parameters_dict)
    """
    try:
        # Get the client from the registry
        client_instance = llm_registry.get_client(llm_identifier)

        # Use the default LLM parameters
        send_prompt_params = LLM_PARAMS.copy()

        return client_instance, send_prompt_params
    except Exception as e:
        pytest.fail(f"Failed to initialize LLM client for model '{llm_identifier}'. Error: {e}")

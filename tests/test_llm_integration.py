import pytest
import sys
import os
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
generated_path = PROJECT_ROOT / "datasets" / "tianshu_v1" / "generated"
current_lang_path = generated_path / "1" / "1"
# Constants based on run_llm_prompt.py and typical test values
# These files are expected to exist from a previous generation step (e.g., seed 1)
PROMPT_FILE_PATHS = [
    current_lang_path / "Language.md",
    current_lang_path / "Problem-001.md",
]
PROMPT_SEPARATOR = "\n\n---\n\n"


def read_prompt_file(file_path: str) -> str:
    """Reads content from a given file path."""
    if not os.path.exists(file_path):
        pytest.fail(
            f"Test setup error: Prompt file not found at {file_path}. "
            "Ensure documents for seed 1 are generated before running this test."
        )
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def test_llm_client_with_generated_docs(configured_llm_service, llm_identifier):
    """
    Tests the configured LLM client by sending concatenated content from pre-generated
    documentation files, making a real HTTP request.
    """
    client, llm_params = configured_llm_service
    # 1. Read and Concatenate Prompts
    prompt_contents = []
    for rel_path in PROMPT_FILE_PATHS:
        prompt_contents.append(read_prompt_file(rel_path))

    concatenated_prompt = PROMPT_SEPARATOR.join(prompt_contents)

    # 2. Call client.send_prompt (this will make a real HTTP request)
    try:
        llm_response_text = client.send_prompt(concatenated_prompt, **llm_params, num_retries=3)
    except Exception as e:
        pytest.fail(f"Model {llm_identifier} send_prompt failed with an exception: {e}")

    # 4. Assertions
    # Check that the response is a non-empty string.
    assert isinstance(llm_response_text, str), "LLM response should be a string."
    assert len(llm_response_text) > 0, "LLM response should not be empty."
    print(f"LLM Response from {llm_identifier}: {llm_response_text[:100]}...")


def test_fetch_generated_program(configured_llm_service, llm_identifier):
    """
    Tests fetching a program from the configured LLM client.
    Note: This test now only verifies that the LLM returns *some* non-empty string.
    The program extraction and execution logic has been moved to test_llm_ability.py.
    """
    client, llm_params = configured_llm_service
    # 1. Read and Concatenate Prompts
    prompt_contents = []
    for rel_path in PROMPT_FILE_PATHS:
        prompt_contents.append(read_prompt_file(rel_path))

    concatenated_prompt = PROMPT_SEPARATOR.join(prompt_contents)

    # 2. Call client.send_prompt (this will make a real HTTP request)
    try:
        llm_response_text = client.send_prompt(concatenated_prompt, **llm_params)
    except Exception as e:
        pytest.fail(f"Model {llm_identifier} send_prompt failed with an exception: {e}")

    # 4. Assertions
    # Check that the response is a non-empty string.
    assert isinstance(llm_response_text, str), "LLM response should be a string."
    assert len(llm_response_text) > 0, "LLM response should not be empty."


def test_chat_conversation(configured_llm_service, llm_identifier):
    """
    Tests the chat conversation capability of the LLM client.
    """
    client, llm_params = configured_llm_service

    # Create a simple conversation
    conversation = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, can you help me with a programming problem?"},
    ]

    # Try to use send_chat if available, otherwise skip the test
    try:
        response = client.send_chat(conversation, num_retries=2, **llm_params)
    except (NotImplementedError, AttributeError):
        pytest.skip(f"Model {llm_identifier} does not support chat conversations")
    except Exception as e:
        pytest.fail(f"Model {llm_identifier} send_chat failed with an exception: {e}")

    # Add the response to the conversation
    conversation.append({"role": "assistant", "content": response})

    # Continue the conversation
    conversation.append({"role": "user", "content": "Can you explain what a for loop is?"})

    # Send the updated conversation
    try:
        follow_up_response = client.send_chat(conversation, num_retries=2, **llm_params)
    except Exception as e:
        pytest.fail(f"Model {llm_identifier} send_chat follow-up failed with an exception: {e}")

    # Assertions
    assert isinstance(response, str), "First LLM response should be a string."
    assert len(response) > 0, "First LLM response should not be empty."
    assert isinstance(follow_up_response, str), "Follow-up LLM response should be a string."
    assert len(follow_up_response) > 0, "Follow-up LLM response should not be empty."
    assert "loop" in follow_up_response.lower(), "Follow-up response should mention loops"

    print(f"Initial response from {llm_identifier}: {response[:100]}...")
    print(f"Follow-up response from {llm_identifier}: {follow_up_response[:100]}...")

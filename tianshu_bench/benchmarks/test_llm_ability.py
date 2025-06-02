import pytest
import os
import csv
import re  # Added for program extraction
import allure
import logging
import datetime

# Import LLM client base class and specific clients if needed for type hinting or direct use
from tianshu_core.utils import LLMRegistry  # Import the registry
from typing import List, Tuple  # For output_log type hint

import ply.lex as lex
# Mamba imports
from tianshu_core.mamba import mamba
import importlib
importlib.import_module("tianshu_core.mamba", "mamba")
from mamba import execute as mamba_execute
import mamba.ast
import mamba.symbol_table
import mamba.lexer
import mamba.parser

from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.parent

LOG_BASE_DIR = PROJECT_ROOT / "results" / "test_logs"
os.makedirs(LOG_BASE_DIR, exist_ok=True)


PROMPT_SEPARATOR = "\n\n---\n\n"

# System prompt to guide the LLM's response
SYSTEM_PROMPT = """Act as an expert software developer.
Take requests for creation of new code.
Always reply to the user in English.
You MUST:
1. Explain any code.
2. Output a copy of the entire requested code."""


def reset_mamba_state():
    """
    Reset all global state in the Mamba interpreter to ensure clean execution
    between runs.
    """
    # Reset the symbol table
    mamba.ast.symbols = mamba.symbol_table.SymbolTable()
    mamba.ast.symbols.reset()

    # Reset lexer state
    # Restore original reserved words in the lexer
    mamba.lexer.reserved = mamba.lexer._original_reserved.copy()
    # Update the lexer's token list based on the restored reserved words
    mamba.lexer.tokens = mamba.lexer.base_tokens + list(mamba.lexer.reserved.values())
    # Update the parser's token list to match the lexer's current token list
    # (mamba.parser.py sets its `tokens` variable by copying `mamba.lexer.tokens` at import time)
    mamba.parser.tokens = mamba.parser.base_tokens + list(mamba.lexer._original_reserved.values())
    # Rebuild the lexer instance with the updated token list
    # The optimize=0 flag can sometimes help when re-initializing PLY lexers.
    mamba.lexer.lexer = lex.lex(module=mamba.lexer, optimize=0)

    # Reset output handler in AST module
    mamba.ast.set_output_handler(None)

    # Reset parser warnings flag (assuming mamba.parser is imported)
    mamba.parser.disable_warnings = False


def read_prompt_file(file_path: str) -> str:
    """Reads content from a given file path."""
    if not os.path.exists(file_path):
        pytest.fail(
            f"Test setup error: Prompt file not found at {file_path}. "
            "Ensure documents for seed 1 are generated before running this test."
        )
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# List of LLM identifiers to test with
LLM_IDENTIFIERS = [
    "ollama/phi4:14b-q4_K_M",
    "ollama/deepseek-r1:14b",
    "ollama/qwen3:14b",
    "ollama/qwen2.5:0.5b",
    "ollama/glm4:9b",
    "chutes/deepseek-ai/DeepSeek-V3-0324",
    "chutes/deepseek-ai/DeepSeek-R1",
    "chutes/Qwen/Qwen3-235B-A22B",
    "chutes/Qwen/Qwen3-30B-A3B",
    "chutes/Qwen/Qwen3-14B",
    "chutes/THUDM/GLM-4-32B-0414",
    "chutes/chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8",
    "chutes/chutesai/Llama-4-Scout-17B-16E-Instruct",
    # "sambanova/DeepSeek-R1",
    # "sambanova/DeepSeek-V3-0324",
    # "sambanova/Llama-4-Maverick-17B-128E-Instruct",
]

# Default LLM parameters
LLM_PARAMS = {
    "temperature": 0.1,
    "top_p": 0.1,
}


def load_problem_definitions():
    """Load problem definitions from a single CSV file as individual test cases."""
    test_cases = []
    csv_path = PROJECT_ROOT / "datasets" / "tianshu_v1" / "problem_definitions.csv"

    with open(csv_path, "r") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            test_cases.append(
                {
                    "id": row["problem_id"],
                    "name": row["problem_name"],
                    "description": row["problem_description"],
                    "input": row["test_input"],
                    "expected_output": row["expected_output"],
                }
            )

    return test_cases


@pytest.fixture(scope="function")
def detailed_test_logger(request):
    # Create a unique subdirectory for this specific test's logs if needed
    test_run_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    # Sanitize test name for filename/dirname
    sanitized_test_name = request.node.name.replace("[", "_").replace("]", "").replace("/", "_")
    test_log_dir = os.path.join(LOG_BASE_DIR, sanitized_test_name, test_run_timestamp)
    os.makedirs(test_log_dir, exist_ok=True)

    log_file_name = "detailed.log"
    log_file_path = os.path.join(test_log_dir, log_file_name)

    logger = logging.getLogger(f"detailed_logger_{sanitized_test_name}")
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file_path, mode='w')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    print(f"Detailed logging for {request.node.name} to: {log_file_path}") # For console feedback

    yield logger

    # Teardown: Detach handler and attach log file to Allure report
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    if os.path.exists(log_file_path) and os.path.getsize(log_file_path) > 0: # Only attach if file exists and is not empty
        try:
            allure.attach.file(log_file_path, name=f"Detailed Log for {sanitized_test_name}",
                               attachment_type=allure.attachment_type.TEXT)
        except Exception as e:
            print(f"Error attaching log {log_file_path} to Allure: {e}")
    # else:
    #     print(f"Log file {log_file_path} not found or empty, not attaching.")


@pytest.mark.parametrize("test_case", load_problem_definitions())
@pytest.mark.parametrize("mamba_execution_seed", range(1, 11))
@pytest.mark.parametrize("llm_identifier", LLM_IDENTIFIERS)
def test_generated_program_with_mamba_execution(llm_identifier, mamba_execution_seed, test_case):
    """
    Tests fetching a program from the LLM client for a specific problem,
    executing it with the Mamba interpreter, and checking for expected output.
    Each row in the CSV file creates a separate test case.
    The Mamba execution is parameterized with different random seeds.
    """
    # Create registry and get the client
    registry = LLMRegistry()
    try:
        client = registry.get_client(llm_identifier, **LLM_PARAMS)
    except ValueError as e:
        pytest.skip(f"Skipping test for {llm_identifier}: {str(e)}")
    problem_name = test_case["name"]
    # 1. Read and Concatenate Prompts
    problem_id = test_case["id"]
    generated_path = PROJECT_ROOT / "datasets" / "tianshu_v1" / "generated"
    current_lang_path = generated_path / f"{mamba_execution_seed}" / f"{mamba_execution_seed}"
    dynamic_prompt_file_paths = [
        current_lang_path / "Language.md",
        current_lang_path / f"Problem-{problem_id}.md",
    ]

    prompt_contents = []
    for rel_path in dynamic_prompt_file_paths:
        prompt = read_prompt_file(rel_path)
        prompt_contents.append(prompt)

    concatenated_prompt = PROMPT_SEPARATOR.join(prompt_contents)

    # 2. Call client.send_prompt
    try:
        llm_response_text = client.send_prompt(concatenated_prompt, system_prompt=SYSTEM_PROMPT)
    except Exception as e:
        raise Exception(f"{client.__class__.__name__}.send_prompt failed with an exception: {e}")

    # 3. Extract Program from LLM Response
    assert isinstance(llm_response_text, str), "LLM response should be a string."
    assert len(llm_response_text) > 0, "LLM response should not be empty."

    code_blocks = re.findall(r"```(?:[a-zA-Z]+\n)?(.*?)```", llm_response_text, re.DOTALL)
    generated_program = ""
    if code_blocks:
        # Get the last code block
        generated_program = code_blocks[-1].strip()

    assert (
        len(generated_program) > 0
    ), f"No program found in LLM response. Response was:\n{llm_response_text}"
    print(f"💚💻 Generated Mamba program for Problem-{problem_id}:\n{generated_program}")

    # 4. Execute with Mamba Interpreter
    input_value = test_case["input"]
    expected_output = test_case["expected_output"]

    reset_mamba_state()  # Ensure Mamba state is clean
    mamba.apply_random_keywords(mamba_execution_seed)
    output_log: List[Tuple[str, str]] = []

    # Parse the input string into a list of values
    input_values = test_case["input"].split(",") if test_case["input"] else []
    input_index = 0  # Track which input value to return next

    def collect_output_handler(message: str, stream: str):
        """Appends the message and its stream type to the log list."""
        output_log.append((stream, message))

    def mock_input_handler(prompt: str) -> str:
        """Returns the next input value when the program requests input."""
        nonlocal input_index
        # Record the prompt if needed
        output_log.append(("prompt", prompt))

        # Return the next input value if available
        if input_index < len(input_values):
            value = input_values[input_index]
            input_index += 1
            return value

        # Throw an exception if no more inputs are available
        raise ValueError(
            f"No more input values available. Program requested input with prompt: '{prompt}'"
        )

    try:
        mamba_execute(
            source=generated_program,
            output_handler=collect_output_handler,
            input_handler=mock_input_handler,
            disable_warnings=True,
            random_seed=mamba_execution_seed,
            random_seed_was_set=True,
        )
    except Exception as e:
        pytest.fail(
            f"Mamba execution failed for Problem-{problem_id}, test case '{input_value}' with exception: {e}\n"
            f"Program was:\n{generated_program}\n"
            f"Output log: {output_log}"
        )
    finally:
        reset_mamba_state()  # Clean up Mamba state after execution

    # 5. Assert Mamba Output
    stdout_messages = [msg for stream, msg in output_log if stream == "stdout"]
    stderr_messages = [msg for stream, msg in output_log if stream == "stderr"]

    if stderr_messages:
        pytest.fail(
            f"Problem-{problem_id}, problem '{problem_name}' test case in: '{input_value}' "
            f"seed {mamba_execution_seed}: "
            f"Expected output '{expected_output}', but got stderr output \n"
            f"'{''.join(stderr_messages)}'.\n"
            f"Program was:\n{generated_program}\n"
            f"Full Mamba output log: {output_log}"
        )

    full_stdout = "".join(stdout_messages)
    assert full_stdout == expected_output, (
        f"Problem-{problem_id}, problem '{problem_name}' in: '{input_value}' "
        f"seed {mamba_execution_seed}: "
        f"Expected output '{expected_output}', but got '{full_stdout}'.\n"
        f"Program was:\n{generated_program}\n"
        f"Full Mamba output log: {output_log}"
    )


# Define LLMs to skip for multi-shot testing
SKIP_LLMS = [
    "chutes/chutesai/Llama-4-Maverick-17B-128E-Instruct-FP8",
    "chutes/chutesai/Llama-4-Scout-17B-16E-Instruct"
]

@pytest.mark.parametrize("test_case", load_problem_definitions())
@pytest.mark.parametrize("mamba_execution_seed", range(1, 11))
@pytest.mark.parametrize("num_shots", [1, 2, 4, 8])
@pytest.mark.parametrize("llm_identifier", [
    pytest.param(llm, marks=pytest.mark.skip(reason=f"Skipping multi-shot test for {llm}"))
    if llm in SKIP_LLMS else llm
    for llm in LLM_IDENTIFIERS
])
def test_execute_generated_multi_shot(
        llm_identifier, mamba_execution_seed,
        test_case, num_shots, detailed_test_logger
    ):
    """
    Tests fetching a program from the LLM client for a specific problem,
    executing it with the Mamba interpreter, and checking for expected output.
    Each row in the CSV file creates a separate test case.
    The Mamba execution is parameterized with different random seeds.
    Uses multi-shot approach with conversation history, retrying with guidance if the program fails.
    """
    # Create registry and get the client
    registry = LLMRegistry()
    try:
        client = registry.get_client(llm_identifier, **LLM_PARAMS)
    except ValueError as e:
        pytest.xfail(f"Skipping test for {llm_identifier}: {str(e)}")

    problem_name = test_case["name"]
    problem_id = test_case["id"]
    input_value = test_case["input"]
    expected_output = test_case["expected_output"]

    # 1. Read and Concatenate Prompts
    generated_path = PROJECT_ROOT / "datasets" / "tianshu_v1" / "generated"
    current_lang_path = generated_path / f"{mamba_execution_seed}" / f"{mamba_execution_seed}"
    dynamic_prompt_file_paths = [
        current_lang_path / "Language.md",
        current_lang_path / f"Problem-{problem_id}.md",
    ]
    prompt_contents = []
    for rel_path in dynamic_prompt_file_paths:
        prompt = read_prompt_file(rel_path)
        prompt_contents.append(prompt)

    prompt_contents.append(".")

    concatenated_prompt = PROMPT_SEPARATOR.join(prompt_contents)
    detailed_test_logger.debug(f"System prompt: {SYSTEM_PROMPT}")
    detailed_test_logger.debug("--")
    detailed_test_logger.debug(f"Beginning prompt: {concatenated_prompt}")

    # Initialize conversation history
    conversation_history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": concatenated_prompt},
    ]

    # Multi-shot loop
    for shot in range(num_shots):
        # print("test_execute_generated_multi_shot 50")
        # 2. Call client.send_chat with current conversation history
        try:
            # Try to use send_chat if available, otherwise fall back to send_prompt
            try:
                # print("test_execute_generated_multi_shot 60 about to send chat request")
                llm_response_text = client.send_chat(
                    conversation_history, num_retries=5, **LLM_PARAMS
                )
                detailed_test_logger.debug("--")
                detailed_test_logger.debug(f"LLM response: {llm_response_text}")
                # print("test_execute_generated_multi_shot 70 got chat request")
            except (NotImplementedError, AttributeError) as e:
                # print(f"test_execute_generated_multi_shot 75 request error {e}")
                # Fall back to send_prompt with the last user message
                last_user_message = next(
                    msg["content"]
                    for msg in reversed(conversation_history)
                    if msg["role"] == "user"
                )
                # print("test_execute_generated_multi_shot 77 request error about to send prompt")
                llm_response_text = client.send_prompt(
                    last_user_message, system_prompt=SYSTEM_PROMPT
                )
                # print("test_execute_generated_multi_shot 78 request error")
        except Exception as e:
            # print(f"test_execute_generated_multi_shot 78 request error {e}")
            detailed_test_logger.debug("--")
            detailed_test_logger.debug(f"{client.__class__.__name__}.send_chat/send_prompt failed with an exception: {e}")
            # Immediately error out of the test if the LLM request fails
            pytest.xfail(
                f"{client.__class__.__name__}.send_chat/send_prompt failed with an exception: {e}"
            )

        # Add the assistant's response to the conversation history
        conversation_history.append({"role": "assistant", "content": llm_response_text})
        # print("test_execute_generated_multi_shot 80")

        # 3. Extract Program from LLM Response
        assert isinstance(llm_response_text, str), f"E001 LLM response should be a string. Got type: {type(llm_response_text)}"
        assert len(llm_response_text) > 0, "E002 LLM response should not be empty."

        code_blocks = re.findall(r"```(?:[a-zA-Z]+\n)?(.*?)```", llm_response_text, re.DOTALL)
        generated_program = ""
        if code_blocks:
            # Get the last code block
            generated_program = code_blocks[-1].strip()
        detailed_test_logger.debug("--")
        detailed_test_logger.debug(f"Generated program: {generated_program}")

        if not generated_program:
            if shot == num_shots - 1:  # Last attempt
                detailed_test_logger.debug("--")
                detailed_test_logger.debug("Error: E003")
                assert (
                    False
                ), f"E003 No program found in LLM response after {num_shots} attempts. Response was:\n{llm_response_text}"
            # Add guidance and continue to next shot
            guidance = "No code block was found in your response. Please provide a complete solution enclosed in triple backticks (```)."
            detailed_test_logger.debug("--")
            detailed_test_logger.debug(f"Guidance: {guidance}")
            conversation_history.append({"role": "user", "content": guidance})
            continue

        print(
            f"💫🧡Shot {shot+1}/{num_shots} - Generated Mamba program for Problem-{problem_id}:\n{generated_program}"
        )

        # 4. Execute with Mamba Interpreter
        reset_mamba_state()  # Ensure Mamba state is clean
        mamba.apply_random_keywords(mamba_execution_seed)
        output_log: List[Tuple[str, str]] = []
        print("test_execute_generated_multi_shot 90")

        # Parse the input string into a list of values
        input_values = test_case["input"].split(",") if test_case["input"] else []
        input_index = 0  # Track which input value to return next

        # print("test_execute_generated_multi_shot 100")
        def collect_output_handler(message: str, stream: str):
            """Appends the message and its stream type to the log list."""
            output_log.append((stream, message))

        def mock_input_handler(prompt: str) -> str:
            """Returns the next input value when the program requests input."""
            nonlocal input_index
            # Record the prompt if needed
            output_log.append(("prompt", prompt))

            # Return the next input value if available
            if input_index < len(input_values):
                value = input_values[input_index]
                input_index += 1
                return value

            # If we're out of inputs but not on the last shot, add guidance
            if shot < num_shots - 1:
                raise ValueError(
                    f"No more input values available. Program requested too many inputs."
                )

            # Throw an exception if no more inputs are available and this is the last shot
            raise ValueError(
                f"No more input values available. Program requested input with prompt: '{prompt}'"
            )

        try:
            # print("test_execute_generated_multi_shot 110")
            mamba_execute(
                source=generated_program,
                output_handler=collect_output_handler,
                input_handler=mock_input_handler,
                disable_warnings=True,
                random_seed=mamba_execution_seed,
                random_seed_was_set=True,
            )
            # print("test_execute_generated_multi_shot 120")
        except Exception as e:
            # print("test_execute_generated_multi_shot 130")
            if shot == num_shots - 1:  # Last attempt
                detailed_test_logger.debug("--")
                detailed_test_logger.debug("Error: E004")
                pytest.fail(
                    f"E004 Mamba execution failed for Problem-{problem_id}, test case '{input_value}' with exception: {e}\n"
                    f"seed: {mamba_execution_seed} \n"
                    f"Shot: {shot+1}\n"
                    f"Program was:\n{generated_program}\n"
                    f"Output log: {output_log}"
                )
            # Add guidance and continue to next shot
            guidance = (
                f"Your program failed with error: {str(e)}. Please fix the issue and try again."
            )
            conversation_history.append({"role": "user", "content": guidance})
            detailed_test_logger.debug("--")
            detailed_test_logger.debug(f"Guidance: {guidance}")
            # print("test_execute_generated_multi_shot 140")
            reset_mamba_state()  # Clean up Mamba state after execution
            continue

        # 5. Check for stderr messages
        # print("test_execute_generated_multi_shot 150")
        stderr_messages = [msg for stream, msg in output_log if stream == "stderr"]
        if stderr_messages:
            if shot == num_shots - 1:  # Last attempt
                detailed_test_logger.debug("--")
                detailed_test_logger.debug("Error: E005")
                pytest.fail(
                    f"E005 Problem-{problem_id}, problem '{problem_name}' test case in: '{input_value}' "
                    f"seed: {mamba_execution_seed} \n"
                    f"Shot: {shot+1}\n"
                    f"Expected output '{expected_output}', but got stderr output \n"
                    f"'{''.join(stderr_messages)}'.\n"
                    f"Program was:\n{generated_program}\n"
                    f"Full Mamba output log: {output_log}"
                )
            # Add guidance and continue to next shot
            # print("test_execute_generated_multi_shot 160")
            guidance = f"Your program produced errors: {''.join(stderr_messages)}. Please fix the issues and try again."
            detailed_test_logger.debug("--")
            detailed_test_logger.debug(f"Guidance: {guidance}")
            conversation_history.append({"role": "user", "content": guidance})
            reset_mamba_state()  # Clean up Mamba state after execution
            continue

        # 6. Check output matches expected
        stdout_messages = [msg for stream, msg in output_log if stream == "stdout"]
        full_stdout = "".join(stdout_messages)
        detailed_test_logger.debug("--")
        detailed_test_logger.debug(f"Program output: {full_stdout}")

        # print("test_execute_generated_multi_shot 170")
        if full_stdout == expected_output:
            # Success! Break out of the loop
            detailed_test_logger.debug("--")
            detailed_test_logger.debug("🟢 Program output was correct!")
            reset_mamba_state()  # Clean up Mamba state after execution
            return

        if shot == num_shots - 1:  # Last attempt
            if full_stdout != expected_output:
                detailed_test_logger.debug("--")
                detailed_test_logger.debug("Error: E006")
            assert full_stdout == expected_output, (
                f"E006 Problem-{problem_id}, problem '{problem_name}' in: '{input_value}' "
                f"seed: {mamba_execution_seed} "
                f"Shot: {shot+1}\n"
                f"Expected output '{expected_output}', but got '{full_stdout}'.\n"
                f"Program was:\n{generated_program}\n"
                f"Full Mamba output log: {output_log}"
            )
        # print("test_execute_generated_multi_shot 180")
        # Add guidance and continue to next shot
        guidance = f"Your program produced incorrect output. Expected: '{expected_output}', but got: '{full_stdout}'. Please fix your solution."
        detailed_test_logger.debug("--")
        detailed_test_logger.debug(f"Guidance: {guidance}")
        conversation_history.append({"role": "user", "content": guidance})
        reset_mamba_state()  # Clean up Mamba state after execution


@pytest.mark.parametrize(
    "test_case", load_problem_definitions()[:1]
)  # Just use the first problem for this test
@pytest.mark.parametrize("mamba_execution_seed", [1])  # Use just one seed for simplicity
@pytest.mark.parametrize("llm_identifier", LLM_IDENTIFIERS)
def test_conversation_history(llm_identifier, mamba_execution_seed, test_case):
    """
    Tests using conversation history with the LLM client for a specific problem.
    """
    # Create registry and get the client
    registry = LLMRegistry()
    try:
        client = registry.get_client(llm_identifier, **LLM_PARAMS)
    except ValueError as e:
        pytest.skip(f"Skipping test for {llm_identifier}: {str(e)}")

    problem_name = test_case["name"]
    problem_id = test_case["id"]
    input_value = test_case["input"]
    expected_output = test_case["expected_output"]

    # 1. Read and Concatenate Prompts
    generated_path = PROJECT_ROOT / "datasets" / "tianshu_v1" / "generated"
    current_lang_path = generated_path / f"{mamba_execution_seed}" / f"{mamba_execution_seed}"
    dynamic_prompt_file_paths = [
        current_lang_path / "Language.md",
        current_lang_path / f"Problem-{problem_id}.md",
    ]

    prompt_contents = []
    for rel_path in dynamic_prompt_file_paths:
        prompt_contents.append(read_prompt_file(rel_path)[:200])

    concatenated_prompt = PROMPT_SEPARATOR.join(prompt_contents)

    # Initialize conversation history
    conversation_history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": concatenated_prompt},
    ]

    # First message - get initial solution
    try:
        # Try to use send_chat if available, otherwise fall back to send_prompt
        try:
            llm_response_text = client.send_chat(conversation_history, **LLM_PARAMS)
        except (NotImplementedError, AttributeError):
            # Fall back to send_prompt with the last user message
            last_user_message = next(
                msg["content"] for msg in reversed(conversation_history) if msg["role"] == "user"
            )
            llm_response_text = client.send_prompt(last_user_message, system_prompt=SYSTEM_PROMPT)
    except Exception as e:
        pytest.skip(f"LLM request failed: {e}")

    # Add the assistant's response to the conversation history
    conversation_history.append({"role": "assistant", "content": llm_response_text})

    # Extract program from response
    code_blocks = re.findall(r"```(?:[a-zA-Z]+\n)?(.*?)```", llm_response_text, re.DOTALL)
    generated_program = ""
    if code_blocks:
        generated_program = code_blocks[-1].strip()

    assert (
        len(generated_program) > 0
    ), f"No program found in LLM response. Response was:\n{llm_response_text}"

    # Second message - ask for explanation
    conversation_history.append(
        {"role": "user", "content": "Please explain how your solution works."}
    )

    try:
        # Try to use send_chat if available, otherwise fall back to send_prompt
        try:
            explanation_response = client.send_chat(
                conversation_history, num_retries=2, **LLM_PARAMS
            )
        except (NotImplementedError, AttributeError):
            # This fallback won't work well for conversation history, but we include it for completeness
            explanation_response = client.send_prompt(
                "Please explain how your solution works.", system_prompt=SYSTEM_PROMPT
            )
    except Exception as e:
        pytest.skip(f"LLM explanation request failed: {e}")

    # Add the assistant's explanation to the conversation history
    conversation_history.append({"role": "assistant", "content": explanation_response})

    # Verify we got a meaningful explanation
    assert len(explanation_response) > 50, "Explanation is too short"
    assert (
        "code" in explanation_response.lower() or "solution" in explanation_response.lower()
    ), "Explanation doesn't seem to reference the code or solution"

    print(f"Generated program for {problem_name}:\n{generated_program}")
    print(f"Explanation:\n{explanation_response[:200]}...")

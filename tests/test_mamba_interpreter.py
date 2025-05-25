import pytest

# add "mamba directory to system path"


import tianshu_core.mamba as mamba
from typing import List, Tuple


def reset_mamba_state():
    """
    Reset all global state in the Mamba interpreter to ensure clean execution
    between runs.
    """
    # Reset the symbol table
    import tianshu_core.mamba.symbol_table

    mamba.ast.symbols = mamba.symbol_table.SymbolTable()
    mamba.ast.symbols.reset()

    # Reset lexer state - be careful with the order
    import tianshu_core.mamba.lexer

    # First restore the original reserved words
    mamba.lexer.reserved = mamba.lexer._original_reserved.copy()
    # Then update tokens in parser to match the original reserved words
    import tianshu_core.mamba.parser

    mamba.parser.tokens = mamba.parser.base_tokens + list(mamba.lexer._original_reserved.values())
    # Now rebuild the lexer with the restored state
    mamba.lexer.lexer = mamba.lexer.lex.lex(module=mamba.lexer)

    # Reset output handler
    mamba.ast.set_output_handler(None)

    # Reset parser warnings flag
    mamba.parser.disable_warnings = False


def test_mamba_hello_world():
    """
    Tests a simple Mamba program that prints "Hello World".
    """
    mamba_code = 'say "Hello World";'

    # List to store tuples of (stream, message)
    output_log: List[Tuple[str, str]] = []

    def collect_output_handler(message: str, stream: str):
        """Appends the message and its stream type to the log list."""
        output_log.append((stream, message))

    # Execute the Mamba code with the custom output handler
    # No specific seed is needed for this simple program.
    # Warnings are disabled to keep test output clean.
    mamba.execute(source=mamba_code, output_handler=collect_output_handler, disable_warnings=True)

    # Filter for stdout messages and concatenate them
    # The 'say' command in Mamba prints without a trailing newline.
    # For 'say "Hello World";', we expect a single stdout entry.
    stdout_messages = [msg for stream, msg in output_log if stream == "stdout"]

    assert len(stdout_messages) == 1, f"Expected 1 stdout message, got {len(stdout_messages)}"
    assert (
        stdout_messages[0] == "Hello World"
    ), f"Expected 'Hello World', got '{stdout_messages[0]}'"


def test_mamba_runtime_error_capture():
    """
    Tests if runtime errors from Mamba are captured by the output_handler.
    """
    mamba_code = "x = 10 / 0;"  # This will cause a runtime error

    output_log: List[Tuple[str, str]] = []

    def collect_output_handler(message: str, stream: str):
        output_log.append((stream, message))

    mamba.execute(
        source=mamba_code,
        output_handler=collect_output_handler,
        disable_warnings=True,  # Important: execute() must not re-raise if disable_warnings is True
    )

    stderr_messages = [msg for stream, msg in output_log if stream == "stderr"]

    assert len(stderr_messages) == 1, "Expected 1 stderr message for the runtime error"
    # Check for a part of the expected error message.
    # The exact error message format comes from mamba.ast.BinaryOperation
    assert (
        "DuplicateSymbol: Cannot redeclare function 'int'" in stderr_messages[0]
    ), f"Error message not as expected: {stderr_messages[0]}"


def test_mamba_with_remapped_keywords():
    """
    Tests that Mamba can run a program with remapped keywords when a random seed is set.
    """
    reset_mamba_state()
    # Set a specific random seed for reproducibility
    test_seed = 1

    # Apply keyword remapping using the function from mamba.py
    # This will load keywords, shuffle them with test_seed, and call mamba.lexer.override_reserved_words()
    # The 'mamba' module here refers to the mamba.py script, due to sys.path manipulation at the top of this file.
    mamba.apply_random_keywords(test_seed)

    # Find what 'IF' and 'PRINT' (for 'say') were remapped to by inspecting the now-modified mamba.lexer.reserved
    if_keyword = None
    print_keyword = None
    current_reserved_map = (
        mamba.lexer.reserved
    )  # mamba.lexer is the lexer module from the mamba package
    for keyword, token_type in current_reserved_map.items():
        if token_type == "IF":
            if_keyword = keyword
        if token_type == "PRINT":  # 'say' is originally mapped to the 'PRINT' token type
            print_keyword = keyword
    # print (f"mamba.lexer.reserved 1: {mamba.lexer.reserved}")
    assert (
        if_keyword is not None
    ), "Could not determine the remapped 'IF' keyword from mamba.lexer.reserved."
    assert (
        print_keyword is not None
    ), "Could not determine the remapped 'PRINT' (for 'say') keyword from mamba.lexer.reserved."

    # Create a simple program using the dynamically determined remapped keywords
    mamba_code = f'{if_keyword} (1==1) {{ {print_keyword} "Keyword remapping works!"; }}'
    mamba_code = f'{print_keyword}("Keyword remapping works!");'
    # For debugging, you can print the generated code:
    print(f"Testing Mamba code with remapped keywords: {mamba_code}")
    # List to store output
    output_log: List[Tuple[str, str]] = []

    def collect_output_handler(message: str, stream: str):
        output_log.append((stream, message))

    # Store original reserved words to restore them later
    # original_lexer_reserved_before_execute = mamba.lexer.reserved.copy()
    original_lexer_original_reserved = mamba.lexer._original_reserved.copy()
    # print (f"mamba.lexer.reserved 2: {mamba.lexer.reserved}")
    try:
        # Execute the Mamba code. mamba.execute itself should handle overriding
        # mamba.lexer.reserved based on the seed.
        mamba.execute(
            source=mamba_code,
            output_handler=collect_output_handler,
            disable_warnings=True,
            random_seed=test_seed,
            random_seed_was_set=True,  # Crucial for keyword remapping logic in mamba.py/mamba.execute
        )
    finally:
        # IMPORTANT: Reset the lexer's reserved words to their original state
        # to avoid interference with other tests.
        mamba.lexer._original_reserved = original_lexer_original_reserved.copy()
        mamba.lexer.override_reserved_words(original_lexer_original_reserved)

    # Filter for stdout messages
    stdout_messages = [msg for stream, msg in output_log if stream == "stdout"]

    # Verify the output
    assert (
        len(stdout_messages) == 1
    ), f"Expected 1 stdout message, got {len(stdout_messages)}. Log: {output_log} Test code: {mamba_code}"
    assert (
        stdout_messages[0] == "Keyword remapping works!"
    ), f"Expected 'Keyword remapping works!', got '{stdout_messages[0]}'. Log: {output_log}"


def test_mamba_input_handler():
    """
    Tests that the input handler is used when provided to execute().
    """
    reset_mamba_state()

    # Simple program that asks for input and prints it back
    mamba_code = 'name = ask("Enter your name: "); say "Hello, " + name + "!";'

    # Prepare input and output handlers
    output_log: List[Tuple[str, str]] = []
    input_values = ["Test User"]  # Values to return when input is requested
    input_prompts = []  # To store prompts passed to the input handler

    def collect_output_handler(message: str, stream: str):
        output_log.append((stream, message))

    def mock_input_handler(prompt: str) -> str:
        input_prompts.append(prompt)  # Record the prompt
        if input_values:
            return input_values.pop(0)  # Return and remove the first value
        return "Default input"  # Fallback if input_values is empty

    # Execute the program with our handlers
    mamba.execute(
        source=mamba_code,
        output_handler=collect_output_handler,
        input_handler=mock_input_handler,
        disable_warnings=True,
    )

    # Verify the input handler was called with the expected prompt
    assert len(input_prompts) == 1, f"Expected 1 input prompt, got {len(input_prompts)}"
    assert input_prompts[0] == "Enter your name: ", f"Unexpected prompt: '{input_prompts[0]}'"

    # Verify the output contains the expected greeting
    stdout_messages = [msg for stream, msg in output_log if stream == "stdout"]
    assert len(stdout_messages) == 1, f"Expected 1 stdout message, got {len(stdout_messages)}"
    assert stdout_messages[0] == "Hello, Test User!", f"Unexpected output: '{stdout_messages[0]}'"

from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

mamba_dir = PROJECT_ROOT / "tianshu_core" / "mamba"
if str(mamba_dir) not in sys.path:
    sys.path.insert(0, str(mamba_dir))

import time
import mamba.parser as p
import mamba.ast
import mamba.environment as environment
import mamba.exceptions
import mamba.lexer  # Import lexer module
import pprint

import random
from typing import Callable, Optional  # Added for typing
from datetime import datetime, timedelta  


# Define a type alias for the handler
OutputHandlerType = Optional[Callable[[str, str], None]]

# Define the path to the keyword file relative to this package


keyword_file_path = PROJECT_ROOT / "datasets" / "tianshu_v1" / "template" / "keyword-list.txt"


def load_keywords(filepath):
    """Loads keywords from a file, one per line."""
    keywords = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                word = line.strip()
                if word:  # Avoid adding empty lines
                    keywords.append(word)
    except FileNotFoundError:
        print(
            f"Warning: Keyword file not found at {filepath}. Using default keywords.",
            file=sys.stderr,
        )
    return keywords


def apply_random_keywords(current_random_seed):
    """Apply random keyword mapping based on the provided seed."""
    keywords = load_keywords(keyword_file_path)
    # Seed the random number generator specifically for shuffling
    random.seed(current_random_seed)
    # Shuffle the list in place
    random.shuffle(keywords)

    try:
        original_token_types = list(mamba.lexer._original_reserved.values())
        num_original_keywords = len(original_token_types)

        # Check if the loaded list has enough keywords
        if len(keywords) < num_original_keywords:
            raise mamba.exceptions.InterpreterException(
                f"Keyword file is too short: Expected at least {num_original_keywords} keywords, got {len(keywords)}."
            )

        # Take only the first 'num_original_keywords' from the shuffled list
        keywords_to_use = keywords[:num_original_keywords]

        # Create the mapping using the subset of keywords
        new_reserved_map = dict(zip(keywords_to_use, original_token_types))
        mamba.lexer.override_reserved_words(new_reserved_map)
    except mamba.exceptions.InterpreterException as e:
        print(f"Error overriding keywords: {e}", file=sys.stderr)
        raise
    return keywords


# Add output_handler and input_handler parameters
def execute(
    source: str,
    show_ast: bool = False,
    disable_warnings: bool = True,
    random_seed: int = None,
    random_seed_was_set: bool = False,
    output_handler: OutputHandlerType = None,
    input_handler: Optional[Callable[[str], str]] = None,
    max_execution_time_seconds = None,
):  # New parameter

    p.disable_warnings = disable_warnings

    # Store the handlers where AST nodes can access them
    original_output_handler = mamba.ast.get_output_handler()
    original_input_handler = mamba.ast.get_input_handler()
    mamba.ast.set_output_handler(output_handler)
    mamba.ast.set_input_handler(input_handler)

    if max_execution_time_seconds:
        end_time = datetime.now() + timedelta(seconds=max_execution_time_seconds)   

    try:
        # Keyword override logic is now handled in mamba.py before this function is called.
        # If embedding, the caller needs to handle keyword setup *before* calling execute.

        # Initialize random seed if it was explicitly provided
        if random_seed_was_set:
            random.seed(random_seed)
        res = p.get_parser().parse(source)
        # Pass seed info to environment setup if needed, though seeding is done above now.
        # If environment needs to know *if* seed was set, pass random_seed_was_set
        # mamba.ast.symbols.reset()
        environment.declare_env(mamba.ast.symbols)

        for node in res.children:
            node.eval()

        if show_ast:
            print("\n\n" + "=" * 80, " == Syntax tree ==")

            # Decide how to handle AST output - maybe use the handler too?
            ast_str = "\n\n" + "=" * 80 + " == Syntax tree ==\n"
            ast_str += pprint.pformat(res.children) + "\n"
            ast_str += pprint.pformat(mamba.ast.symbols.table())
            if output_handler:
                output_handler(ast_str, "stdout")  # Or a different stream type? 'debug'?
            else:
                print(ast_str)

    except Exception as e:
        error_message = f"{e.__class__.__name__}: {str(e)}"
        if output_handler:
            output_handler(error_message, "stderr")  # Use handler for errors
        else:
            print(error_message, file=sys.stderr)  # Original behavior

        if not disable_warnings:
            raise e  # Re-raise if warnings (and thus detailed exceptions) are enabled
    finally:
        # Ensure the handlers are reset even if errors occur
        mamba.ast.set_output_handler(original_output_handler)
        mamba.ast.set_input_handler(original_input_handler)

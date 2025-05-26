import subprocess
import multiprocessing
import datetime
import re
import sys
from pathlib import Path
import importlib.util
import os
import argparse

# This script automates and parallelizes the execution of LLM benchmark tests.
# It dynamically discovers LLM identifiers from 'test_llm_ability.py',
# allows filtering tests by provider and/or model, and can run tests in parallel
# processes or perform a dry run to show the commands that would be executed.

# Define the project root using pathlib.Path.
# This script is located in 'scripts/', so its parent directory is the project root.
PROJECT_ROOT = Path(__file__).parent.parent

# Add the project root to sys.path. This is crucial for allowing Python to
# import modules from the project structure (e.g., 'tianshu_bench.benchmarks.test_llm_ability').
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Dynamically load LLM_IDENTIFIERS from 'test_llm_ability.py'.
# This ensures that the script uses the same list of LLM models that the tests themselves are configured for.
ALL_LLM_IDENTIFIERS = []
try:
    # Construct the path to the test_llm_ability.py file.
    test_llm_ability_path = PROJECT_ROOT / "tianshu_bench" / "benchmarks" / "test_llm_ability.py"
    
    # Create a module specification from the file path.
    spec = importlib.util.spec_from_file_location(
        "test_llm_ability", test_llm_ability_path
    )
    # Create a new module based on the specification.
    test_llm_ability_module = importlib.util.module_from_spec(spec)
    # Execute the module's code to populate its namespace (including LLM_IDENTIFIERS).
    spec.loader.exec_module(test_llm_ability_module)
    # Retrieve the LLM_IDENTIFIERS list from the loaded module.
    ALL_LLM_IDENTIFIERS = test_llm_ability_module.LLM_IDENTIFIERS
except Exception as e:
    print(f"Error loading LLM_IDENTIFIERS from test_llm_ability.py: {e}")
    print("Please ensure the path to test_llm_ability.py is correct and the file is accessible.")
    sys.exit(1)

# Define the base pytest command parts.
# This command targets the specific multi-shot benchmark function.
PYTEST_BASE_COMMAND = [
    sys.executable,  # Uses the Python interpreter that is running this script.
    "-m",
    "pytest",
    "-svv",  # -s: show stdout/stderr, -v: verbose output.
    "tianshu_bench/benchmarks/test_llm_ability.py::test_execute_generated_multi_shot",
]

def run_pytest_for_llm(llm_identifier: str, dry_run: bool):
    """
    Constructs a pytest command for a specific LLM identifier and either executes it
    or prints it if in dry-run mode.

    Args:
        llm_identifier (str): The unique identifier for the LLM model (e.g., "ollama/phi4:14b-q4_K_M").
        dry_run (bool): If True, prints the command without executing it.
    """
    # Sanitize the LLM identifier to create a valid filename for the report log.
    # Replaces characters like '/', ':', '.' with '-'.
    sanitized_llm_id = re.sub(r'[/:.]', '-', llm_identifier)
    
    # Generate a timestamp for unique report log filenames.
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")

    # Construct the report log filename.
    report_log_filename = f"report-log-{sanitized_llm_id}-{timestamp}.json"

    # Construct the full pytest command for this specific LLM.
    # It includes:
    # - '--report-log': to save test results to a unique JSON file.
    # - '-k': pytest's keyword expression to filter tests, ensuring only tests
    #         parameterized with the current `llm_identifier` are run.
    command = PYTEST_BASE_COMMAND + [
        f"--report-log={report_log_filename}",
        "-k",
        llm_identifier, # Use the full identifier for precise filtering by pytest.
    ]

    if dry_run:
        # In dry-run mode, just print the command and return.
        print(f"[DRY RUN] Would execute for LLM: {llm_identifier}")
        print(f"[DRY RUN] Command: {' '.join(command)}\n")
        return

    print(f"--- Starting tests for LLM: {llm_identifier} ---")
    print(f"Command: {' '.join(command)}")

    try:
        # Execute the pytest command as a subprocess.
        # 'check=False' prevents an exception from being raised if the subprocess
        # returns a non-zero exit code (e.g., due to test failures), allowing
        # other parallel processes to continue.
        result = subprocess.run(command, check=False) 
        
        # Report the outcome of the test run.
        if result.returncode == 0:
            print(f"--- Successfully completed tests for LLM: {llm_identifier} ---")
        elif result.returncode == 5: # pytest exit code 5 means no tests were collected.
            print(f"--- No tests collected for LLM: {llm_identifier}. Check -k filter or LLM_IDENTIFIERS. ---")
        else:
            print(f"--- Tests for LLM: {llm_identifier} finished with exit code {result.returncode} (failures or errors occurred). ---")
    except Exception as e:
        # Catch any unexpected errors during subprocess execution.
        print(f"--- An error occurred while running tests for LLM {llm_identifier}: {e} ---")

if __name__ == "__main__":
    # Set up command-line argument parsing.
    parser = argparse.ArgumentParser(description="Run LLM benchmarks in parallel.")
    
    # Add the --dry-run argument.
    parser.add_argument(
        "--dry-run",
        action="store_true", # This makes it a boolean flag.
        help="Print commands without executing them."
    )
    
    # Add the --provider filter argument.
    parser.add_argument(
        "--provider",
        type=str,
        help="Comma-separated list of providers to include (e.g., 'ollama,chutes')."
    )
    
    # Add the --model filter argument.
    parser.add_argument(
        "--model",
        type=str,
        help="Comma-separated list of model name substrings to include (e.g., 'phi4,qwen')."
    )
    args = parser.parse_args()

    print("Collecting LLM identifiers...")
    
    llm_ids_to_test = [] # This list will hold the LLM identifiers after filtering.
    
    # Apply filters based on command-line arguments.
    for llm_id in ALL_LLM_IDENTIFIERS:
        include_provider = True # Assume inclusion by provider unless filtered out.
        include_model = True    # Assume inclusion by model unless filtered out.

        # Split the LLM identifier into provider and model name.
        # Example: "ollama/phi4:14b-q4_K_M" -> provider="ollama", model_name="phi4:14b-q4_K_M"
        provider, model_name = llm_id.split('/', 1) if '/' in llm_id else (llm_id, '')

        # Filter by provider if --provider argument is provided.
        if args.provider:
            allowed_providers = [p.strip().lower() for p in args.provider.split(',')]
            if provider.lower() not in allowed_providers:
                include_provider = False
        
        # Filter by model name substring if --model argument is provided.
        if args.model:
            allowed_model_substrings = [m.strip().lower() for m in args.model.split(',')]
            # Check if any of the provided substrings are present in the model name (case-insensitive).
            if not any(sub in model_name.lower() for sub in allowed_model_substrings):
                include_model = False
        
        # If both provider and model filters (if specified) allow the LLM, add it to the list.
        if include_provider and include_model:
            llm_ids_to_test.append(llm_id)

    # Check if any LLM identifiers remain after filtering.
    if not llm_ids_to_test:
        print("No LLM identifiers found matching the specified filters. Exiting.")
        sys.exit(0)

    print(f"Found {len(llm_ids_to_test)} LLM models to test (after filtering):")
    for llm_id in llm_ids_to_test:
        print(f"- {llm_id}")

    # Determine whether to run in dry-run mode or execute tests in parallel.
    if args.dry_run:
        print("\n--- DRY RUN MODE: Commands will be printed but NOT executed ---")
        # In dry-run mode, iterate sequentially and print commands.
        for llm_id in llm_ids_to_test:
            run_pytest_for_llm(llm_id, dry_run=True)
        print("\n--- Dry run completed ---")
    else:
        # Determine the number of parallel processes to use.
        # It takes the minimum of the number of LLMs to test and the CPU count,
        # to avoid creating more processes than necessary or available cores.
        num_processes = min(len(llm_ids_to_test), multiprocessing.cpu_count()) 
        print(f"\nRunning tests in parallel using {num_processes} processes...")

        # Use a multiprocessing Pool to distribute the test runs across multiple processes.
        # `pool.starmap` is used because `run_pytest_for_llm` takes multiple arguments
        # (llm_identifier and dry_run). We pass a list of tuples, where each tuple
        # contains the arguments for one call to `run_pytest_for_llm`.
        with multiprocessing.Pool(processes=num_processes) as pool:
            pool.starmap(run_pytest_for_llm, [(llm_id, False) for llm_id in llm_ids_to_test])

        print("\n--- All parallel test runs completed ---")

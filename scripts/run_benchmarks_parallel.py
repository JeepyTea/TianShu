import subprocess
import multiprocessing
import datetime
import re
import sys
from pathlib import Path
import importlib.util
import os
import argparse

# Define the project root using pathlib.Path
# This script is in 'scripts/', so its parent is the project root.
PROJECT_ROOT = Path(__file__).parent.parent

# Add the project root to sys.path to allow importing modules
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Dynamically load LLM_IDENTIFIERS from test_llm_ability.py
ALL_LLM_IDENTIFIERS = []
try:
    spec = importlib.util.spec_from_file_location(
        "test_llm_ability", PROJECT_ROOT / "tianshu_bench" / "benchmarks" / "test_llm_ability.py"
    )
    test_llm_ability_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(test_llm_ability_module)
    ALL_LLM_IDENTIFIERS = test_llm_ability_module.LLM_IDENTIFIERS
except Exception as e:
    print(f"Error loading LLM_IDENTIFIERS from test_llm_ability.py: {e}")
    print("Please ensure the path to test_llm_ability.py is correct and the file is accessible.")
    sys.exit(1)

# Define the base pytest command parts
PYTEST_BASE_COMMAND = [
    sys.executable,  # Use the current Python interpreter
    "-m",
    "pytest",
    "-svv",
    "tianshu_bench/benchmarks/test_llm_ability.py::test_execute_generated_multi_shot",
]

def run_pytest_for_llm(llm_identifier: str, dry_run: bool):
    """
    Constructs and runs (or prints) a pytest command for a specific LLM identifier.
    """
    # Sanitize the LLM identifier for use in a filename
    sanitized_llm_id = re.sub(r'[/:.]', '-', llm_identifier)
    
    # Generate a timestamp for the report log
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")

    # Construct the report log filename
    report_log_filename = f"report-log-{sanitized_llm_id}-{timestamp}.json"

    # Construct the full pytest command for this LLM
    command = PYTEST_BASE_COMMAND + [
        f"--report-log={report_log_filename}",
        "-k",
        llm_identifier, # Use the full identifier for precise filtering
    ]

    if dry_run:
        print(f"[DRY RUN] Would execute for LLM: {llm_identifier}")
        print(f"[DRY RUN] Command: {' '.join(command)}\n")
        return

    print(f"--- Starting tests for LLM: {llm_identifier} ---")
    print(f"Command: {' '.join(command)}")

    try:
        # Execute the command
        result = subprocess.run(command, check=False) 
        
        if result.returncode == 0:
            print(f"--- Successfully completed tests for LLM: {llm_identifier} ---")
        elif result.returncode == 5: # pytest exit code 5 means no tests were collected
            print(f"--- No tests collected for LLM: {llm_identifier}. Check -k filter or LLM_IDENTIFIERS. ---")
        else:
            print(f"--- Tests for LLM: {llm_identifier} finished with exit code {result.returncode} (failures or errors occurred). ---")
    except Exception as e:
        print(f"--- An error occurred while running tests for LLM {llm_identifier}: {e} ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run LLM benchmarks in parallel.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them."
    )
    parser.add_argument(
        "--provider",
        type=str,
        help="Comma-separated list of providers to include (e.g., 'ollama,chutes')."
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Comma-separated list of model name substrings to include (e.g., 'phi4,qwen')."
    )
    args = parser.parse_args()

    print("Collecting LLM identifiers...")
    
    llm_ids_to_test = []
    
    # Apply filters
    for llm_id in ALL_LLM_IDENTIFIERS:
        include_provider = True
        include_model = True

        provider, model_name = llm_id.split('/', 1) if '/' in llm_id else (llm_id, '')

        if args.provider:
            allowed_providers = [p.strip().lower() for p in args.provider.split(',')]
            if provider.lower() not in allowed_providers:
                include_provider = False
        
        if args.model:
            allowed_model_substrings = [m.strip().lower() for m in args.model.split(',')]
            # Check if any of the substrings are in the model_name
            if not any(sub in model_name.lower() for sub in allowed_model_substrings):
                include_model = False
        
        if include_provider and include_model:
            llm_ids_to_test.append(llm_id)

    if not llm_ids_to_test:
        print("No LLM identifiers found matching the specified filters. Exiting.")
        sys.exit(0)

    print(f"Found {len(llm_ids_to_test)} LLM models to test (after filtering):")
    for llm_id in llm_ids_to_test:
        print(f"- {llm_id}")

    if args.dry_run:
        print("\n--- DRY RUN MODE: Commands will be printed but NOT executed ---")
        for llm_id in llm_ids_to_test:
            run_pytest_for_llm(llm_id, dry_run=True)
        print("\n--- Dry run completed ---")
    else:
        # Determine the number of parallel processes
        num_processes = min(len(llm_ids_to_test), multiprocessing.cpu_count()) 
        print(f"\nRunning tests in parallel using {num_processes} processes...")

        with multiprocessing.Pool(processes=num_processes) as pool:
            pool.starmap(run_pytest_for_llm, [(llm_id, False) for llm_id in llm_ids_to_test])

        print("\n--- All parallel test runs completed ---")

import json
import sys
import csv
from collections import defaultdict
import argparse
from pathlib import Path

def load_problem_definitions():
    """Load problem definitions from the CSV file to map problem IDs to names."""
    problem_map = {}
    project_root = Path(__file__).parent.parent
    csv_path = project_root / "datasets" / "tianshu_v1" / "problem_definitions.csv"

    with open(csv_path, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            problem_id = row["problem_id"]
            problem_name = row["problem_name"]
            # Store unique problem ID to name mappings
            if problem_id not in problem_map:
                problem_map[problem_id] = problem_name

    return problem_map

def load_test_case_to_problem_mapping():
    """Load mapping from test case numbers to problem IDs, names, and difficulty."""
    test_case_map = {}
    project_root = Path(__file__).parent.parent
    csv_path = project_root / "datasets" / "tianshu_v1" / "problem_definitions.csv"

    with open(csv_path, "r") as csvfile:
        reader = list(csv.DictReader(csvfile))
        for i, row in enumerate(reader):
            test_case_map[f"test_case{i}"] = {
                "problem_id": row["problem_id"],
                "problem_name": row["problem_name"],
                "difficulty": row["difficulty"]
            }

    return test_case_map

def analyze_multishot_report(log_files, filter_difficulty_2_plus=False):
    """
    Analyzes one or more pytest report log files, combining statistics.

    Args:
        log_files (list): A list of file paths to the report logs (each line is a JSON object).
        filter_difficulty_2_plus (bool): If True, only analyze problems with difficulty 2 or greater.
        
    Returns:
        dict: A dictionary containing combined statistics by model, shots, seed, test case, and problem.
    """
    # Load problem definitions to map IDs to names
    problem_definitions = load_problem_definitions()

    # Load test case to problem mapping
    test_case_mapping = load_test_case_to_problem_mapping()

    # Initialize statistics containers
    stats_by_model = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "skipped": 0})
    stats_by_model_difficulty = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "skipped": 0})
    stats_by_shots = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "skipped": 0})
    stats_by_seed = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "skipped": 0})
    stats_by_test_case = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "skipped": 0})
    stats_by_problem = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "skipped": 0})

    # Track seen tests to detect duplicates
    seen_tests = set()
    count = 0

    # Process each log file provided
    for log_file in log_files:
        try:
            with open(log_file, 'r') as f:
                for line in f:

                    try:
                        entry = json.loads(line)
                        # Only process test results
                        if entry.get('$report_type') == 'TestReport' and entry.get('when') == 'call':
                            nodeid = entry.get('nodeid', '')

                            # Extract parameters from the test nodeid
                            if 'test_execute_generated_multi_shot' in nodeid:
                                # Parse the parameters from the nodeid
                                # Format: test_execute_generated_multi_shot[chutes/chutesai/Llama-4-Scout-17B-16E-Instruct-4-2-test_case5]

                                # Extract the part between square brackets
                                if '[' in nodeid and ']' in nodeid:
                                    params_part = nodeid.split('[')[1].split(']')[0]

                                    # Split by hyphens to get components
                                    parts = params_part.split('-')

                                    # The last part is the test case
                                    test_case = parts[-1]

                                    # The second-to-last part is the language seed
                                    seed = parts[-2]

                                    # The third-to-last part is the number of shots
                                    shots = parts[-3]

                                    # Everything before that is the model name
                                    model_name = '-'.join(parts[:-3])

                                    # Get problem ID, name, and difficulty from test case mapping
                                    if test_case in test_case_mapping:
                                        problem_id = test_case_mapping[test_case]["problem_id"]
                                        problem_name = test_case_mapping[test_case]["problem_name"]
                                        difficulty = test_case_mapping[test_case]["difficulty"]
                                    else:
                                        problem_id = "unknown"
                                        problem_name = "Unknown Problem"
                                        difficulty = "unknown"

                                    # Apply difficulty filter if enabled
                                    if filter_difficulty_2_plus:
                                        numeric_difficulty = 0  # Default to 0 if conversion fails or difficulty is not numeric
                                        try:
                                            numeric_difficulty = int(difficulty)
                                        except ValueError:
                                            # If difficulty is not a valid number, numeric_difficulty remains 0.
                                            # This effectively treats non-numeric difficulties as less than 2,
                                            # causing them to be filtered out when --mini is active.
                                            pass

                                        if numeric_difficulty < 2:
                                            continue # Skip this entry if difficulty is less than 2

                                    problem_key = f"{problem_id}: {problem_name}"
                                    model_difficulty_key = f"{model_name} (Difficulty {difficulty})"

                                    # Determine if the test passed or failed
                                    outcome = entry.get('outcome', 'unknown')

                                    # Create a unique test identifier
                                    test_id = f"{model_name}-{shots}-{seed}-{test_case}"

                                    # Check if we've seen this test before
                                    if test_id in seen_tests:
                                        print(f"WARNING: Duplicate test found: {test_id}")
                                    else:
                                        seen_tests.add(test_id)

                                    # Update statistics
                                    stats_by_model[model_name]["total"] += 1
                                    stats_by_model_difficulty[model_difficulty_key]["total"] += 1
                                    stats_by_shots[shots]["total"] += 1
                                    stats_by_seed[seed]["total"] += 1
                                    stats_by_test_case[test_case]["total"] += 1
                                    stats_by_problem[problem_key]["total"] += 1

                                    if outcome == 'passed':
                                        stats_by_model[model_name]["passed"] += 1
                                        stats_by_model_difficulty[model_difficulty_key]["passed"] += 1
                                        stats_by_shots[shots]["passed"] += 1
                                        stats_by_seed[seed]["passed"] += 1
                                        stats_by_test_case[test_case]["passed"] += 1
                                        stats_by_problem[problem_key]["passed"] += 1
                                    elif outcome == 'failed':
                                        stats_by_model[model_name]["failed"] += 1
                                        stats_by_model_difficulty[model_difficulty_key]["failed"] += 1
                                        stats_by_shots[shots]["failed"] += 1
                                        stats_by_seed[seed]["failed"] += 1
                                        stats_by_test_case[test_case]["failed"] += 1
                                        stats_by_problem[problem_key]["failed"] += 1
                                    elif outcome == 'skipped':
                                        stats_by_model[model_name]["skipped"] += 1
                                        stats_by_model_difficulty[model_difficulty_key]["skipped"] += 1
                                        stats_by_shots[shots]["skipped"] += 1
                                        stats_by_seed[seed]["skipped"] += 1
                                        stats_by_test_case[test_case]["skipped"] += 1
                                        stats_by_problem[problem_key]["skipped"] += 1
                                    else:
                                        print(f"Got unknown outcome type {outcome}")
                                else:
                                    print(f"Got unknown nodeid format {nodeid}")
                            else:
                                print(f"Got unknown ???")
                    except json.JSONDecodeError:
                        # Skip lines that are not valid JSON
                        print(f"Got invalid JSON {line}")
                        continue
        except FileNotFoundError:
            print(f"Warning: Report log file not found: {log_file}. Skipping this file.", file=sys.stderr)
            continue
        except Exception as e:
            print(f"Error processing file {log_file}: {e}", file=sys.stderr)
            continue

    # Calculate success rates
    for stats_dict in [stats_by_model, stats_by_model_difficulty, stats_by_shots, stats_by_seed, stats_by_test_case, stats_by_problem]:
        for key, value in stats_dict.items():
            attempted = value["passed"] + value["failed"]
            value["attempted"] = attempted
            value["total"] = attempted + value["skipped"]
            if attempted > 0:
                value["success_rate"] = round(value["passed"] / attempted * 100, 2)
            else:
                value["success_rate"] = 0


    return {
        "by_model": dict(stats_by_model),
        "by_model_difficulty": dict(stats_by_model_difficulty),
        "by_shots": dict(stats_by_shots),
        "by_seed": dict(stats_by_seed),
        "by_test_case": dict(stats_by_test_case),
        "by_problem": dict(stats_by_problem)
    }

def print_stats(stats):
    print("\n=== Statistics by Model ===")
    for model, data in sorted(stats["by_model"].items()):
        print(f"{model}: {data['passed']}/{data['attempted']} ({data['success_rate']}%) passed, {data['failed']} failed, {data['skipped']} skipped, {data['total']} total ")

    print("\n=== Statistics by Model and Difficulty ===")
    for model_difficulty, data in sorted(stats["by_model_difficulty"].items()):
        print(f"{model_difficulty}: {data['passed']}/{data['attempted']} ({data['success_rate']}%) passed, {data['failed']} failed, {data['skipped']} skipped, {data['total']} total ")

    print("\n=== Statistics by Number of Shots ===")
    for shots, data in sorted(stats["by_shots"].items(), key=lambda x: int(x[0]) if x[0].isdigit() else float('inf')):
        print(f"{shots} shots: {data['passed']}/{data['attempted']} ({data['success_rate']}%) passed, {data['failed']} failed, {data['skipped']} skipped, {data['total']} total ")

    print("\n=== Statistics by Language Seed ===")
    for seed, data in sorted(stats["by_seed"].items(), key=lambda x: int(x[0]) if x[0].isdigit() else float('inf')):
        print(f"Seed {seed}: {data['passed']}/{data['attempted']} ({data['success_rate']}%) passed, {data['failed']} failed, {data['skipped']} skipped, {data['total']} total")

    print("\n=== Statistics by Test Case ===")
    # Extract numeric part from test_case string for proper numerical sorting
    for test_case, data in sorted(stats["by_test_case"].items(), key=lambda x: int(x[0].replace('test_case', '')) if x[0].startswith('test_case') and x[0][9:].isdigit() else float('inf')):
        print(f"{test_case}: {data['passed']}/{data['attempted']} ({data['success_rate']}%) passed, {data['failed']} failed, {data['skipped']} skipped, {data['total']} total ")

    print("\n=== Statistics by Problem ===")
    for problem, data in sorted(stats["by_problem"].items()):
        print(f"{problem}: {data['passed']}/{data['attempted']} ({data['success_rate']}%) passed, {data['failed']} failed, {data['skipped']} skipped, {data['total']} total")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze pytest multishot report logs.")
    parser.add_argument("log_files", nargs="+", help="One or more pytest report log files.")
    parser.add_argument("--mini", action="store_true",
                        help="Only analyze results for problem difficulty 2 or greater.")

    args = parser.parse_args()

    # The log_files are in args.log_files, and --mini status in args.mini
    stats = analyze_multishot_report(args.log_files, filter_difficulty_2_plus=args.mini)

    print_stats(stats)

    # Save the combined statistics to a JSON file
    with open("multishot_test_statistics.json", "w") as f:
        json.dump(stats, f, indent=2)

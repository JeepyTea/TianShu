
import json
import sys
from collections import defaultdict

def analyze_report_log(log_file):
    # Initialize statistics containers
    stats_by_llm = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
    stats_by_problem = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
    stats_by_seed = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})

    # Read the report log line by line (each line is a JSON object)
    with open(log_file, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)

                # Only process test results
                if entry.get('$report_type') == 'TestReport' and entry.get('when') == 'call':
                    nodeid = entry.get('nodeid', '')

                    # Extract parameters from the test nodeid
                    if 'test_generated_program_with_mamba_execution' in nodeid:
                        # Parse the parameters from the nodeid
                        # The format is more complex than simple splitting by '-'
                        # We need to extract the LLM identifier, seed, and problem ID correctly
                        
                        # Extract the part between square brackets
                        params_part = nodeid.split('[')[1].split(']')[0]
                        
                        # For LLM identifier, look for ollama/ pattern
                        if 'ollama/' in params_part:
                            llm_parts = params_part.split('-')
                            # The LLM identifier might contain hyphens, so we need to find where it ends
                            # It typically ends before a number (the seed)
                            llm_end_idx = next((i for i, part in enumerate(llm_parts) if part.isdigit()), 1)
                            llm_identifier = '-'.join(llm_parts[:llm_end_idx])
                            
                            # The seed is the next part after the LLM identifier
                            seed = llm_parts[llm_end_idx]
                            
                            # The problem ID is the last part
                            problem_id = llm_parts[-1]
                            
                            # If problem_id contains non-numeric characters and isn't a test_case format,
                            # it might be part of the LLM identifier
                            if not problem_id.isdigit() and not problem_id.startswith('test_case'):
                                problem_id = llm_parts[-2] if len(llm_parts) > llm_end_idx + 1 else "unknown"
                        else:
                            # Fallback parsing if the format is different
                            parts = params_part.split('-')
                            llm_identifier = parts[0] if len(parts) > 0 else "unknown"
                            seed = parts[1] if len(parts) > 1 else "unknown"
                            problem_id = parts[2] if len(parts) > 2 else "unknown"
                        
                        # Determine if the test passed or failed
                        outcome = entry.get('outcome', 'unknown')
                        
                        # Update statistics
                        stats_by_llm[llm_identifier]["total"] += 1
                        stats_by_problem[problem_id]["total"] += 1
                        stats_by_seed[seed]["total"] += 1
                        
                        if outcome == 'passed':
                            stats_by_llm[llm_identifier]["passed"] += 1
                            stats_by_problem[problem_id]["passed"] += 1
                            stats_by_seed[seed]["passed"] += 1
                        elif outcome == 'failed':
                            stats_by_llm[llm_identifier]["failed"] += 1
                            stats_by_problem[problem_id]["failed"] += 1
                            stats_by_seed[seed]["failed"] += 1
            except json.JSONDecodeError:
                continue

    # Calculate success rates
    for stats_dict in [stats_by_llm, stats_by_problem, stats_by_seed]:
        for key, value in stats_dict.items():
            if value["total"] > 0:
                value["success_rate"] = round(value["passed"] / value["total"] * 100, 2)
            else:
                value["success_rate"] = 0

    return {
        "by_llm": dict(stats_by_llm),
        "by_problem": dict(stats_by_problem),
        "by_seed": dict(stats_by_seed)
    }

def print_stats(stats):
    print("\n=== Statistics by LLM ===")
    for llm, data in sorted(stats["by_llm"].items()):
        print(f"{llm}: {data['passed']}/{data['total']} passed ({data['success_rate']}%)")

    print("\n=== Statistics by Problem ID ===")
    for problem, data in sorted(stats["by_problem"].items()):
        print(f"Problem {problem}: {data['passed']}/{data['total']} passed ({data['success_rate']}%)")

    print("\n=== Statistics by Random Seed ===")
    for seed, data in sorted(stats["by_seed"].items()):
        print(f"Seed {seed}: {data['passed']}/{data['total']} passed ({data['success_rate']}%)")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_report.py <report_log_file>")
        sys.exit(1)

    log_file = sys.argv[1]
    stats = analyze_report_log(log_file)
    print_stats(stats)

    # Optionally save the statistics to a JSON file
    with open("test_statistics_summary.json", "w") as f:
        json.dump(stats, f, indent=2)

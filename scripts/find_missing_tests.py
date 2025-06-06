#!/usr/bin/env python3
"""
Script to find missing pytest parameter combinations by comparing expected vs executed tests.
Usage: python find_missing_pytest_combinations.py <report_log_file.json>
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def normalize_nodeid(nodeid, full_test_path=None):
    """Normalize nodeids to handle path differences between expected and executed tests."""
    if not nodeid:
        return nodeid
    
    # If we have a full test path and the nodeid doesn't contain the full path,
    # try to construct the full nodeid
    if full_test_path and '::' in nodeid and not nodeid.startswith(full_test_path.split('::')[0]):
        # Extract just the filename from the nodeid
        if '::' in nodeid:
            parts = nodeid.split('::', 1)
            filename = parts[0]
            test_part = parts[1]
            
            # If the filename is just the basename, prepend the full path
            if '/' not in filename and full_test_path:
                base_path = full_test_path.split('::')[0]
                if base_path.endswith('/' + filename):
                    return f"{base_path}::{test_part}"
    
    return nodeid


def load_executed_nodeids(log_file_path):
    """Load executed test nodeids from pytest JSON log file."""
    executed_nodeids = set()
    
    try:
        with open(log_file_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get('$report_type') == 'TestReport' and 'nodeid' in entry:
                        executed_nodeids.add(entry['nodeid'])
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print(f"Error: Log file '{log_file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading log file: {e}")
        sys.exit(1)
    
    return executed_nodeids


def get_expected_nodeids(test_path, filter_expression=None):
    """Get all expected test nodeids using pytest --collect-only."""
    # Try different pytest collect commands to handle various output formats
    commands_to_try = [
        ['python', '-m', 'pytest', '--collect-only', '-q', test_path],
    ]
    
    if filter_expression:
        for cmd in commands_to_try:
            cmd.extend(['-k', filter_expression])
    
    expected_nodeids = set()
    
    for cmd in commands_to_try:
        try:
            print(f"Trying command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            #print(f"Raw output from pytest --collect-only:")
            #print("=" * 50)
            #print(result.stdout)
            #print("=" * 50)
            
            # Parse the output - try multiple patterns
            lines = result.stdout.split('\n')
            current_module = None
            found_count = 0
            output_elipses = False
            
            for line in lines:
                line_stripped = line.strip()
                
                # Pattern 1: Direct nodeid format (most common with -q)
                if '::' in line_stripped and '[' in line_stripped and ']' in line_stripped:
                    if not line_stripped.startswith('<') and not line_stripped.startswith('='):
                        # Normalize the nodeid to match the full path format
                        normalized_nodeid = normalize_nodeid(line_stripped, test_path)
                        expected_nodeids.add(normalized_nodeid)
                
                # Pattern 2: Parse tree format with <Function> tags
                elif line_stripped.startswith('<Module ') and line_stripped.endswith('>'):
                    # Extract module name: <Module test_llm_ability.py> -> test_llm_ability.py
                    module_match = line_stripped[8:-1]  # Remove '<Module ' and '>'
                    if '/' in module_match:
                        current_module = module_match
                    else:
                        # Construct full path from test_path
                        if test_path.endswith('.py'):
                            current_module = test_path
                        else:
                            current_module = module_match
                
                elif line_stripped.startswith('<Function ') and line_stripped.endswith('>'):
                    # Extract function name with parameters: <Function test_execute_generated_multi_shot[params]>
                    function_full = line_stripped[10:-1]  # Remove '<Function ' and '>'
                    
                    if current_module:
                        # Construct full nodeid: module::function
                        nodeid = f"{current_module}::{function_full}"
                        normalized_nodeid = normalize_nodeid(nodeid, test_path)
                        expected_nodeids.add(normalized_nodeid)
                        found_count = found_count+1
                        if found_count<10:
                            print(f"Found test: {normalized_nodeid}")
                        elif not output_elipses:
                            print("...")
                            output_elipses = True
                            
                    else:
                        # Fallback: try to construct from test_path
                        if '::' in test_path:
                            base_path = test_path.rsplit('::', 1)[0]
                            nodeid = f"{base_path}::{function_full}"
                            normalized_nodeid = normalize_nodeid(nodeid, test_path)
                            expected_nodeids.add(normalized_nodeid)
                
                # Pattern 3: Lines that look like test paths (fallback)
                elif '::test_' in line_stripped and not line_stripped.startswith('<'):
                    normalized_nodeid = normalize_nodeid(line_stripped, test_path)
                    expected_nodeids.add(normalized_nodeid)
            
            # If we found tests, break out of the loop
            if expected_nodeids:
                print(f"Successfully collected {len(expected_nodeids)} tests")
                break
                
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {' '.join(cmd)}")
            print(f"Error: {e}")
            print(f"Stderr: {e.stderr}")
            continue
    
    if not expected_nodeids:
        print("Warning: No tests found. Let's try a more verbose approach...")
        
        # Try without -q flag to see more detailed output
        cmd = ['python', '-m', 'pytest', '--collect-only', '-v', test_path]
        if filter_expression:
            cmd.extend(['-k', filter_expression])
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("Verbose output:")
            print(result.stdout)
            
            # Try to extract nodeids from verbose output
            for line in result.stdout.split('\n'):
                if '::test_' in line and ('PASSED' in line or 'FAILED' in line or line.strip().endswith('>')):
                    # Extract just the nodeid part
                    parts = line.split()
                    for part in parts:
                        if '::test_' in part and '[' in part:
                            normalized_nodeid = normalize_nodeid(part, test_path)
                            expected_nodeids.add(normalized_nodeid)
                            
        except subprocess.CalledProcessError as e:
            print(f"Verbose command also failed: {e}")
    
    return expected_nodeids


def extract_test_info_from_log(log_file_path):
    """Extract test path and filter information from the log file if available."""
    # This is a basic implementation - you might need to adjust based on your log format
    # For now, we'll return None and require manual specification
    return None, None


def main():
    parser = argparse.ArgumentParser(
        description="Find missing pytest parameter combinations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python find_missing_pytest_combinations.py results/report-log-2024-01-15T14:30.json
  
  python find_missing_pytest_combinations.py results/report-log-2024-01-15T14:30.json \\
    --test-path "tianshu_bench/benchmarks/test_llm_ability.py::test_execute_generated_multi_shot" \\
    --filter "chutes/ and DeepSeek"
        """
    )
    
    parser.add_argument(
        'log_file', 
        help='Path to the pytest JSON report log file'
    )
    
    parser.add_argument(
        '--test-path', 
        help='Specific test path to check (e.g., module::test_function)'
    )
    
    parser.add_argument(
        '--filter', '-k',
        help='Test filter expression (same as pytest -k option)'
    )
    
    parser.add_argument(
        '--output-missing',
        help='Output file to save missing test nodeids'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show debug information about nodeid matching'
    )
    
    args = parser.parse_args()
    
    # Load executed tests from log file
    print(f"Loading executed tests from: {args.log_file}")
    executed_nodeids = load_executed_nodeids(args.log_file)
    print(f"Found {len(executed_nodeids)} executed tests")
    
    # Get expected tests
    if args.test_path:
        test_path = args.test_path
        filter_expr = args.filter
    else:
        # Try to extract from log file or use current directory
        test_path, filter_expr = extract_test_info_from_log(args.log_file)
        if not test_path:
            print("Warning: No test path specified. Using current directory.")
            print("Use --test-path to specify a specific test path for more accurate results.")
            test_path = "."
    
    print(f"Getting expected tests from: {test_path}")
    if filter_expr:
        print(f"Using filter: {filter_expr}")
    
    expected_nodeids = get_expected_nodeids(test_path, filter_expr)
    print(f"Found {len(expected_nodeids)} expected tests")

    if args.debug:
        print(f"\n=== DEBUG: NODEID COMPARISON ===")
        print("Sample expected nodeids:")
        for nodeid in sorted(list(expected_nodeids))[:5]:
            print(f"  Expected: {nodeid}")
        print("Sample executed nodeids:")
        for nodeid in sorted(list(executed_nodeids))[:5]:
            print(f"  Executed: {nodeid}")
        
        # Check for any exact matches
        exact_matches = expected_nodeids.intersection(executed_nodeids)
        print(f"Exact matches found: {len(exact_matches)}")
        if exact_matches:
            print("Sample exact matches:")
            for nodeid in sorted(list(exact_matches))[:3]:
                print(f"  Match: {nodeid}")
    
    # Find missing combinations
    missing_nodeids = list(set(expected_nodeids) - set(executed_nodeids))
    
    print(f"\n=== RESULTS ===")
    print(f"Expected tests: {len(expected_nodeids)}")
    print(f"Executed tests: {len(executed_nodeids)}")
    print(f"Missing tests: {len(missing_nodeids)}")
    

    if expected_nodeids:
        print(f"\n=== EXPECTED TEST COMBINATIONS ===")
        for nodeid in sorted(list(expected_nodeids))[:10]:  # Show first 10 as examples
            print(f'  python -m pytest -svv "{nodeid}"')
        if len(expected_nodeids) > 10:
            print(f"  ... and {len(expected_nodeids) - 10} more")


    if missing_nodeids:        
        print(f"\n=== MISSING TEST COMBINATIONS ===")
        
        if args.output_missing:
            with open(args.output_missing, 'w') as f:
                for nodeid in sorted(missing_nodeids):
                    f.write(f"{nodeid}\n")
            print(f"\nMissing nodeids saved to: {args.output_missing}")
        
        print(f"\n=== TO RE-RUN MISSING TESTS ===")
        print("You can re-run missing tests using:")
        for nodeid in sorted(list(missing_nodeids))[:10]:  # Show first 10 as examples
            print(f'  python -m pytest -svv "{nodeid}"')
        if len(missing_nodeids) > 10:
            print(f"  ... and {len(missing_nodeids) - 10} more")
    else:
        print("\n✅ No missing test combinations found! All expected tests were executed.")
    
    # Show some executed tests for reference
    if executed_nodeids:
        print(f"\n=== SAMPLE EXECUTED TESTS ===")
        for nodeid in sorted(list(executed_nodeids))[:10]:
            print(f"  {nodeid}")
        if len(executed_nodeids) > 5:
            print(f"  ... and {len(executed_nodeids) - 10} more")


if __name__ == "__main__":
    main()

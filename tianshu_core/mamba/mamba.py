import mamba
import sys
import argparse
import random
import os
import mamba.lexer  # Import lexer to override keywords
import mamba.exceptions  # Import exceptions for error handling
import glob  # Import glob for finding template files
from pathlib import Path

# Define the path to the keyword file relative to this script's location
# Use os.path.abspath and __file__ to get the directory of the current script
PROJECT_ROOT = Path(__file__).parent.parent.parent
template_dir = PROJECT_ROOT / "datasets" / "tianshu_v1" / "template"
keyword_file_path = template_dir / "keyword-list.txt"

def main():
    # Initialize keywords list
    keywords = []

    parser = argparse.ArgumentParser(description="Mamba Interpreter")
    parser.add_argument(
        "filename",
        nargs="?",
        default=None,
        help="The script file to execute (optional if --dump-keywords is used).",
    )
    parser.add_argument(
        "--random-seed", type=int, help="Integer seed for the random number generator."
    )
    parser.add_argument(
        "--show-ast", action="store_true", help="Show the Abstract Syntax Tree after execution."
    )
    parser.add_argument(
        "--enable-warnings",
        action="store_false",
        dest="disable_warnings",
        help="Enable parser warnings.",
    )
    parser.add_argument(
        "--dump-keywords", action="store_true", help="Print the current keyword mapping and exit."
    )
    parser.add_argument(
        "--write-documentation",
        action="store_true",
        help="Generate documentation with current keywords based on seed and exit.",
    )
    parser.add_argument(
        "--max-execution-time",
        type=int,
        help="Maximum execution time in seconds before timeout (default: no limit)."
    )

    args = parser.parse_args()

    random_seed_was_set = args.random_seed is not None
    current_random_seed = args.random_seed if random_seed_was_set else None
    # Load and shuffle keywords only if the random seed was provided
    if random_seed_was_set:
        keywords = mamba.apply_random_keywords(current_random_seed)
        # --- End of override logic ---

        # --- Choose Language Name ---
        # Use the already seeded random generator to pick a name
        if keywords:  # Check if the list is not empty
            lang_name = random.choice(keywords).capitalize()  # Capitalize the chosen word
        else:
            lang_name = "Mamba"  # Default if keyword list is empty
        # --- End Language Name Choice ---

        # --- Documentation Generation Logic ---
        if args.write_documentation:
            try:
                # Define directory containing templates (one level up from this script)
                template_pattern = os.path.join(template_dir, "*-template*.md")
                template_files = glob.glob(template_pattern)

                if not template_files:
                    print(
                        f"Error: No template files found matching '{template_pattern}'",
                        file=sys.stderr,
                    )
                    sys.exit(1)

                # Get current keyword mapping {keyword: TOKEN_TYPE}
                current_reserved = mamba.lexer.reserved
                # Create reverse mapping {TOKEN_TYPE: keyword}
                token_to_keyword_map = {v: k for k, v in current_reserved.items()}

                # Calculate output directory based on seed
                seed_str = str(args.random_seed)
                first_three_digits = seed_str[:3]
                generated_path = PROJECT_ROOT / "datasets" / "tianshu_v1" / "generated"
                output_dir = generated_path / f"{first_three_digits}" / f"{seed_str}"

                # Create output directory if it doesn't exist
                os.makedirs(output_dir, exist_ok=True)

                generated_files_paths = []

                # Process each template file
                for template_path in template_files:
                    with open(template_path, "r") as f:
                        template_content = f.read()

                    processed_content = template_content

                    # Replace ${LANG_NAME} with the chosen name
                    processed_content = processed_content.replace("${LANG_NAME}", lang_name)

                    # Replace ${TOKEN_TYPE} placeholders
                    for token_type, keyword in token_to_keyword_map.items():
                        placeholder = f"${{{token_type}}}"
                        processed_content = processed_content.replace(placeholder, keyword)

                    # Determine output filename (remove -template)
                    template_basename = os.path.basename(template_path)
                    output_filename = template_basename.replace("-template", "")
                    output_file_path = output_dir / output_filename

                    # Write the processed file
                    with open(output_file_path, "w") as f:
                        f.write(processed_content)
                    generated_files_paths.append(output_file_path)

                print(f"Documentation generated successfully in: {output_dir}")
                # Optionally list generated files:
                # print("Generated files:")
                # for path in generated_files_paths:
                #     print(f"- {path}")
                sys.exit(0)

            except Exception as e:
                print(f"Error generating documentation: {e}", file=sys.stderr)
                sys.exit(1)
        # --- End Documentation Generation ---

    # If --dump-keywords is specified, print the mapping and exit
    if args.dump_keywords:
        # Now 'reserved' will reflect the overrides if they happened
        from mamba.lexer import reserved
        import pprint

        print("Current Keyword Mapping:")
        pprint.pprint(reserved)
        sys.exit(0)

    # Ensure filename is provided if not dumping keywords or writing documentation
    if not args.filename and not args.dump_keywords and not args.write_documentation:
        parser.error(
            "the following arguments are required: filename (unless --dump-keywords or --write-documentation is used)"
        )

    # Exit if only documentation or keyword dump was requested and filename wasn't needed
    if not args.filename and (args.dump_keywords or args.write_documentation):
        # The specific actions already called sys.exit(0) on success
        # If we reach here, it implies an error occurred in those blocks,
        # which should have already exited with sys.exit(1).
        # This path shouldn't normally be reached if those flags were set.
        # However, if filename is None AND one of the flags is set, we don't proceed to execute.
        sys.exit(0)  # Or handle potential prior error states if necessary

    # Proceed with execution only if a filename was provided
    try:
        # Note: mamba.execute will also seed the random generator if random_seed_was_set is True.
        # This ensures that subsequent 'rand' calls within the Mamba script use the same seed.
        with open(args.filename) as f:
            source = f.read()
        mamba.execute(
            source,
            show_ast=args.show_ast,
            disable_warnings=args.disable_warnings,
            random_seed=args.random_seed,
            random_seed_was_set=random_seed_was_set,
            max_execution_time_seconds=args.max_execution_time,
            # No longer pass keywords here
        )
    except FileNotFoundError:
        print(f"Error: File not found: {args.filename}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Catch potential exceptions during execution if warnings are disabled in execute
        print(f"An error occurred during execution: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

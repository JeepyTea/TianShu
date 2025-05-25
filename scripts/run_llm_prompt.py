#!/usr/bin/env python3

import os
import sys
import sys
from llm_client import SambaNovaClient

# --- Configuration ---
PROMPT_FILE_PATHS = [
    "generated_doc/1/1/Language.md",
    "generated_doc/1/1/Problem-001.md", # Added second file path
]
# Configuration for API Key and Model are now handled within the client:
# Priority: Client config dict -> Environment Variable -> Default constant in client file
# Relevant Env Vars: SAMBANOVA_API_KEY, SAMBANOVA_MODEL, SAMBANOVA_BASE_URL
# Separator to use when joining content from multiple files
PROMPT_SEPARATOR = "\n\n---\n\n" # Example separator

# Optional: Add other parameters for the API call here
# e.g., temperature=0.1, top_p=0.1, max_tokens=1024
LLM_PARAMS = {
    "temperature": 0.1,
    "top_p": 0.1,
    # "max_tokens": 1024, # Uncomment and adjust if needed
}
# --- End Configuration ---

def read_prompt_file(file_path: str) -> str:
    """Reads the content of the specified file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Prompt file not found at '{file_path}'", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading prompt file '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """Main execution function."""
    # --- Input Validation ---
    # API Key and Model validation are now handled inside the SambaNovaClient constructor
    # --- End Input Validation ---

    print(f"Reading prompt content from files:")
    all_prompt_content = []
    for file_path in PROMPT_FILE_PATHS:
        print(f"  - Reading {file_path}...")
        content = read_prompt_file(file_path)
        all_prompt_content.append(content)
        print(f"    Read {len(content)} characters.")

    # Concatenate the content from all files
    prompt_content = PROMPT_SEPARATOR.join(all_prompt_content)
    print(f"Combined prompt length: {len(prompt_content)} characters.")
    print("Prompt content prepared successfully.")


    # Configure the SambaNova client
    # API Key and Model will be sourced by the client itself
    # (config -> env var -> constant)
    # We pass an empty config here, relying on env vars or defaults.
    # If you wanted to override the model/key/url specifically for this run,
    # you could add them here, e.g., client_config = {"model": "some_other_model"}
    client_config = {
        # "model": "override_model_here", # Example override
        # "api_key": "override_key_here", # Example override
    }

    # The client will determine the actual model used based on its internal logic
    print(f"Initializing SambaNovaClient...")
    try:
        client = SambaNovaClient(config=client_config)
        # Optionally print the model the client resolved to use
        print(f"Client initialized. Using model: {client.model}")
    except ValueError as e:
        print(f"Error initializing LLM client: {e}", file=sys.stderr)
        sys.exit(1)
    print("Client initialized.")

    print("Sending prompt to SambaNova API...")
    try:
        response = client.send_prompt(prompt=prompt_content, **LLM_PARAMS)
        print("\n--- LLM Response ---")
        print(response)
        print("--- End Response ---")
    except Exception as e:
        print(f"\nError during LLM API call: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

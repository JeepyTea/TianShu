import mamba
import mamba.lexer  # To potentially set keywords if needed
import os

# --- Keyword setup (if needed for the embedded run) ---
# This part is crucial if you rely on non-default keywords.
# You'd need to replicate the logic from mamba.py's main()
# to load, shuffle (if seeded), and apply keywords using
# mamba.lexer.override_reserved_words() *before* calling mamba.execute.
# For simplicity, this example assumes default keywords.
# --- End Keyword Setup ---

output_log: list[tuple[str, str]] = []


def my_output_collector(message: str, stream: str):
    """Appends the message and its stream type to the log list."""
    print(f"Captured [{stream}]: {message}")  # Optional: See capture in real-time
    output_log.append((stream, message))


mamba_code = """
print "Hello from Mamba!";
x = 10 / 0; // This will cause a runtime error
print "This won't be printed";
"""

print("--- Running Mamba Code ---")
try:
    # Call execute with the custom handler
    mamba.execute(
        source=mamba_code,
        output_handler=my_output_collector,
        disable_warnings=True,  # Keep True to prevent execute from re-raising captured errors
    )
except Exception as e:
    # This catches errors *outside* of mamba.execute itself,
    # like potential issues setting up keywords if you added that logic.
    print(f"Error during Mamba setup or execution call: {e}")

print("--- Mamba Execution Finished ---")
print("\nCollected Output Log:")
for stream, message in output_log:
    print(f"- Stream: {stream}, Message: {message}")

# output_log now contains:
# [('stdout', 'Hello from Mamba!'),
#  ('stderr', 'InterpreterRuntimeError: Unable to apply operation (int: 10) / (int: 0)')]

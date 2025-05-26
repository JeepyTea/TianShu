# TiānshūBench

A benchmark suite for evaluating Large Language Models (LLMs).

## Installation

Setup Python virtual environment:
```bash
python -m venv .venv
```
Activate the virtual environment:
```bash
source .venv/bin/activate
```
or
```fish
source .venv/bin/activate.fish
```


Install required libraries:
```bash
pip install -e .
```

Copy `.env.example` to `.env` and edit it to set up your API keys and Ollama endpoint.

## Quick Start

```bash
# Generate benchmark language descriptions and instructions
scripts/generate_test_docs.sh

# Run benchmark tests. Note that test selection is available here using standard Pytest
# mechanisms, like running tianshu_bench/benchmarks/test_llm_ability.py::test_generated_program_with_mamba_execution
# or selecting individual tests with the -k flag to filter the exact test identifier, like -k "DeepSeek-V3-0324 and -8-"
python -m pytest -sv --report-log=report-file-name.json tianshu_bench/benchmarks/test_llm_ability.py

# List all available benchmark tests.
python -m pytest -q tianshu_bench/benchmarks/test_llm_ability.py --collect-only

# Also useful with the -k flag to see certain tests before running
python -m pytest -q tianshu_bench/benchmarks/test_llm_ability.py --collect-only -k  "DeepSeek-V3-0324 and -8-"

# Generate report for test_llm_ability.py::test_generated_program_with_mamba_execution
python scripts/analyze_report.py report-file-name.json
```

## Project Structure

- `tianshu_bench/` - Main benchmark test suite
- `tianshu_core/` - Core evaluation framework
- `datasets/` - Benchmark datasets
- `results/` - Evaluation results and leaderboard
- `configs/` - Configuration files
- `scripts/` - Utility scripts

## Adding New Benchmarks

See `docs/adding_tests.md` for detailed instructions.

## License
MIT

# TiānshūBench

A benchmark suite for evaluating Large Language Models (LLMs).

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Run all benchmarks for a model
python scripts/run_tianshu.py --model gpt-3.5-turbo

# Run specific category
python scripts/run_tianshu.py --model claude-3 --category coding

# Generate report
python scripts/generate_report.py --model gpt-3.5-turbo
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

[Your License Here]

"""Run the spec-faithfulness benchmark: Popper vs proof checker vs LLM judge.

    python examples/run_benchmark.py            # Popper + proof-checker baseline (offline)
    python examples/run_benchmark.py --llm      # also run a live model (needs ANTHROPIC_API_KEY)

Writes results/benchmark.{json,csv} and reports/benchmark.md.
"""

from falsify.bench.run import main

if __name__ == "__main__":
    main()

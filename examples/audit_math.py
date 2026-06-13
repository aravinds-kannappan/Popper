#!/usr/bin/env python3
"""Audit the information-theory ladder with the numerical oracle.

Runs fully offline with the standard library:

    python examples/audit_math.py
    python examples/audit_math.py --markdown > reports/math_audit.md
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falsify import NumericalOracle, information_theory_library, run_audit  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", action="store_true", help="emit a Markdown report")
    ap.add_argument("--trials", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    oracle = NumericalOracle(n_trials=args.trials, seed=args.seed)
    report = run_audit(
        information_theory_library(), oracle,
        title="Numerical oracle — information-theory ladder",
    )
    print(report.render_markdown() if args.markdown else report.render_terminal())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

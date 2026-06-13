#!/usr/bin/env python3
"""Live spec-faithfulness audit of the real Verina benchmark over AXLE.

Needs `pip install axiom-axle` and `AXLE_API_KEY` (free key:
https://axle.axiommath.ai/app/console). The dataset is fetched on demand into a
git-ignored cache.

    export AXLE_API_KEY=...
    python examples/verina_live_audit.py --limit 8
    python examples/verina_live_audit.py --limit 8 --markdown > reports/verina_live_audit.md
    python examples/verina_live_audit.py --tasks verina_advanced_1,verina_advanced_10
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from popper import run_live_audit  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=8, help="number of tasks (ignored if --tasks)")
    ap.add_argument("--tasks", type=str, default=None, help="comma-separated task ids")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-tests", type=int, default=2)
    ap.add_argument("--max-unexpected", type=int, default=2)
    ap.add_argument("--timeout", type=float, default=200.0)
    ap.add_argument("--environment", default="lean-4.28.0")
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()

    if not os.environ.get("AXLE_API_KEY"):
        print("ERROR: set AXLE_API_KEY (free key at https://axle.axiommath.ai/app/console)",
              file=sys.stderr)
        return 2

    ids = [t.strip() for t in args.tasks.split(",")] if args.tasks else None
    report = run_live_audit(
        task_ids=ids, limit=None if ids else args.limit,
        environment=args.environment, concurrency=args.concurrency,
        max_tests=args.max_tests, max_unexpected=args.max_unexpected,
        timeout_s=args.timeout, progress=not args.markdown,
    )
    print(report.render_markdown() if args.markdown else report.render_terminal())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

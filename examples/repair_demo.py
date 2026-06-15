#!/usr/bin/env python3
"""M2 demo: counterexample-guided spec repair on the offline fixtures.

Shows each unfaithful spec being driven to FAITHFUL by the repair loop.

    python examples/repair_demo.py
    python examples/repair_demo.py --markdown > reports/repair_demo.md
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falsify import (CodeSpecOracle, MockAxleClient, default_repairer,  # noqa: E402
                    repair_loop, verina_like_tasks)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()

    oracle = CodeSpecOracle(MockAxleClient())
    traces = [repair_loop(t, oracle, default_repairer()) for t in verina_like_tasks()]

    if args.markdown:
        print("# M2 - counterexample-guided spec repair\n")
        print("| task | verdict path | repaired? |")
        print("|---|---|---|")
        for tr in traces:
            path = " → ".join(f"`{r.verdict.value}`" for r in tr.rounds)
            print(f"| `{tr.task}` | {path} | {'✅' if tr.success else '-'} |")
    else:
        print("\n=== M2: counterexample-guided spec repair ===\n")
        for tr in traces:
            print(tr.render())
        fixed = sum(1 for t in traces if t.success and len(t.rounds) > 1)
        print(f"\nrepaired {fixed} unfaithful specs to FAITHFUL "
              f"({sum(1 for t in traces if t.success)}/{len(traces)} faithful overall)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

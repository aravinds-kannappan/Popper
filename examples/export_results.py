#!/usr/bin/env python3
"""Export all audit results to results/ as JSON + CSV.

Offline audits always run. The live Verina audit also runs when AXLE_API_KEY is
set (and --live-limit > 0).

    python examples/export_results.py
    AXLE_API_KEY=... python examples/export_results.py --live-limit 10
"""

import argparse
import csv
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
RESULTS = os.path.join(REPO, "results")

from falsify import (CodeSpecOracle, MockAxleClient, NumericalOracle,  # noqa: E402
                     default_repairer, information_theory_library, repair_loop,
                     run_audit, run_live_audit, verina_like_tasks)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live-limit", type=int, default=10,
                    help="how many real Verina tasks to audit live (0 = skip)")
    args = ap.parse_args()
    os.makedirs(RESULTS, exist_ok=True)
    written = []

    # 1. numerical oracle (math)
    rep = run_audit(information_theory_library(), NumericalOracle(),
                    "Numerical oracle - information-theory ladder")
    written += [rep.write_json(f"{RESULTS}/math_audit.json"),
                rep.write_csv(f"{RESULTS}/math_audit.csv")]

    # 2. offline code-spec oracle
    rep = run_audit(verina_like_tasks(), CodeSpecOracle(MockAxleClient()),
                    "Code-spec oracle - offline fixtures")
    written += [rep.write_json(f"{RESULTS}/codespec_offline.json"),
                rep.write_csv(f"{RESULTS}/codespec_offline.csv")]

    # 3. M2 repair traces
    oracle = CodeSpecOracle(MockAxleClient())
    traces = [repair_loop(t, oracle, default_repairer()) for t in verina_like_tasks()]
    records = [{"task": tr.task,
                "verdict_path": " -> ".join(r.verdict.value for r in tr.rounds),
                "rounds": len(tr.rounds), "final": tr.final.value,
                "repaired": tr.success and len(tr.rounds) > 1} for tr in traces]
    json.dump({"results": records}, open(f"{RESULTS}/repair.json", "w"), indent=2)
    with open(f"{RESULTS}/repair.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["task", "verdict_path", "rounds", "final", "repaired"])
        w.writeheader(); w.writerows(records)
    written += [f"{RESULTS}/repair.json", f"{RESULTS}/repair.csv"]

    # 4. live Verina audit over AXLE (optional)
    if args.live_limit > 0 and os.environ.get("AXLE_API_KEY"):
        live = run_live_audit(limit=args.live_limit, progress=True)
        written += [live.write_json(f"{RESULTS}/verina_live.json"),
                    live.write_csv(f"{RESULTS}/verina_live.csv")]
    else:
        print("(skipping live Verina audit - set AXLE_API_KEY and --live-limit > 0)")

    print("\nwrote:")
    for p in written:
        print(" ", os.path.relpath(p, REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

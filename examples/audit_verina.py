#!/usr/bin/env python3
"""Audit Verina-style code specifications with the code-spec oracle.

Offline (default): evaluates an executable model of each task via MockAxleClient.

    python examples/audit_verina.py
    python examples/audit_verina.py --markdown > reports/verina_audit.md

Live: with `AXLE_API_KEY` set, `--live` routes every soundness/completeness check
through the real Axiom Lean Engine instead of the offline model.

    export AXLE_API_KEY=...        # free key: https://axle.axiommath.ai/app/console
    python examples/audit_verina.py --live
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from popper import CodeSpecOracle, MockAxleClient, run_audit, verina_like_tasks  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--live", action="store_true", help="use the real AXLE API (needs AXLE_API_KEY)")
    args = ap.parse_args()

    if args.live:
        from popper import AxleClient
        client = AxleClient()  # raises a helpful error if AXLE_API_KEY is unset
        backend = "live AXLE"
    else:
        client = MockAxleClient()
        backend = "offline model (MockAxleClient)"

    oracle = CodeSpecOracle(client)
    report = run_audit(
        verina_like_tasks(), oracle,
        title=f"Code-spec oracle — Verina-style tasks [{backend}]",
    )
    print(report.render_markdown() if args.markdown else report.render_terminal())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

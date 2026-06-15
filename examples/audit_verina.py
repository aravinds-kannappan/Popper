#!/usr/bin/env python3
"""Code-spec oracle on offline Verina-style fixtures (executable model, no network).

    python examples/audit_verina.py
    python examples/audit_verina.py --markdown > reports/verina_audit.md

For the LIVE audit of the real 189-task Verina benchmark over the Axiom Lean
Engine, see `examples/verina_live_audit.py`.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falsify import CodeSpecOracle, MockAxleClient, run_audit, verina_like_tasks  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()

    oracle = CodeSpecOracle(MockAxleClient())
    report = run_audit(
        verina_like_tasks(), oracle,
        title="Code-spec oracle - Verina-style fixtures [offline model]",
    )
    print(report.render_markdown() if args.markdown else report.render_terminal())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

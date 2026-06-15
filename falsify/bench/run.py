"""Run the spec-faithfulness benchmark and write the results.

Outputs (under the repo root):
  * ``results/benchmark.json``  -- per-judge scores and per-item verdicts
  * ``results/benchmark.csv``   -- one row per item, one column per judge
  * ``reports/benchmark.md``    -- a readable summary table

The Popper and proof-checker columns need no API key and are fully reproducible
offline. The LLM column is filled in only when ANTHROPIC_API_KEY is set; without
it the column is reported as "not run" rather than guessed.
"""

from __future__ import annotations

import csv
import json
import os

from ..core.oracle import Verdict
from .corpus import benchmark_corpus
from .judges import llm_available, llm_judge, popper_judge, proof_checker_judge
from .metrics import score_judge

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_RESULTS = os.path.join(_ROOT, "results")
_REPORTS = os.path.join(_ROOT, "reports")
_WEB_DATA = os.path.join(_ROOT, "web", "app", "data")


def run_benchmark(*, with_llm: bool = False, n_trials: int = 2000, seed: int = 0) -> dict:
    items = benchmark_corpus()

    judges = [("popper", lambda it: popper_judge(it, n_trials=n_trials, seed=seed)),
              ("proof_checker", proof_checker_judge)]
    if with_llm:
        judges.append(("llm_judge", llm_judge))

    results: dict[str, list] = {name: [] for name, _ in judges}
    for item in items:
        for name, fn in judges:
            results[name].append((item, fn(item)))

    scores = {name: score_judge(name, pairs).as_dict() for name, pairs in results.items()}

    # per-item rows
    rows = []
    by_item = {name: {it.name: res for it, res in pairs} for name, pairs in results.items()}
    for item in items:
        row = {
            "name": item.name,
            "surface": item.surface,
            "family": item.family,
            "gold": item.gold.value,
        }
        for name, _ in judges:
            res = by_item[name][item.name]
            row[f"{name}_verdict"] = res.verdict.value
            row[f"{name}_counterexample"] = res.counterexample or ""
        rows.append(row)

    out = {
        "title": "Spec-faithfulness benchmark: Popper vs proof checker vs LLM judge",
        "n_items": len(items),
        "surfaces": _surface_counts(items),
        "judges": list(results.keys()),
        "llm_run": with_llm and llm_available(),
        "scores": scores,
        "rows": rows,
    }
    return out


def _surface_counts(items) -> dict:
    out: dict = {}
    for it in items:
        s = out.setdefault(it.surface, {"total": 0, "faithful": 0, "unfaithful": 0, "vacuity": 0})
        s["total"] += 1
        if it.gold is Verdict.INCONCLUSIVE:
            s["vacuity"] += 1
        elif it.gold_unfaithful:
            s["unfaithful"] += 1
        else:
            s["faithful"] += 1
    return out


def write_outputs(out: dict) -> None:
    os.makedirs(_RESULTS, exist_ok=True)
    os.makedirs(_REPORTS, exist_ok=True)
    with open(os.path.join(_RESULTS, "benchmark.json"), "w") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    if os.path.isdir(_WEB_DATA):
        with open(os.path.join(_WEB_DATA, "benchmark.json"), "w") as fh:
            json.dump(out, fh, indent=2, ensure_ascii=False)

    # CSV: one row per item
    rows = out["rows"]
    if rows:
        with open(os.path.join(_RESULTS, "benchmark.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    with open(os.path.join(_REPORTS, "benchmark.md"), "w") as fh:
        fh.write(_markdown(out))


def _markdown(out: dict) -> str:
    s = out["scores"]
    judges = out["judges"]
    pretty = {"popper": "Popper", "proof_checker": "Proof checker (AXLE/Lean)", "llm_judge": "LLM judge"}

    lines = []
    lines.append("# Spec-faithfulness benchmark\n")
    lines.append(
        f"_{out['n_items']} labelled claims across "
        + ", ".join(f"{k} ({v['total']})" for k, v in out["surfaces"].items())
        + ". The task: flag the unfaithful specs, leave the faithful ones alone._\n"
    )
    lines.append("## Headline\n")
    lines.append("| judge | unfaithful caught (recall) | false positives | counterexample yield | F1 |")
    lines.append("|---|---|---|---|---|")
    for j in judges:
        sc = s[j]
        lines.append(
            f"| {pretty.get(j, j)} | {sc['true_positives']}/{sc['n_unfaithful']} "
            f"({sc['recall_unfaithful']:.0%}) | {sc['false_positives']}/{sc['n_faithful']} "
            f"({sc['false_positive_rate']:.0%}) | {sc['counterexample_yield']:.0%} | {sc['f1']:.2f} |"
        )
    if not out["llm_run"]:
        lines.append(
            "\n_LLM judge not run in this pass (no ANTHROPIC_API_KEY). For a published "
            "reference point, the Verina paper reports the best general model reaching "
            "about 52% combined specification soundness and completeness, and it returns "
            "no counterexample. Re-run with `--llm` to fill the row from a live model._\n"
        )

    lines.append("## What the numbers mean\n")
    lines.append(
        "- **Recall** is the fraction of unfaithful specs the judge flagged. The proof "
        "checker cannot flag any, by construction, so it scores zero however good the prover is.\n"
        "- **False positives** are faithful specs wrongly flagged. Lower is better.\n"
        "- **Counterexample yield** is the fraction of true detections that came with a concrete "
        "witness you can act on. Only Popper produces these.\n"
    )

    lines.append("## Per-item verdicts\n")
    lines.append("| item | surface | gold | " + " | ".join(pretty.get(j, j) for j in judges) + " | counterexample |")
    lines.append("|---|---|---|" + "---|" * (len(judges) + 1))
    for r in out["rows"]:
        verdicts = " | ".join(f"`{r[f'{j}_verdict']}`" for j in judges)
        ce = r.get("popper_counterexample", "")
        ce = (ce[:70] + "...") if len(ce) > 73 else ce
        lines.append(f"| `{r['name']}` | {r['surface']} | `{r['gold']}` | {verdicts} | {ce} |")

    lines.append(
        "\n> Popper falsifies; it does not certify. A FAITHFUL verdict means no counterexample "
        "was found within the search budget.\n"
    )
    return "\n".join(lines) + "\n"


def main(argv=None) -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Run the spec-faithfulness benchmark.")
    ap.add_argument("--llm", action="store_true", help="also run the live LLM judge (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--trials", type=int, default=2000, help="Monte-Carlo draws per math statement")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    out = run_benchmark(with_llm=args.llm, n_trials=args.trials, seed=args.seed)
    write_outputs(out)

    print(f"Benchmark: {out['n_items']} items across {len(out['surfaces'])} surfaces.")
    for j in out["judges"]:
        sc = out["scores"][j]
        print(
            f"  {j:14s} recall {sc['recall_unfaithful']:.0%}  "
            f"FP {sc['false_positive_rate']:.0%}  "
            f"counterexamples {sc['counterexample_yield']:.0%}  F1 {sc['f1']:.2f}"
        )
    print("Wrote results/benchmark.json, results/benchmark.csv, reports/benchmark.md")


if __name__ == "__main__":
    main()

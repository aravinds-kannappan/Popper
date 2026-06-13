"""Run an oracle over a batch of claims and render a report.

Surface-agnostic: it works for math statements and code specs identically,
because both produce :class:`~falsify.core.oracle.OracleResult`.
"""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from dataclasses import dataclass, field

from .oracle import GLYPH, Oracle, OracleResult, Verdict


@dataclass
class AuditReport:
    title: str
    oracle_name: str
    results: list[OracleResult] = field(default_factory=list)

    @property
    def counts(self) -> Counter:
        return Counter(r.verdict for r in self.results)

    @property
    def faithful_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.counts[Verdict.FAITHFUL] / len(self.results)

    def summary_line(self) -> str:
        c = self.counts
        parts = [f"{GLYPH[v]} {v.value} {c[v]}" for v in Verdict if c[v]]
        return f"{len(self.results)} claims | " + "  ".join(parts)

    def render_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            f"_oracle: `{self.oracle_name}` — {self.summary_line()}_",
            "",
            "| | verdict | claim | reason / counterexample |",
            "|---|---|---|---|",
        ]
        for r in self.results:
            ce = f" **⟵ {r.counterexample}**" if r.counterexample else ""
            lines.append(
                f"| {GLYPH[r.verdict]} | `{r.verdict.value}` | `{r.name}` | {r.reason}{ce} |"
            )
        lines += [
            "",
            "> Popper *falsifies*; it does not certify. A FAITHFUL verdict means "
            "no counterexample was found within the search budget — the dominant "
            "real-world failures (dropped hypotheses, vacuity, wrong direction, "
            "too-strong/too-weak specs) are exactly what it catches.",
        ]
        return "\n".join(lines)

    def render_terminal(self) -> str:
        head = f"\n=== {self.title} ===\n{self.summary_line()}\n"
        body = "\n".join(r.one_line() for r in self.results)
        return head + body + "\n"

    # -- machine-readable export ------------------------------------------- #
    def to_records(self) -> list[dict]:
        return [
            {"name": r.name, "verdict": r.verdict.value, "reason": r.reason,
             "counterexample": r.counterexample or "", "trials": r.trials,
             **{k: v for k, v in r.details.items()}}
            for r in self.results
        ]

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "oracle": self.oracle_name,
            "summary": {v.value: c for v, c in self.counts.items()},
            "faithful_rate": round(self.faithful_rate, 4),
            "results": self.to_records(),
        }

    def write_json(self, path: str) -> str:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path

    def write_csv(self, path: str) -> str:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        cols = ["name", "verdict", "reason", "counterexample", "trials"]
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for rec in self.to_records():
                w.writerow(rec)
        return path


def run_audit(items, oracle: Oracle, title: str) -> AuditReport:
    report = AuditReport(title=title, oracle_name=oracle.name)
    for item in items:
        report.results.append(oracle.audit(item))
    return report

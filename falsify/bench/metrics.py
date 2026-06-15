"""Scoring for the benchmark.

The task is binary: flag the unfaithful specs, leave the faithful ones alone.
We treat "unfaithful" as the positive class. A judge "flags" an item when its
verdict is one of the falsified kinds (FALSIFIED / UNSOUND / INCOMPLETE /
VACUOUS). Vacuity traps are scored separately because the honest answer there is
INCONCLUSIVE, not a hard flag.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.oracle import OracleResult, Verdict
from .corpus import Item


@dataclass
class JudgeScore:
    judge: str
    n: int = 0
    n_unfaithful: int = 0
    n_faithful: int = 0
    n_vacuity: int = 0
    tp: int = 0                 # flagged and gold-unfaithful
    fp: int = 0                 # flagged and gold-faithful
    fn: int = 0                 # not flagged but gold-unfaithful
    vacuity_handled: int = 0    # vacuity trap answered INCONCLUSIVE or VACUOUS
    counterexamples: int = 0    # true detections that came with a concrete witness

    @property
    def recall(self) -> float:
        return self.tp / self.n_unfaithful if self.n_unfaithful else 0.0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def false_positive_rate(self) -> float:
        return self.fp / self.n_faithful if self.n_faithful else 0.0

    @property
    def counterexample_yield(self) -> float:
        return self.counterexamples / self.tp if self.tp else 0.0

    def as_dict(self) -> dict:
        return {
            "judge": self.judge,
            "n": self.n,
            "n_unfaithful": self.n_unfaithful,
            "n_faithful": self.n_faithful,
            "n_vacuity": self.n_vacuity,
            "true_positives": self.tp,
            "false_positives": self.fp,
            "false_negatives": self.fn,
            "recall_unfaithful": round(self.recall, 4),
            "precision": round(self.precision, 4),
            "f1": round(self.f1, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "vacuity_handled": self.vacuity_handled,
            "counterexample_yield": round(self.counterexample_yield, 4),
        }


def score_judge(judge_name: str, pairs: list[tuple[Item, OracleResult]]) -> JudgeScore:
    s = JudgeScore(judge=judge_name, n=len(pairs))
    for item, result in pairs:
        flagged = result.verdict.is_falsified
        if item.gold is Verdict.INCONCLUSIVE:
            s.n_vacuity += 1
            if result.verdict in (Verdict.INCONCLUSIVE, Verdict.VACUOUS):
                s.vacuity_handled += 1
            continue
        if item.gold_unfaithful:
            s.n_unfaithful += 1
            if flagged:
                s.tp += 1
                if result.counterexample:
                    s.counterexamples += 1
            else:
                s.fn += 1
        else:  # gold faithful
            s.n_faithful += 1
            if flagged:
                s.fp += 1
    return s

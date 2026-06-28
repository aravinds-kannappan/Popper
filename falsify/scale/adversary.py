"""Train the adversary instead of hand-writing it.

The reward-hack probe in :mod:`.rewardhack` tries a fixed family of candidate
implementations in a fixed order. That is the spec-side mirror of the lesson in
the reward-hacking literature: a real optimizer does not respect your
enumeration, it *learns* which shortcuts pay off and reaches for those first. So
this module makes the adversary adaptive on three fronts.

  * :class:`AdaptiveHackPolicy` - a UCB1 bandit over hacker *families* (constant
    answers, identity, negation, off-by-one, declared mutants). Across a stream
    of tasks it learns which families actually catch bugs and orders the search
    to try them first, so the average number of candidate evaluations before a
    catch falls as it sees more specs. This is the co-trained adversary in
    miniature: each catch rewards the family that produced it.
  * :class:`WitnessMemory` - transfer across tasks. A catch is recorded against
    the *shape* of the spec (its parsed signature), so a new task with the same
    shape replays the family that worked before and is caught on the first try.
  * :func:`conjunctive_trigger_search` - learn the trigger *predicate*, not just
    a point. Real sleepers fire on a conjunction of rare conditions; by reading
    the converged Cross-Entropy proposal it identifies which input coordinates
    the search had to drive into a corner, recovering the structure of the
    backdoor rather than a single witness.

Pure standard library.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from typing import Optional

from ..speccheck.task import Task
from .importance import AdaptiveFalsifier, ScoredClaim
from .rewardhack import RewardHackReport, _rates, hacker_candidates


# --------------------------------------------------------------------------- #
# hacker families
# --------------------------------------------------------------------------- #
def family_of(name: str) -> str:
    if name.startswith("const::"):
        return "const"
    return {
        "identity_arg0": "identity",
        "reverse_arg0": "reverse",
        "negate_arg0": "negate",
        "off_by_one": "off_by_one",
    }.get(name, "declared")


FAMILIES = ("const", "identity", "reverse", "negate", "off_by_one", "declared")


# --------------------------------------------------------------------------- #
# UCB1 bandit over families
# --------------------------------------------------------------------------- #
@dataclass
class AdaptiveHackPolicy:
    c: float = 1.4
    counts: dict = field(default_factory=lambda: {f: 0 for f in FAMILIES})
    value: dict = field(default_factory=lambda: {f: 0.0 for f in FAMILIES})
    t: int = 0

    def _ucb(self, f: str) -> float:
        if self.counts[f] == 0:
            return math.inf
        return self.value[f] + self.c * math.sqrt(math.log(self.t + 1) / self.counts[f])

    def order(self, families: list[str]) -> list[str]:
        return sorted(families, key=self._ucb, reverse=True)

    def update(self, family: str, reward: float) -> None:
        self.t += 1
        self.counts[family] += 1
        n = self.counts[family]
        self.value[family] += (reward - self.value[family]) / n


# --------------------------------------------------------------------------- #
# transfer memory keyed by spec shape
# --------------------------------------------------------------------------- #
@dataclass
class WitnessMemory:
    store: dict = field(default_factory=dict)   # shape_key -> [family, ...] (most recent first)

    def shape_key(self, task: Task) -> str:
        try:
            from ..speccheck.typegen import parse_signature
            args, ret = parse_signature(task.signature)
            return f"{[type(a).__name__ for a in args]}->{type(ret).__name__}"
        except Exception:
            return task.signature.split(":", 1)[-1].strip()

    def suggest(self, task: Task) -> list[str]:
        return list(self.store.get(self.shape_key(task), []))

    def record(self, task: Task, family: str) -> None:
        key = self.shape_key(task)
        fams = [f for f in self.store.get(key, []) if f != family]
        self.store[key] = [family] + fams

    def save(self, path: str) -> str:
        import os
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.store, f, indent=2)
        return path

    def load(self, path: str) -> "WitnessMemory":
        with open(path) as f:
            self.store = json.load(f)
        return self


# --------------------------------------------------------------------------- #
# first-hit search with a given family ordering (counts evaluations)
# --------------------------------------------------------------------------- #
def _first_hack(task: Task, client, family_order: list[str], *, seed: int = 0):
    inputs_rng = random.Random(seed)
    inputs = (list(task.test_inputs)
              + [task.gen_input(inputs_rng) for _ in range(task.fuzz_n)])
    cands = hacker_candidates(task)
    by_family: dict = {}
    for name, fn in cands.items():
        by_family.setdefault(family_of(name), []).append((name, fn))

    ordered = family_order + [f for f in by_family if f not in family_order]
    evals = 0
    tried_families: list[str] = []
    for fam in ordered:
        if fam not in by_family:
            continue
        tried_families.append(fam)
        for name, fn in by_family[fam]:
            evals += 1
            acc, agr, div = _rates(task, fn, client, inputs)
            if acc >= 1.0 - 1e-9 and agr < 1.0 - 1e-9:
                ignores = name.startswith("const::") or name == task.arbitrary
                ce = (f"impl '{name}' satisfies the spec on every input yet diverges "
                      f"from the reference at {div}")
                report = RewardHackReport(
                    task=task.name, hacked=True, hacker=name, acceptance=acc, agreement=agr,
                    counterexample=ce, candidates_tried=evals, ignores_input=ignores)
                return report, evals, fam, tried_families
    return (RewardHackReport(task=task.name, hacked=False, candidates_tried=evals),
            evals, None, tried_families)


def probe_reward_hacks_learned(task: Task, client, *, policy: AdaptiveHackPolicy,
                               memory: Optional[WitnessMemory] = None, seed: int = 0):
    """Find a reward hack using the learned family order and transfer memory.

    Updates ``policy`` (reward the catching family, penalize the rest tried) and
    ``memory`` (record the catch against the spec shape). Returns the report; the
    number of candidate evaluations is on ``report.candidates_tried``.
    """
    prelude = memory.suggest(task) if memory else []
    learned = policy.order([f for f in FAMILIES if f not in prelude])
    order = prelude + learned

    report, evals, hit_family, tried = _first_hack(task, client, order, seed=seed)
    for fam in tried:
        policy.update(fam, 1.0 if fam == hit_family else 0.0)
    if hit_family and memory is not None:
        memory.record(task, hit_family)
    return report


def naive_evaluations(task: Task, client, *, seed: int = 0) -> int:
    """Candidate evaluations for the fixed-order baseline (first-hit)."""
    _, evals, _, _ = _first_hack(task, client, list(FAMILIES), seed=seed)
    return evals


# --------------------------------------------------------------------------- #
# learn the trigger predicate (conjunctive sleeper structure)
# --------------------------------------------------------------------------- #
@dataclass
class TriggerStructure:
    claim: str
    found: bool
    trigger_coords: list           # latent coords the search drove into a corner
    proposal_mean: Optional[list] = None
    note: str = ""

    def one_line(self) -> str:
        if not self.found:
            return f"{self.claim}: no trigger found"
        return (f"{self.claim}: trigger is a conjunction over coords {self.trigger_coords} "
                f"(proposal mean {[round(m, 2) for m in (self.proposal_mean or [])]})")


def conjunctive_trigger_search(claim: ScoredClaim, *, budget: int = 6000,
                               low: float = 0.35, seed: int = 0) -> TriggerStructure:
    """Recover which coordinates the sleeper's trigger constrains, not just a point.

    Runs adaptive search and reads the converged Cross-Entropy proposal: a
    coordinate whose proposal mean was driven well below 0.5 is one the trigger
    forces into a corner. The set of such coordinates is the learned conjunction.
    """
    res = AdaptiveFalsifier(budget=budget, seed=seed).search(claim)
    mean = res.proposal_mean or [0.5] * claim.dim
    coords = [i for i, m in enumerate(mean) if m < low]
    note = ("conjunction recovered" if res.found and coords
            else "single point" if res.found else "no counterexample")
    return TriggerStructure(claim=claim.name, found=res.found, trigger_coords=coords,
                            proposal_mean=mean, note=note)

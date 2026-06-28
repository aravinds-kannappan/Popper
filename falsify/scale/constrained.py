"""Safe-RLHF faithfulness scoring: decouple reward from cost.

*Safe RLHF* (Dai et al. 2023) makes one move that turns out to be exactly what a
faithfulness oracle needs. Instead of folding everything into a single scalar
reward, it splits human preference into a **reward** (helpfulness: how good the
answer is) and a separate **cost** (harmlessness: how unsafe it is), trains a
model for each, and optimizes ``maximize reward subject to cost <= d`` with a
Lagrangian that adapts the trade-off during training. Collapsing the two into one
number is what lets a model trade a little harm for a lot of helpfulness; keeping
them separate, with a hard constraint on cost, is what prevents it.

Popper's two failure verdicts are precisely those two axes:

  * UNSOUND   = the spec rejects the *correct* answer  -> a **reward** failure
    (it is not helpful; it refuses good outputs).
  * INCOMPLETE / VACUOUS = the spec accepts a *wrong* answer -> a **cost**
    failure (it is unsafe; it admits bad outputs).

So we score a spec the Safe-RLHF way. ``reward`` is the fraction of correct
outputs the spec accepts (helpfulness, want 1.0). ``cost`` is the fraction of
wrong outputs it accepts (harm, want 0.0). The faithfulness objective is the
Lagrangian ``reward - lambda * cost``, and a spec is *safe* only if it satisfies
the hard constraint ``cost <= threshold``. The win over a one-bit verdict is that
this is a smooth, signed reward: it gives the repair loop (and, on the live path,
an RL fine-tune) a gradient instead of a yes/no, which is what the README means by
"the counterexample doubles as a clean RL reward".
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from ..speccheck.task import Task
from ..core.oracle import OracleResult, Verdict

SAFE_THRESHOLD = 0.0   # zero tolerance for accepting a wrong answer
DEFAULT_LAMBDA = 4.0   # cost is weighted heavily, as in Safe-RLHF's tuned regime


@dataclass
class FaithfulnessScore:
    """The Safe-RLHF view of one spec's faithfulness."""

    task: str
    reward: float            # acceptance rate of CORRECT outputs (helpfulness)
    cost: float              # acceptance rate of WRONG outputs (harm)
    lam: float = DEFAULT_LAMBDA
    threshold: float = SAFE_THRESHOLD
    n_correct: int = 0
    n_wrong: int = 0

    @property
    def objective(self) -> float:
        """The Lagrangian faithfulness reward, in (-inf, 1]."""
        return self.reward - self.lam * self.cost

    @property
    def constraint_satisfied(self) -> bool:
        return self.cost <= self.threshold + 1e-9

    @property
    def verdict(self) -> Verdict:
        if self.reward < 1.0 - 1e-9:
            return Verdict.UNSOUND       # rejects a correct answer
        if self.cost > self.threshold + 1e-9:
            return Verdict.INCOMPLETE     # accepts a wrong answer
        return Verdict.FAITHFUL

    def as_dict(self) -> dict:
        return {
            "task": self.task,
            "reward": round(self.reward, 4),
            "cost": round(self.cost, 4),
            "lambda": self.lam,
            "objective": round(self.objective, 4),
            "constraint_satisfied": self.constraint_satisfied,
            "verdict": self.verdict.value,
            "n_correct": self.n_correct,
            "n_wrong": self.n_wrong,
        }

    def one_line(self) -> str:
        flag = "ok " if self.constraint_satisfied else "VIOLATED"
        return (f"{self.task:<24} reward={self.reward:.2f}  cost={self.cost:.2f}  "
                f"J={self.objective:+.2f}  [{flag}] -> {self.verdict.value}")


def score_task(task: Task, client, *, lam: float = DEFAULT_LAMBDA,
               threshold: float = SAFE_THRESHOLD, seed: int = 0,
               wrong_impls: Optional[list[str]] = None) -> FaithfulnessScore:
    """Compute the reward/cost faithfulness score for ``task``'s spec.

    reward = fraction of inputs where the *reference* output is accepted.
    cost   = over every known-wrong implementation, the fraction of inputs where
             the spec accepts an output that disagrees with the reference.
    """
    spec = task.spec_py[task.spec]
    ref = task.impls_py[task.reference]
    rng = random.Random(seed)
    inputs = list(task.test_inputs) + [task.gen_input(rng) for _ in range(task.fuzz_n)]

    # reward: how often the correct answer is accepted (helpfulness)
    correct_total = correct_ok = 0
    for args in inputs:
        out = ref(*args)
        correct_total += 1
        correct_ok += int(bool(spec(args, out)))
    reward = correct_ok / correct_total if correct_total else 0.0

    # cost: how often a wrong answer is accepted (harm)
    wrong = wrong_impls or list(task.wrong_impls)
    if task.arbitrary and task.arbitrary not in wrong:
        wrong = wrong + [task.arbitrary]
    cost_total = cost_bad = 0
    for impl in wrong:
        fn = task.impls_py.get(impl)
        if fn is None:
            continue
        for args in inputs:
            out = fn(*args)
            if out == ref(*args):
                continue                 # agrees with reference here; not a harm case
            cost_total += 1
            cost_bad += int(bool(spec(args, out)))
    cost = cost_bad / cost_total if cost_total else 0.0

    return FaithfulnessScore(
        task=task.name, reward=reward, cost=cost, lam=lam, threshold=threshold,
        n_correct=correct_total, n_wrong=cost_total)


def as_oracle_result(score: FaithfulnessScore) -> OracleResult:
    v = score.verdict
    reason = {
        Verdict.FAITHFUL: f"reward {score.reward:.2f}, cost {score.cost:.2f}; constraint satisfied",
        Verdict.UNSOUND: f"reward {score.reward:.2f} < 1; the spec refuses some correct answers",
        Verdict.INCOMPLETE: f"cost {score.cost:.2f} > {score.threshold}; the spec admits wrong answers",
    }[v]
    return OracleResult(
        name=score.task, verdict=v, reason=reason,
        trials=score.n_correct + score.n_wrong,
        details={"check": "safe-rlhf", **score.as_dict()})

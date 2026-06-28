"""Aggregate the checks into a risk card and a gate decision.

*Model evaluation for extreme risks* (Shevlane et al. 2023) argues that an
evaluation is only useful if it feeds a *decision*: you separate a capability
axis ("can it do the dangerous thing") from a propensity / alignment axis ("will
it"), score both, and gate deployment on a threshold rather than on a vibe.
Popper sits in exactly that governance position. It is the screen in front of an
expensive prover, so its output should not be a lone verdict but a graded risk
card that decides whether the next, costly stage runs at all.

This module composes the other five into one card:

  * **capability** - does the spec pin down the right answer? Driven by the
    Safe-RLHF ``reward`` (does it accept the correct output): a spec that rejects
    correct answers is low-capability (UNSOUND).
  * **propensity** - will a wrong answer slip through? Driven by the Safe-RLHF
    ``cost`` and the reward-hack margin (does an adversarial impl collect reward):
    high propensity is the alignment-relevant risk (INCOMPLETE / VACUOUS).

The two combine into a risk in ``[0, 1]`` and a gate:

  * ``PROVE``  - low risk; send the statement to the expensive prover.
  * ``REPAIR`` - a recoverable fault (the debate found the missing premise, or
    the cost is fixable); run the counterexample-guided repair loop first.
  * ``REJECT`` - the spec constrains nothing (vacuous) or rejects correctness
    (unsound); do not spend proof compute on it at all.

That is the concrete shape of "protect the expensive compute": a thresholded
decision, with the witness attached, instead of a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..core.oracle import Verdict
from ..speccheck.task import Task
from .constrained import FaithfulnessScore, score_task
from .rewardhack import RewardHackReport, probe_reward_hacks


class GateDecision(str, Enum):
    PROVE = "PROVE"     # faithful enough; spend prover compute
    REPAIR = "REPAIR"   # recoverable; run the repair loop first
    REJECT = "REJECT"   # do not prove this statement


@dataclass
class EvalCard:
    task: str
    capability: float          # in [0,1]; 1 = pins the correct answer
    propensity: float          # in [0,1]; 1 = freely admits wrong answers
    gate: GateDecision
    verdict: Verdict
    score: Optional[FaithfulnessScore] = None
    hack: Optional[RewardHackReport] = None
    reasons: list[str] = field(default_factory=list)

    @property
    def risk(self) -> float:
        """Overall faithfulness risk in [0,1]: low capability or high propensity is risk."""
        return round(max(self.propensity, 1.0 - self.capability), 4)

    def as_dict(self) -> dict:
        return {
            "task": self.task,
            "capability": round(self.capability, 4),
            "propensity": round(self.propensity, 4),
            "risk": self.risk,
            "gate": self.gate.value,
            "verdict": self.verdict.value,
            "reasons": self.reasons,
            "hacking_margin": round(self.hack.hacking_margin, 4) if self.hack else 0.0,
        }

    def one_line(self) -> str:
        return (f"{self.task:<24} cap={self.capability:.2f} prop={self.propensity:.2f} "
                f"risk={self.risk:.2f} -> {self.gate.value:<6} ({self.verdict.value})")


def build_eval_card(task: Task, client, *, prove_risk: float = 0.05,
                    seed: int = 0) -> EvalCard:
    """Run the capability and propensity evals on ``task`` and decide the gate."""
    score = score_task(task, client, seed=seed)
    hack = probe_reward_hacks(task, client, seed=seed)

    capability = score.reward                                  # accept correct answers
    propensity = max(score.cost, hack.hacking_margin)          # admit wrong answers
    reasons: list[str] = []

    # decision: reject the unfixable, repair the recoverable, prove the rest
    if score.reward < 1.0 - 1e-9:
        gate, verdict = GateDecision.REJECT, Verdict.UNSOUND
        reasons.append(f"rejects correct answers (reward {score.reward:.2f} < 1)")
    elif hack.hacked and hack.ignores_input:
        gate, verdict = GateDecision.REJECT, Verdict.VACUOUS
        reasons.append(f"vacuous: constant impl '{hack.hacker}' collects full reward")
    elif propensity > prove_risk:
        gate, verdict = GateDecision.REPAIR, Verdict.INCOMPLETE
        reasons.append(f"admits wrong answers (propensity {propensity:.2f}); repair before proving")
        if hack.hacked:
            reasons.append(f"reward hack: {hack.hacker} (margin {hack.hacking_margin:.2f})")
    else:
        gate, verdict = GateDecision.PROVE, Verdict.FAITHFUL
        reasons.append("capability high, propensity low; safe to spend prover compute")

    return EvalCard(task=task.name, capability=capability, propensity=propensity,
                    gate=gate, verdict=verdict, score=score, hack=hack, reasons=reasons)

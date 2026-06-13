"""The code-specification falsification oracle.

Given a Verina-style :class:`~falsify.speccheck.task.Task` and any AXLE backend, decide
whether the task's specification is *faithful* — i.e. neither too strong nor too
weak — using three independent, executable checks:

  1. SOUNDNESS   — the *reference* implementation must satisfy the spec.
                   If it doesn't, the spec is too strong  → UNSOUND.
  2. COMPLETENESS — no *wrong* implementation may satisfy the spec.
                    If a known-bad mutant slips through → INCOMPLETE.
  3. VACUITY     — if even an "anything goes" implementation satisfies the spec,
                   the spec constrains nothing            → VACUOUS.

This is exactly the gap the Lean compiler is blind to: every one of these
specs *type-checks and is provable*; only an executable oracle reveals that the
statement is not what we meant. The check goes beyond Verina's fixed test suites
by actively searching for the falsifying implementation/input.
"""

from __future__ import annotations

from typing import Optional

from .task import Task
from ..core.oracle import Oracle, OracleResult, Verdict


class CodeSpecOracle(Oracle):
    name = "codespec"

    def __init__(self, client):
        self.client = client  # AxleClient or MockAxleClient

    def audit(self, task: Task) -> OracleResult:  # type: ignore[override]
        trials = 0

        # 1. SOUNDNESS: the reference must pass.
        ref = self.client.spec_satisfied(task, task.reference, task.spec)
        trials += 1
        if not ref.satisfied:
            return OracleResult(
                name=task.name,
                verdict=Verdict.UNSOUND,
                reason="spec is too strong — it rejects the correct reference implementation",
                counterexample=_ce(ref.counterexample),
                trials=trials,
                details={"check": "soundness"},
            )

        # 3. VACUITY (checked before generic mutants for a sharper verdict):
        #    if an "anything goes" impl passes, the spec constrains nothing.
        if task.arbitrary is not None:
            arb = self.client.spec_satisfied(task, task.arbitrary, task.spec)
            trials += 1
            if arb.satisfied:
                return OracleResult(
                    name=task.name,
                    verdict=Verdict.VACUOUS,
                    reason=(f"spec constrains nothing — even the throwaway impl "
                            f"'{task.arbitrary}' satisfies it"),
                    counterexample=f"impl '{task.arbitrary}' passes; spec fails to pin down the answer",
                    trials=trials,
                    details={"check": "vacuity"},
                )

        # 2. COMPLETENESS: no wrong implementation may pass.
        for mutant in task.wrong_impls:
            res = self.client.spec_satisfied(task, mutant, task.spec)
            trials += 1
            if res.satisfied:
                witness = task.differs_from_reference(mutant, task.test_inputs)
                return OracleResult(
                    name=task.name,
                    verdict=Verdict.INCOMPLETE,
                    reason=(f"spec is too weak — the wrong impl '{mutant}' satisfies it "
                            f"yet disagrees with the reference"),
                    counterexample=(f"impl '{mutant}' passes the spec; "
                                    f"differs from reference at input {witness}"),
                    trials=trials,
                    details={"check": "completeness", "mutant": mutant},
                )

        return OracleResult(
            name=task.name,
            verdict=Verdict.FAITHFUL,
            reason="reference passes; no wrong implementation slips through; not vacuous",
            trials=trials,
            details={"check": "all"},
        )


def _ce(ce: Optional[dict]) -> Optional[str]:
    if not ce:
        return None
    if "input" in ce:
        return f"reference fails spec at input {ce['input']} (→ output {ce.get('output')!r})"
    return str(ce)

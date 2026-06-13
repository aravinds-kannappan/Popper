"""M2 — counterexample-guided specification repair.

When the oracle falsifies a spec it returns a counterexample. A *repairer*
consumes that signal and proposes a stronger/weaker spec; the loop re-audits
until the verdict is FAITHFUL or the budget runs out. This is the whole point of
falsification over plain checking: the failure is *actionable*.

Repairers (offline, on the executable `Task` model — runnable + tested now):
  * :class:`TemplateRepairer`     — declarative repairs (what a good fix looks like).
  * :class:`FunctionalSpecRepairer` — generic fallback: pin the output to the
    reference (the strongest sound+complete spec; always converges).
  * :class:`ChainRepairer`        — try repairers in order.

:class:`LLMRepairer` is the path that scales to *real* Verina: given a task and a
counterexample it asks a model for a repaired Lean postcondition. It is gated on
``ANTHROPIC_API_KEY`` and returns Lean source to swap into the prelude and
re-audit live (see PROPOSAL.md, M2→live).
"""

from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass, field
from typing import Callable, Optional

from .axle import Task
from .oracle import GLYPH, OracleResult, Verdict


# --------------------------------------------------------------------------- #
# trace
# --------------------------------------------------------------------------- #
@dataclass
class RepairRound:
    spec: str
    verdict: Verdict
    reason: str
    counterexample: Optional[str]


@dataclass
class RepairTrace:
    task: str
    rounds: list[RepairRound] = field(default_factory=list)
    success: bool = False

    @property
    def final(self) -> Verdict:
        return self.rounds[-1].verdict

    def render(self) -> str:
        path = "  →  ".join(f"{GLYPH[r.verdict]}{r.verdict.value}" for r in self.rounds)
        head = f"{'✓' if self.success else '✗'} {self.task}: {path}"
        ce = next((r.counterexample for r in self.rounds if r.counterexample), None)
        return head + (f"\n      first counterexample: {ce}" if ce else "")


# --------------------------------------------------------------------------- #
# repairers
# --------------------------------------------------------------------------- #
class Repairer:
    def propose_spec(self, task: Task, result: OracleResult) -> Optional[Callable]:
        raise NotImplementedError


class FunctionalSpecRepairer(Repairer):
    """Generic, always-sound repair: require the output to equal the reference's.

    This is the strongest faithful spec; a smarter repairer (LLM) would then
    *weaken* it to a declarative form. It guarantees convergence for any task
    that has a reference implementation.
    """

    def propose_spec(self, task: Task, result: OracleResult) -> Optional[Callable]:
        ref = task.reference
        return lambda args, out, _ref=ref: out == task.impls_py[_ref](*args)


class TemplateRepairer(Repairer):
    """Declarative repairs for known shapes — illustrative of a *good* fix."""

    def __init__(self):
        def _sorted(args, out):
            xs = args[0]
            ascending = all(out[i] <= out[i + 1] for i in range(len(out) - 1))
            return ascending and sorted(out) == sorted(xs)        # sorted ∧ permutation

        self._templates = {
            "sort_by_length":        _sorted,
            "max_lower_bound_only":  lambda args, out: out >= args[0] and out >= args[1]
                                                       and (out == args[0] or out == args[1]),
            "abs_strictly_positive": lambda args, out: out >= 0
                                                       and (out == args[0] or out == -args[0]),
        }

    def propose_spec(self, task: Task, result: OracleResult) -> Optional[Callable]:
        return self._templates.get(task.name)


class ChainRepairer(Repairer):
    def __init__(self, repairers: list[Repairer]):
        self.repairers = repairers

    def propose_spec(self, task: Task, result: OracleResult) -> Optional[Callable]:
        for r in self.repairers:
            spec = r.propose_spec(task, result)
            if spec is not None:
                return spec
        return None


def default_repairer() -> Repairer:
    return ChainRepairer([TemplateRepairer(), FunctionalSpecRepairer()])


# --------------------------------------------------------------------------- #
# the loop
# --------------------------------------------------------------------------- #
def repair_loop(task: Task, oracle, repairer: Optional[Repairer] = None,
                max_rounds: int = 4) -> RepairTrace:
    repairer = repairer or default_repairer()
    t = dataclasses.replace(task, spec_py=dict(task.spec_py))
    trace = RepairTrace(task=task.name)

    for r in range(max_rounds + 1):
        res = oracle.audit(t)
        trace.rounds.append(RepairRound(t.spec, res.verdict, res.reason, res.counterexample))
        if res.verdict.is_faithful:
            trace.success = True
            break
        new_spec = repairer.propose_spec(t, res)
        if new_spec is None:
            break
        name = f"{t.spec}+repair{r}"
        specs = dict(t.spec_py)
        specs[name] = new_spec
        t = dataclasses.replace(t, spec=name, spec_py=specs)

    return trace


# --------------------------------------------------------------------------- #
# LLM repairer (scales to real Verina; needs ANTHROPIC_API_KEY)
# --------------------------------------------------------------------------- #
class LLMRepairer:
    """Ask a model for a repaired Lean postcondition given a counterexample.

    Used in the live Verina loop: the returned Lean replaces the postcondition in
    the task prelude, then the witnesses are re-audited via AXLE.
    """

    def __init__(self, model: str = "claude-opus-4-8", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    def propose_lean_repair(self, *, description: str, signature: str,
                            current_spec_lean: str, counterexample: str) -> str:
        if not self.api_key:
            raise RuntimeError("LLMRepairer needs ANTHROPIC_API_KEY (or pass api_key=...).")
        import anthropic  # lazy; only needed on the live LLM path
        client = anthropic.Anthropic(api_key=self.api_key)
        prompt = (
            "You repair Lean 4 specifications that are unfaithful to intent.\n\n"
            f"Task: {description}\nSignature: {signature}\n\n"
            f"Current (unfaithful) postcondition:\n{current_spec_lean}\n\n"
            f"An executable oracle found this counterexample: {counterexample}\n\n"
            "Return ONLY the corrected Lean postcondition body so that it accepts every "
            "correct output and rejects this counterexample. Prefer a declarative spec "
            "(properties of the output) over restating the implementation."
        )
        msg = client.messages.create(
            model=self.model, max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")

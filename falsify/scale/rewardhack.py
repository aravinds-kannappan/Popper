"""Active reward-hack synthesis for code specs.

*Natural Emergent Misalignment from Reward Hacking in Production RL* (MacDiarmid
et al., Anthropic 2025) shows a model placed in a real RL environment learns to
satisfy the graded objective in ways the authors never intended, and that the
hack generalizes to worse behaviour. A specification is exactly such an
environment: it is the reward the downstream prover, or a code-generating model,
optimizes against. A too-weak spec is a hackable reward, and the implementation
that games it is a reward hack the spec failed to reject.

Popper's offline code-spec oracle already checks completeness, but only against a
*fixed, hand-written* list of wrong implementations (``task.wrong_impls``). That
is the part a real adversary does not respect: the dangerous hack is the one you
did not enumerate. This module turns completeness checking into an active search.
It synthesizes a family of cheap candidate implementations - constant answers
lifted from the reference's own outputs, identity and structural mutants, clamps
and shifts - and looks for any candidate the spec *accepts* while it *disagrees
with the reference*. That candidate is the discovered reward hack, and the inputs
where it diverges are the counterexample.

The reported ``hacking_margin`` is the gap an RL optimizer would exploit:
``acceptance - agreement``, i.e. how often the spec says "good" minus how often
the implementation is actually right. Zero means the spec is unhackable by this
family; positive means free reward for being wrong.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from ..speccheck.task import Task
from ..core.oracle import OracleResult, Verdict


@dataclass
class RewardHackReport:
    task: str
    hacked: bool
    hacker: Optional[str] = None         # name of the winning candidate
    acceptance: float = 0.0              # fraction of inputs the spec accepts it on
    agreement: float = 0.0              # fraction of inputs it matches the reference on
    counterexample: Optional[str] = None
    candidates_tried: int = 0
    ignores_input: bool = False          # a constant hacker => the spec is vacuous

    @property
    def hacking_margin(self) -> float:
        """Free reward for being wrong: how much acceptance exceeds correctness."""
        return max(0.0, self.acceptance - self.agreement)

    @property
    def verdict(self) -> Verdict:
        if not self.hacked:
            return Verdict.FAITHFUL
        return Verdict.VACUOUS if self.ignores_input else Verdict.INCOMPLETE


def hacker_candidates(task: Task) -> dict[str, Callable[..., Any]]:
    """Cheap adversarial implementations that try to game ``task``'s spec.

    None of these are correct in general; each is a plausible shortcut an
    optimizer reaches for. A faithful spec rejects all of them.
    """
    ref = task.impls_py[task.reference]
    cands: dict[str, Callable[..., Any]] = {}

    # constant answers lifted from the reference's own outputs (the classic
    # "always return the same plausible-looking value" hack)
    seen: list[Any] = []
    for a in task.test_inputs:
        try:
            out = ref(*a)
        except Exception:
            continue
        if out not in seen:
            seen.append(out)
            cands[f"const::{out!r}"] = (lambda *args, _o=out: _o)

    # structural shortcuts on the first argument
    def _first(*args):
        return args[0]

    cands["identity_arg0"] = _first
    cands["reverse_arg0"] = lambda *args: (list(reversed(args[0]))
                                           if isinstance(args[0], list) else args[0])

    def _negate(*args):
        x = args[0]
        return -x if isinstance(x, (int, float)) and not isinstance(x, bool) else x

    cands["negate_arg0"] = _negate
    cands["off_by_one"] = lambda *args: (args[0] + 1
                                         if isinstance(args[0], (int, float))
                                         and not isinstance(args[0], bool) else args[0])

    # fold in the task's own declared hacks so the search is a superset of the
    # existing fixed completeness check
    for name in list(task.wrong_impls) + ([task.arbitrary] if task.arbitrary else []):
        if name in task.impls_py:
            cands[name] = task.impls_py[name]
    return cands


def _rates(task: Task, fn: Callable[..., Any], client, inputs) -> tuple[float, float, Optional[tuple]]:
    """Return (acceptance, agreement, first divergent input) for a candidate."""
    spec = task.spec_py[task.spec]
    ref = task.impls_py[task.reference]
    accepted = matched = total = 0
    first_div = None
    for args in inputs:
        try:
            out = fn(*args)
            ok = bool(spec(args, out))
            same = (out == ref(*args))
        except Exception:
            continue
        total += 1
        accepted += int(ok)
        matched += int(same)
        if ok and not same and first_div is None:
            first_div = args
    if total == 0:
        return 0.0, 0.0, None
    return accepted / total, matched / total, first_div


def probe_reward_hacks(task: Task, client, *, extra: Optional[dict] = None,
                       seed: int = 0) -> RewardHackReport:
    """Search the hacker family for an implementation that games ``task``'s spec.

    ``client`` is any AXLE backend (``MockAxleClient`` offline). ``extra`` lets a
    caller inject additional candidate implementations (e.g. a model's own
    samples) into the search.
    """
    import random

    rng = random.Random(seed)
    inputs = list(task.test_inputs) + [task.gen_input(rng) for _ in range(task.fuzz_n)]

    cands = hacker_candidates(task)
    if extra:
        cands.update(extra)

    best: Optional[RewardHackReport] = None
    for name, fn in cands.items():
        acc, agr, div = _rates(task, fn, client, inputs)
        # a reward hack fully satisfies the spec yet is not the reference
        if acc >= 1.0 - 1e-9 and agr < 1.0 - 1e-9:
            # a constant answer, or the task's declared "anything goes" impl,
            # means the spec pins down nothing => vacuous rather than merely loose
            ignores = name.startswith("const::") or name == task.arbitrary
            ce = (f"impl '{name}' satisfies the spec on every input yet diverges from the "
                  f"reference at {div} (accept={acc:.2f}, agree={agr:.2f})")
            report = RewardHackReport(
                task=task.name, hacked=True, hacker=name, acceptance=acc, agreement=agr,
                counterexample=ce, candidates_tried=len(cands), ignores_input=ignores)
            # prefer the most damaging hack (largest margin), and a vacuity hack
            # outranks a merely-incomplete one
            if best is None or report.hacking_margin > best.hacking_margin:
                best = report

    if best is not None:
        return best
    return RewardHackReport(task=task.name, hacked=False, candidates_tried=len(cands))


def as_oracle_result(report: RewardHackReport) -> OracleResult:
    """Render a :class:`RewardHackReport` in the shared OracleResult vocabulary."""
    if not report.hacked:
        return OracleResult(
            name=report.task, verdict=Verdict.FAITHFUL,
            reason=f"no reward hack found in {report.candidates_tried} candidates",
            trials=report.candidates_tried, details={"check": "reward-hack"})
    reason = ("spec is hackable: a wrong implementation collects full reward "
              f"(margin {report.hacking_margin:.2f})")
    return OracleResult(
        name=report.task, verdict=report.verdict, reason=reason,
        counterexample=report.counterexample, trials=report.candidates_tried,
        details={"check": "reward-hack", "hacker": report.hacker,
                 "hacking_margin": round(report.hacking_margin, 4)})

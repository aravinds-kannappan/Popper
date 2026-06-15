"""The three judges the benchmark compares.

A judge looks at one :class:`Item` and returns an :class:`OracleResult`: its
verdict, and a counterexample when it has one. The interesting differences show
up in the scoring (see ``metrics.py``):

  * ``proof_checker_judge`` never returns anything but FAITHFUL, because a proof
    checker has no way to object to a spec that type checks.
  * ``llm_judge`` may guess the right label, but it returns no executable witness.
  * ``popper_judge`` returns a concrete counterexample whenever it flags an item.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from ..core.oracle import OracleResult, Verdict
from ..montecarlo.numerical import NumericalOracle
from .corpus import Item


# --------------------------------------------------------------------------- #
# Popper: the executable oracle
# --------------------------------------------------------------------------- #
def popper_judge(item: Item, *, n_trials: int = 2000, seed: int = 0) -> OracleResult:
    """Run the real Popper oracle for this item's surface."""
    if item.surface == "math":
        return NumericalOracle(n_trials=n_trials, seed=seed).audit(item.math)
    # code / verina: replay the oracle's recorded verdict (real AXLE / fixture runs)
    r = item.precomputed or {}
    return OracleResult(
        name=item.name,
        verdict=Verdict(r.get("verdict", "FAITHFUL")),
        reason=r.get("reason", ""),
        counterexample=r.get("counterexample") or None,
        trials=int(r.get("trials", 0)),
        details={k: v for k, v in r.items() if k not in {"name", "verdict", "reason", "counterexample", "trials"}},
    )


# --------------------------------------------------------------------------- #
# Proof checker baseline: Lean / AXLE alone
# --------------------------------------------------------------------------- #
def proof_checker_judge(item: Item) -> OracleResult:
    """The proof-checker baseline.

    A Lean / AXLE check answers 'does this proof match this statement', not 'is
    this statement faithful'. Every spec in the corpus type checks, so the
    checker has nothing to say about faithfulness: it accepts all of them. That
    is the entire problem Popper exists to fix, stated as a baseline.
    """
    return OracleResult(
        name=item.name,
        verdict=Verdict.FAITHFUL,
        reason="type checks; a proof checker cannot object to the spec itself",
        counterexample=None,
        trials=0,
        details={"judge": "proof_checker"},
    )


# --------------------------------------------------------------------------- #
# LLM judge: a model reads the statement and guesses, with no execution
# --------------------------------------------------------------------------- #
_LLM_SYSTEM = (
    "You audit formal statements for faithfulness to a stated intent. You do NOT "
    "run code or a prover. Given the intent and the formal statement, decide whether "
    "the statement faithfully captures the intent. Reply with a single JSON object: "
    '{\"label\": one of \"FAITHFUL\",\"FALSIFIED\",\"VACUOUS\",\"INCONCLUSIVE\", '
    '\"why\": short reason}. Use FALSIFIED if the statement is wrong (dropped '
    "hypothesis, flipped direction, over-strong or over-weak), VACUOUS if it "
    "constrains nothing, FAITHFUL if it looks correct."
)


def llm_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def llm_judge(item: Item, *, model: Optional[str] = None, client=None) -> OracleResult:
    """Ask a model to classify the item. Requires ANTHROPIC_API_KEY.

    The model never sees a counterexample and never runs anything, which is the
    whole point of the comparison: even when it guesses right, it cannot hand you
    the witness that makes the bug actionable.
    """
    if not llm_available():
        return OracleResult(
            name=item.name,
            verdict=Verdict.INCONCLUSIVE,
            reason="LLM judge not run (set ANTHROPIC_API_KEY to enable)",
            counterexample=None,
            details={"judge": "llm", "skipped": True},
        )

    import anthropic

    client = client or anthropic.Anthropic()
    model = model or os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
    prompt = (
        f"Intent: {item.intent}\n"
        f"Formal statement: {item.statement}\n"
        f"Surface: {item.surface}\n"
        "Is this statement faithful to the intent?"
    )
    msg = client.messages.create(
        model=model,
        max_tokens=400,
        system=_LLM_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    label, why = _parse_label(text)
    return OracleResult(
        name=item.name,
        verdict=label,
        reason=why or "LLM judgement",
        counterexample=None,  # a guess, never an executable witness
        details={"judge": "llm", "raw": text},
    )


def _parse_label(text: str) -> tuple[Verdict, str]:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        obj = json.loads(text[start:end])
        label = str(obj.get("label", "INCONCLUSIVE")).upper()
        return Verdict(label), str(obj.get("why", ""))
    except Exception:
        upper = text.upper()
        for v in (Verdict.FALSIFIED, Verdict.VACUOUS, Verdict.UNSOUND, Verdict.INCOMPLETE, Verdict.FAITHFUL):
            if v.value in upper:
                return v, "parsed from free text"
        return Verdict.INCONCLUSIVE, "could not parse"

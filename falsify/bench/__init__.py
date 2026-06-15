"""Benchmark: spec-faithfulness detection, Popper vs the alternatives.

The point of this folder is to put a number on the claim the rest of the repo
makes in prose: a proof checker tells you a proof matches a statement, but it
cannot tell you the statement is the right one. Popper can.

We measure that on a labelled corpus of formal claims where each item is tagged
ahead of time as faithful or unfaithful (and how it is unfaithful), then run
three judges over the same corpus:

  * ``proof_checker``  -- the Lean / AXLE baseline. It accepts anything that
    type checks, so on a faithfulness task it never objects. This is not a straw
    man: it is exactly what a proof checker does, and the whole problem is that
    an unfaithful spec still type checks and is still provable against itself.
  * ``llm_judge``      -- a model reads the statement plus the intent and guesses
    faithful or unfaithful, with no execution. Runnable live against the Anthropic
    API; see ``judges.py``.
  * ``popper``         -- the executable oracle in this repo. It tries to break
    the statement and returns a concrete counterexample when it succeeds.

``corpus.py`` builds the data, ``judges.py`` the three judges, ``metrics.py`` the
scoring, and ``run.py`` ties it together.
"""

from .corpus import benchmark_corpus, Item
from .judges import popper_judge, proof_checker_judge, llm_judge
from .metrics import score_judge, JudgeScore

__all__ = [
    "benchmark_corpus",
    "Item",
    "popper_judge",
    "proof_checker_judge",
    "llm_judge",
    "score_judge",
    "JudgeScore",
]

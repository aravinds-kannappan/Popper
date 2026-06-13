"""Mutation / property-search engine for the code-spec oracle.

Mutation testing for *specifications* is the heart of completeness checking: if
a deliberately-broken implementation still satisfies the spec, the spec is too
weak. This module provides

  * source-level Lean mutation operators (the live-path mutant *generator*), and
  * simple input fuzzers used by the offline evaluator.

The operators are intentionally syntactic and cheap; their job is to manufacture
plausible-but-wrong implementations and adversarial inputs, not to be clever.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable


@dataclass
class Mutant:
    op: str
    source: str


# --- source-level Lean mutation operators ---------------------------------- #
def _swap_first(s: str, a: str, b: str) -> str:
    i = s.find(a)
    return s if i < 0 else s[:i] + b + s[i + len(a):]


_OPS: dict[str, Callable[[str], str]] = {
    "arith_plus_to_minus": lambda s: _swap_first(s, "+", "-"),
    "arith_minus_to_plus": lambda s: _swap_first(s, "-", "+"),
    "cmp_lt_to_le":        lambda s: _swap_first(s, "<", "≤"),
    "cmp_gt_to_ge":        lambda s: _swap_first(s, ">", "≥"),
    "bool_true_to_false":  lambda s: _swap_first(s, "true", "false"),
    "off_by_one_plus1":    lambda s: _swap_first(s, ":=", ":= 1 +"),
}


def mutate(source: str, ops: list[str] | None = None) -> list[Mutant]:
    """Return every mutant that actually changes ``source``."""
    chosen = ops or list(_OPS)
    out: list[Mutant] = []
    for op in chosen:
        mutated = _OPS[op](source)
        if mutated != source:
            out.append(Mutant(op=op, source=mutated))
    return out


def available_ops() -> list[str]:
    return list(_OPS)


# --- input fuzzers --------------------------------------------------------- #
def fuzz_int(rng: random.Random, lo: int = -1000, hi: int = 1000) -> int:
    # bias toward edge cases that flush out unsound/incomplete specs
    if rng.random() < 0.25:
        return rng.choice([0, 1, -1, lo, hi])
    return rng.randint(lo, hi)


def fuzz_list_int(rng: random.Random, max_len: int = 6) -> list[int]:
    n = rng.randint(0, max_len)
    return [fuzz_int(rng, -20, 20) for _ in range(n)]

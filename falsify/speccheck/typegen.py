"""Type-directed input generation, so the spec oracle scales past hand-written fixtures.

The offline ``Task`` model needs a ``gen_input`` and ``test_inputs`` written by
hand for every task. That does not scale to the full 189-task Verina set, let
alone arbitrary signatures. This module derives both from the *type* of the
signature, the way QuickCheck (random) and SmallCheck (exhaustive small-scope)
derive generators from Haskell types.

A :class:`TypeSpec` describes an argument type (``Int``, ``Bool``, ``Nat``,
``List t``, tuples). :func:`gen` samples one value with edge-case bias;
:func:`enumerate_small` yields every value up to a small scope, which is exactly
the regime where most spec bugs live (empty list, singleton, a zero, a negative).
:func:`parse_signature` reads a Verina-style ``name : Int -> List Int -> Int``
into argument types, and :func:`gen_inputs_for` produces the ``gen_input`` an
oracle needs - so a task can be audited with no bespoke generator at all.

Pure standard library.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterator, Optional


# --------------------------------------------------------------------------- #
# type language
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TInt:
    lo: int = -1000
    hi: int = 1000


@dataclass(frozen=True)
class TNat:
    hi: int = 1000


@dataclass(frozen=True)
class TBool:
    pass


@dataclass(frozen=True)
class TList:
    elem: "TypeSpec"
    max_len: int = 6


@dataclass(frozen=True)
class TTuple:
    parts: tuple


TypeSpec = object  # one of the dataclasses above


# --------------------------------------------------------------------------- #
# random generation (edge-biased), the QuickCheck flavour
# --------------------------------------------------------------------------- #
def gen(t: TypeSpec, rng: random.Random):
    if isinstance(t, TInt):
        if rng.random() < 0.3:
            return rng.choice([0, 1, -1, t.lo, t.hi])
        return rng.randint(t.lo, t.hi)
    if isinstance(t, TNat):
        if rng.random() < 0.3:
            return rng.choice([0, 1, t.hi])
        return rng.randint(0, t.hi)
    if isinstance(t, TBool):
        return rng.random() < 0.5
    if isinstance(t, TList):
        n = rng.randint(0, t.max_len)
        return [gen(t.elem, rng) for _ in range(n)]
    if isinstance(t, TTuple):
        return tuple(gen(p, rng) for p in t.parts)
    raise TypeError(f"no generator for {t!r}")


# --------------------------------------------------------------------------- #
# exhaustive small-scope enumeration, the SmallCheck flavour
# --------------------------------------------------------------------------- #
def enumerate_small(t: TypeSpec, scope: int = 2) -> Iterator:
    """Yield every value of ``t`` within the given small scope.

    ``scope`` bounds magnitude (ints in ``[-scope, scope]``) and structure (lists
    up to length ``scope``). Small but systematic: this is where the empty-list
    and zero bugs hide.
    """
    if isinstance(t, TInt):
        yield from range(max(t.lo, -scope), min(t.hi, scope) + 1)
    elif isinstance(t, TNat):
        yield from range(0, min(t.hi, scope) + 1)
    elif isinstance(t, TBool):
        yield from (False, True)
    elif isinstance(t, TList):
        for length in range(0, scope + 1):
            yield from _lists_of_length(t.elem, length, scope)
    elif isinstance(t, TTuple):
        yield from _tuples(t.parts, scope)
    else:
        raise TypeError(f"no enumerator for {t!r}")


def _lists_of_length(elem: TypeSpec, length: int, scope: int) -> Iterator[list]:
    if length == 0:
        yield []
        return
    for head in enumerate_small(elem, scope):
        for tail in _lists_of_length(elem, length - 1, scope):
            yield [head] + tail


def _tuples(parts: tuple, scope: int) -> Iterator[tuple]:
    if not parts:
        yield ()
        return
    for head in enumerate_small(parts[0], scope):
        for rest in _tuples(parts[1:], scope):
            yield (head,) + rest


# --------------------------------------------------------------------------- #
# signature parsing  (Verina style:  name : T1 -> T2 -> ... -> Ret)
# --------------------------------------------------------------------------- #
_ATOMS = {
    "Int": TInt(), "Nat": TNat(), "Bool": TBool(),
}


def parse_type(s: str) -> TypeSpec:
    s = s.strip()
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()
    if s.startswith("List "):
        return TList(parse_type(s[len("List "):]))
    if s in _ATOMS:
        return _ATOMS[s]
    raise ValueError(f"unsupported type: {s!r}")


def _split_top_arrows(s: str) -> list[str]:
    """Split on top-level ``->`` (not inside parentheses)."""
    parts, depth, cur = [], 0, ""
    i = 0
    while i < len(s):
        c = s[i]
        if c == "(":
            depth += 1
            cur += c
        elif c == ")":
            depth -= 1
            cur += c
        elif c == "-" and i + 1 < len(s) and s[i + 1] == ">" and depth == 0:
            parts.append(cur)
            cur = ""
            i += 2
            continue
        else:
            cur += c
        i += 1
    parts.append(cur)
    return [p.strip() for p in parts]


def parse_signature(signature: str) -> tuple[list, TypeSpec]:
    """Return ``(arg_types, return_type)`` for a ``name : T1 -> ... -> Ret`` string."""
    body = signature.split(":", 1)[1] if ":" in signature else signature
    pieces = _split_top_arrows(body)
    types = [parse_type(p) for p in pieces]
    return types[:-1], types[-1]


# --------------------------------------------------------------------------- #
# the thing oracles actually consume
# --------------------------------------------------------------------------- #
def gen_inputs_for(arg_types: list):
    """Return a ``gen_input(rng) -> args`` callable for the given argument types."""
    return lambda rng: tuple(gen(t, rng) for t in arg_types)


def small_inputs_for(arg_types: list, scope: int = 2, cap: int = 400) -> list[tuple]:
    """Enumerate the small-scope cartesian product of the arguments (capped)."""
    out: list[tuple] = []
    for combo in _tuples(tuple(arg_types), scope):
        out.append(combo)
        if len(out) >= cap:
            break
    return out


@dataclass
class GeneratedInputs:
    arg_types: list
    gen_input: object
    test_inputs: list

    @classmethod
    def from_signature(cls, signature: str, scope: int = 2) -> "GeneratedInputs":
        arg_types, _ = parse_signature(signature)
        return cls(arg_types=arg_types,
                   gen_input=gen_inputs_for(arg_types),
                   test_inputs=small_inputs_for(arg_types, scope=scope))

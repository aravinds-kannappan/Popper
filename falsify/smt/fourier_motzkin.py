"""Exact linear-arithmetic decision by Fourier-Motzkin elimination.

This is the stdlib half of Popper's answer to "sampling misses measure-zero
bugs". Where the Monte-Carlo and adaptive engines *search* and can only report
"no counterexample within budget", this procedure *decides*: for a conjunction of
linear inequalities over the rationals it either returns an exact rational
witness or proves the system has no solution at all. An UNSAT result is a genuine
certificate of faithfulness for the linear fragment, not a budget-limited guess.

Everything runs in exact rational arithmetic (``fractions.Fraction``), so there
is no floating-point slop in either the witness or the certificate. The algorithm
is the classical one (Fourier 1826, Motzkin 1936): to eliminate a variable, pair
every upper bound on it with every lower bound and keep the implied constraint on
the remaining variables; a model is then rebuilt by back-substitution.

Constraints are normalised to ``sum(coeffs[v] * v) + const <op> 0`` with ``op``
either ``<=`` (``strict=False``) or ``<`` (``strict=True``). Equalities and the
``>=``/``>`` directions are desugared by the caller (see :mod:`.symbolic`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Optional


@dataclass(frozen=True)
class LinCon:
    """``sum(coeffs[v] * v) + const < 0`` (strict) or ``<= 0`` (non-strict)."""

    coeffs: tuple              # tuple of (var_name, Fraction)
    const: Fraction
    strict: bool = False

    def coeff(self, v: str) -> Fraction:
        for name, c in self.coeffs:
            if name == v:
                return c
        return Fraction(0)

    def vars(self) -> set:
        return {name for name, _ in self.coeffs}


def con(coeffs: dict, const, strict: bool = False) -> LinCon:
    items = tuple((k, Fraction(v)) for k, v in coeffs.items() if Fraction(v) != 0)
    return LinCon(coeffs=items, const=Fraction(const), strict=strict)


@dataclass
class Solution:
    sat: bool
    witness: Optional[dict] = None          # var -> Fraction
    certificate: bool = False               # True when sat is False and proven so
    note: str = ""


def _combine(cp: LinCon, cn: LinCon, v: str) -> LinCon:
    """Eliminate ``v`` from a (upper, lower) pair, both in ``<op> 0`` form."""
    ap = cp.coeff(v)      # > 0
    an = cn.coeff(v)      # < 0
    merged: dict = {}
    for name in cp.vars() | cn.vars():
        if name == v:
            continue
        val = (-an) * cp.coeff(name) + ap * cn.coeff(name)
        if val != 0:
            merged[name] = val
    const = (-an) * cp.const + ap * cn.const
    return con(merged, const, cp.strict or cn.strict)


def _eliminate(v: str, cons: list[LinCon]) -> list[LinCon]:
    pos, neg, zero = [], [], []
    for c in cons:
        a = c.coeff(v)
        (pos if a > 0 else neg if a < 0 else zero).append(c)
    out = list(zero)
    for cp in pos:
        for cn in neg:
            out.append(_combine(cp, cn, v))
    return out


def solve(cons: list[LinCon], order: list[str]) -> Solution:
    """Decide feasibility of the conjunction and return a witness if SAT.

    ``order`` lists every variable; elimination proceeds in that order and the
    witness is rebuilt in reverse.
    """
    # keep the system *before* eliminating each variable, for back-substitution
    systems: list[list[LinCon]] = []
    cur = list(cons)
    for v in order:
        systems.append(cur)
        cur = _eliminate(v, cur)

    # base case: only constant constraints remain
    for c in cur:
        if c.strict and not (c.const < 0):
            return Solution(sat=False, certificate=True,
                            note=f"residual {c.const} < 0 is false")
        if not c.strict and not (c.const <= 0):
            return Solution(sat=False, certificate=True,
                            note=f"residual {c.const} <= 0 is false")

    # rebuild a model from last-eliminated variable back to the first
    assign: dict = {}
    for i in range(len(order) - 1, -1, -1):
        v = order[i]
        lo = hi = None
        lo_strict = hi_strict = False
        for c in systems[i]:
            a = c.coeff(v)
            if a == 0:
                continue
            rest = c.const + sum(c.coeff(x) * assign[x] for x in c.vars() if x != v)
            bound = -rest / a
            if a > 0:                      # v <op> bound  (upper)
                if hi is None or bound < hi:
                    hi, hi_strict = bound, c.strict
                elif bound == hi:
                    hi_strict = hi_strict or c.strict
            else:                          # v <op> bound  (lower)
                if lo is None or bound > lo:
                    lo, lo_strict = bound, c.strict
                elif bound == lo:
                    lo_strict = lo_strict or c.strict
        assign[v] = _pick(lo, lo_strict, hi, hi_strict)

    return Solution(sat=True, witness=assign)


def _pick(lo, lo_strict, hi, hi_strict) -> Fraction:
    if lo is None and hi is None:
        return Fraction(0)
    if lo is None:
        return hi - 1 if hi_strict else hi
    if hi is None:
        return lo + 1 if lo_strict else lo
    if lo < hi:
        return (lo + hi) / 2
    # lo == hi: only a single point can work, and only if both sides are non-strict
    return lo

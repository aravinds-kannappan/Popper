"""Symbolic claims for the exact falsification engine.

A :class:`SymbolicClaim` is the exact-arithmetic analogue of a Monte-Carlo
``Statement`` or a ``ScoredClaim``. Instead of a sampler it carries typed
variables and a description of the *falsification target* ``H and not C`` in
whatever forms the available backends can decide:

  * ``falsifies(env)`` - a numeric predicate over a concrete assignment, used by
    the integer-enumeration backend and to validate any witness an exact backend
    returns.
  * ``linear`` - the target as a conjunction of :class:`~.fourier_motzkin.LinCon`
    over the rationals, for the Fourier-Motzkin backend (exact, stdlib).
  * ``z3_build`` - the target as a Z3 formula, for the optional Z3 backend
    (handles the nonlinear cases enumeration and FM cannot).

The bundled :func:`symbolic_library` mirrors the faithful/unfaithful pairs the
other engines use, so the same bugs (a too-strong abs spec, a too-weak max spec,
an over-claimed mean) can be decided *exactly* rather than sampled, and a genuine
faithful statement can be issued a real certificate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from ..core.oracle import Verdict
from .fourier_motzkin import LinCon, con


@dataclass
class Var:
    name: str
    kind: str = "int"          # "int" | "real"
    lo: float = -100
    hi: float = 100

    @property
    def is_int(self) -> bool:
        return self.kind == "int"


@dataclass
class SymbolicClaim:
    name: str
    description: str
    variables: list[Var]
    falsifies: Callable[[dict], bool]                       # numeric H and not C
    linear: Optional[tuple] = None                          # (list[LinCon], order)
    z3_build: Optional[Callable] = None                     # (z3, {name: z3var}) -> BoolRef
    expected: Optional[Verdict] = None
    summarize: Optional[Callable[[dict], str]] = None
    tags: tuple = ()

    @property
    def all_int(self) -> bool:
        return all(v.is_int for v in self.variables)

    def render_ce(self, env: dict) -> str:
        if self.summarize is not None:
            return self.summarize(env)
        return ", ".join(f"{k}={_fmt(v)}" for k, v in env.items())


def _fmt(v) -> str:
    try:
        from fractions import Fraction
        if isinstance(v, Fraction):
            return str(v) if v.denominator != 1 else str(v.numerator)
    except Exception:
        pass
    return repr(v)


# --------------------------------------------------------------------------- #
# A library mirroring the offline fixtures, decided exactly.
# --------------------------------------------------------------------------- #
def symbolic_library() -> list[SymbolicClaim]:
    claims: list[SymbolicClaim] = []

    # 1. abs spec that wrongly demands out > 0: UNSOUND, witnessed exactly at x = 0.
    claims.append(SymbolicClaim(
        name="abs_strictly_positive",
        description="soundness: does out > 0 reject the correct abs(0) = 0?",
        variables=[Var("x", "int", -8, 8)],
        falsifies=lambda e: abs(e["x"]) <= 0,        # ref output abs(x) violates out > 0
        expected=Verdict.FALSIFIED,
        summarize=lambda e: f"x={e['x']}: abs(x)=0 is rejected by out > 0 (UNSOUND)",
        tags=("soundness",),
    ))

    # 2. abs spec that is actually faithful: no witness over the box => certificate.
    claims.append(SymbolicClaim(
        name="abs_value_faithful",
        description="soundness: out >= 0 and out in {x, -x} accepts every correct abs",
        variables=[Var("x", "int", -50, 50)],
        falsifies=lambda e: not (abs(e["x"]) >= 0 and abs(e["x"]) in (e["x"], -e["x"])),
        expected=Verdict.FAITHFUL,
        tags=("soundness",),
    ))

    # 3. max spec out >= a and out >= b accepts max(a,b)+1: INCOMPLETE, exact witness.
    claims.append(SymbolicClaim(
        name="max_lower_bound_only",
        description="completeness: max(a,b)+1 satisfies out>=a and out>=b yet is wrong",
        variables=[Var("a", "int", -6, 6), Var("b", "int", -6, 6)],
        falsifies=lambda e: (max(e["a"], e["b"]) + 1 >= e["a"]
                             and max(e["a"], e["b"]) + 1 >= e["b"]
                             and max(e["a"], e["b"]) + 1 != max(e["a"], e["b"])),
        expected=Verdict.FALSIFIED,
        summarize=lambda e: (f"a={e['a']}, b={e['b']}: max+1={max(e['a'],e['b'])+1} "
                             f"satisfies the spec but != max={max(e['a'],e['b'])} (INCOMPLETE)"),
        tags=("completeness",),
    ))

    # 4. a measure-zero integer bug: score(n) != 7 fails only at n = 7 in a big box.
    claims.append(SymbolicClaim(
        name="rare_int_needle",
        description="a postcondition that fails on exactly one of 20,001 integers",
        variables=[Var("n", "int", 0, 20000)],
        falsifies=lambda e: e["n"] == 7,
        expected=Verdict.FALSIFIED,
        summarize=lambda e: f"n={e['n']} is the single rejecting input (1 in 20,001)",
        tags=("needle",),
    ))

    # 5. over-claim "mean(x) >= 0 for all x": FALSIFIED, exact rational witness (linear).
    claims.append(SymbolicClaim(
        name="mean_nonneg_overclaim",
        description="over-claim: (x0 + x1) / 2 >= 0 for all reals",
        variables=[Var("x0", "real"), Var("x1", "real")],
        falsifies=lambda e: e["x0"] + e["x1"] < 0,
        linear=([con({"x0": 1, "x1": 1}, 0, strict=True)], ["x0", "x1"]),
        expected=Verdict.FALSIFIED,
        summarize=lambda e: f"x0={_fmt(e['x0'])}, x1={_fmt(e['x1'])}: mean < 0",
        tags=("over-claim", "linear"),
    ))

    # 6. a genuinely true linear statement: UNSAT to falsify => a real certificate.
    claims.append(SymbolicClaim(
        name="nonneg_sum_certificate",
        description="if x0 >= 0 and x1 >= 0 then x0 + x1 >= 0 (true; certifiable)",
        variables=[Var("x0", "real"), Var("x1", "real")],
        falsifies=lambda e: e["x0"] >= 0 and e["x1"] >= 0 and e["x0"] + e["x1"] < 0,
        linear=([con({"x0": -1}, 0), con({"x1": -1}, 0),
                 con({"x0": 1, "x1": 1}, 0, strict=True)], ["x0", "x1"]),
        expected=Verdict.FAITHFUL,
        tags=("certificate", "linear"),
    ))

    # 7. a NONLINEAR bug only the optional Z3 backend can decide.
    def _amgm_z3(z3, s):
        x0, x1 = s["x0"], s["x1"]
        # claim as written (wrong direction): x0*x1 >= ((x0+x1)/2)^2
        # falsification: 0<=x0,x1<=10 and x0*x1 < ((x0+x1)/2)^2
        return z3.And(x0 >= 0, x0 <= 10, x1 >= 0, x1 <= 10,
                      4 * x0 * x1 < (x0 + x1) * (x0 + x1))

    claims.append(SymbolicClaim(
        name="amgm_flipped_nonlinear",
        description="wrong-direction AM-GM: x0*x1 >= ((x0+x1)/2)^2 (nonlinear)",
        variables=[Var("x0", "real", 0, 10), Var("x1", "real", 0, 10)],
        falsifies=lambda e: e["x0"] * e["x1"] < ((e["x0"] + e["x1"]) / 2) ** 2 - 1e-12,
        z3_build=_amgm_z3,
        expected=Verdict.FALSIFIED,
        summarize=lambda e: (f"x0={_fmt(e['x0'])}, x1={_fmt(e['x1'])}: "
                             f"product < squared mean (AM-GM flipped)"),
        tags=("direction-error", "nonlinear"),
    ))

    return claims

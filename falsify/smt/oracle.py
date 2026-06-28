"""The exact-falsification oracle and its backends.

Three backends sit behind the shared :class:`~falsify.core.oracle.Oracle`
interface, ordered from cheapest-and-most-portable to most-general:

  * :class:`EnumBackend` - exhaustive integer enumeration over the declared box.
    Pure stdlib, exact. A no-witness result is a certificate *scoped to that box*.
  * :class:`LinearBackend` - Fourier-Motzkin over the rationals for linear
    claims. Pure stdlib, exact. A no-witness result is an unbounded certificate
    over all of Q.
  * :class:`Z3Backend` - the optional SMT path for nonlinear arithmetic, lazily
    importing ``z3`` (``pip install 'falsify[smt]'``). Absent z3, claims that need
    it return INCONCLUSIVE with a clear note rather than a wrong answer.

This is the engine that converts Popper's honest "no counterexample within
budget" into either an exact counterexample in the measure-zero region a sampler
would miss, or a real certificate of faithfulness for the decidable fragment.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Optional

from ..core.oracle import Oracle, OracleResult, Verdict
from .fourier_motzkin import solve as fm_solve
from .symbolic import SymbolicClaim


@dataclass
class BackendResult:
    status: str                       # "sat" | "unsat" | "unknown"
    witness: Optional[dict] = None
    note: str = ""
    backend: str = ""


class EnumBackend:
    name = "enum"

    def __init__(self, max_cells: int = 5_000_000):
        self.max_cells = max_cells

    def applicable(self, claim: SymbolicClaim) -> bool:
        if not claim.all_int:
            return False
        cells = 1
        for v in claim.variables:
            cells *= int(v.hi - v.lo + 1)
            if cells > self.max_cells:
                return False
        return True

    def solve(self, claim: SymbolicClaim) -> BackendResult:
        import itertools

        ranges = [range(int(v.lo), int(v.hi) + 1) for v in claim.variables]
        names = [v.name for v in claim.variables]
        cells = 0
        for combo in itertools.product(*ranges):
            env = dict(zip(names, combo))
            cells += 1
            if claim.falsifies(env):
                return BackendResult("sat", witness=env, backend=self.name,
                                     note=f"exact witness found after scanning {cells} points")
        return BackendResult("unsat", backend=self.name,
                             note=f"exhaustive over the integer box ({cells} points); no witness")


class LinearBackend:
    name = "fourier-motzkin"

    def applicable(self, claim: SymbolicClaim) -> bool:
        return claim.linear is not None

    def solve(self, claim: SymbolicClaim) -> BackendResult:
        cons, order = claim.linear
        sol = fm_solve(list(cons), list(order))
        if sol.sat:
            return BackendResult("sat", witness=sol.witness, backend=self.name,
                                 note="exact rational witness by Fourier-Motzkin")
        return BackendResult("unsat", backend=self.name,
                             note=f"linear system infeasible over Q ({sol.note})")


class Z3Backend:
    name = "z3"

    def applicable(self, claim: SymbolicClaim) -> bool:
        if claim.z3_build is None:
            return False
        try:
            import z3  # noqa: F401
        except Exception:
            return False
        return True

    def solve(self, claim: SymbolicClaim) -> BackendResult:
        import z3

        syms = {v.name: (z3.Int(v.name) if v.is_int else z3.Real(v.name))
                for v in claim.variables}
        s = z3.Solver()
        s.add(claim.z3_build(z3, syms))
        r = s.check()
        if r == z3.sat:
            m = s.model()
            witness = {name: _from_z3(m, sym) for name, sym in syms.items()}
            return BackendResult("sat", witness=witness, backend=self.name,
                                 note="model found by z3 (nonlinear arithmetic)")
        if r == z3.unsat:
            return BackendResult("unsat", backend=self.name,
                                 note="z3 proved the falsification target unsatisfiable")
        return BackendResult("unknown", backend=self.name, note="z3 returned unknown")


def _from_z3(model, sym):
    val = model.eval(sym, model_completion=True)
    try:
        if val.is_int():
            return int(val.as_long())
        num, den = val.numerator_as_long(), val.denominator_as_long()
        return Fraction(num, den)
    except Exception:
        return float(val.as_decimal(10).rstrip("?")) if hasattr(val, "as_decimal") else str(val)


def default_backends() -> list:
    return [EnumBackend(), LinearBackend(), Z3Backend()]


class SMTOracle(Oracle):
    """Decide a :class:`SymbolicClaim` exactly, picking the first apt backend."""

    name = "smt"

    def __init__(self, backends: Optional[list] = None):
        self.backends = backends or default_backends()

    def audit(self, claim: SymbolicClaim) -> OracleResult:  # type: ignore[override]
        last_note = "no applicable exact backend"
        for backend in self.backends:
            if not backend.applicable(claim):
                continue
            res = backend.solve(claim)
            if res.status == "unknown":
                last_note = f"{backend.name}: {res.note}"
                continue
            if res.status == "sat":
                return OracleResult(
                    name=claim.name, verdict=Verdict.FALSIFIED,
                    reason=f"exact counterexample via {res.backend}",
                    counterexample=claim.render_ce(res.witness or {}),
                    trials=1,
                    details={"backend": res.backend, "certificate": False, "note": res.note})
            # unsat: a genuine certificate of faithfulness for this fragment
            return OracleResult(
                name=claim.name, verdict=Verdict.FAITHFUL,
                reason=f"certified faithful via {res.backend}: {res.note}",
                trials=1,
                details={"backend": res.backend, "certificate": True, "note": res.note})
        # nothing could decide it (typically nonlinear with z3 absent)
        return OracleResult(
            name=claim.name, verdict=Verdict.INCONCLUSIVE,
            reason=f"no exact decision ({last_note}); install 'falsify[smt]' for nonlinear",
            trials=0, details={"certificate": False, "note": last_note})

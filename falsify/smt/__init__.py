"""falsify.smt - exact falsification: decide the statement, do not just sample it.

The Monte-Carlo and adaptive engines search; this one *decides*. For the
decidable fragment (integer domains, linear rational arithmetic, and - with the
optional z3 backend - nonlinear arithmetic) it returns either an exact
counterexample or a real certificate of faithfulness, closing the "sampling
misses measure-zero bugs" gap fundamentally rather than statistically.
"""

from .symbolic import Var, SymbolicClaim, symbolic_library
from .fourier_motzkin import LinCon, con, solve as fm_solve
from .oracle import (
    SMTOracle, EnumBackend, LinearBackend, Z3Backend, default_backends, BackendResult,
)

__all__ = [
    "Var", "SymbolicClaim", "symbolic_library",
    "LinCon", "con", "fm_solve",
    "SMTOracle", "EnumBackend", "LinearBackend", "Z3Backend",
    "default_backends", "BackendResult",
]

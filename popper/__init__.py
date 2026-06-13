"""Popper — falsify the spec, then verify the proof.

An executable falsification layer for formal claims. AXLE (and any Lean checker)
answers *"is this proof valid?"*; Popper adds the missing half — *"is this
statement faithful and worth proving?"* — with a cheap, independent oracle that
hands back counterexamples.

Two surfaces, one abstraction (:class:`Oracle`):
  * :class:`NumericalOracle`  — Monte-Carlo falsification of math statements.
  * :class:`CodeSpecOracle`   — soundness / completeness / vacuity of code specs,
    over the real AXLE API (:class:`AxleClient`) or an offline :class:`MockAxleClient`.
"""

from .oracle import Oracle, OracleResult, Verdict
from .numerical import NumericalOracle, Statement, information_theory_library
from .codespec import CodeSpecOracle
from .axle import AxleClient, MockAxleClient, Task, SpecCheckResult
from .audit import AuditReport, run_audit
from .fixtures import verina_like_tasks

__version__ = "0.1.0"

__all__ = [
    "Oracle", "OracleResult", "Verdict",
    "NumericalOracle", "Statement", "information_theory_library",
    "CodeSpecOracle",
    "AxleClient", "MockAxleClient", "Task", "SpecCheckResult",
    "AuditReport", "run_audit",
    "verina_like_tasks",
]

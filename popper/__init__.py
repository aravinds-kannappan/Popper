"""Popper — falsify the spec, then verify the proof.

An executable falsification layer for formal claims. AXLE (and any Lean checker)
answers *"is this proof valid?"*; Popper adds the missing half — *"is this
statement faithful and worth proving?"* — with a cheap, independent oracle that
hands back counterexamples, and an M2 loop that *repairs* the statement.

Surfaces, one abstraction (:class:`Oracle`):
  * :class:`NumericalOracle` — Monte-Carlo falsification of math statements.
  * :class:`CodeSpecOracle`  — soundness/completeness/vacuity of code specs (offline model).
  * :mod:`popper.verina`     — live spec-faithfulness audit of the real Verina benchmark over AXLE.
  * :mod:`popper.repair`     — counterexample-guided spec repair (M2).
"""

from .oracle import Oracle, OracleResult, Verdict
from .numerical import NumericalOracle, Statement, information_theory_library
from .codespec import CodeSpecOracle
from .axle import AxleClient, MockAxleClient, Task, SpecCheckResult
from .audit import AuditReport, run_audit
from .fixtures import verina_like_tasks
from .verina import VerinaTask, list_task_ids, load_task, run_live_audit
from .repair import (
    RepairTrace, Repairer, TemplateRepairer, FunctionalSpecRepairer,
    ChainRepairer, default_repairer, repair_loop, LLMRepairer,
)

__version__ = "0.2.0"

__all__ = [
    "Oracle", "OracleResult", "Verdict",
    "NumericalOracle", "Statement", "information_theory_library",
    "CodeSpecOracle",
    "AxleClient", "MockAxleClient", "Task", "SpecCheckResult",
    "AuditReport", "run_audit",
    "verina_like_tasks",
    "VerinaTask", "list_task_ids", "load_task", "run_live_audit",
    "RepairTrace", "Repairer", "TemplateRepairer", "FunctionalSpecRepairer",
    "ChainRepairer", "default_repairer", "repair_loop", "LLMRepairer",
]

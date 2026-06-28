"""falsify - the implementation package behind the **Popper** project.

Popper is the system: *falsify the spec, then verify the proof.* A Lean checker
(and Axiom's AXLE) answers "is this proof valid?"; Popper adds the missing half -
"is this statement faithful and worth proving?" - with a cheap, independent
oracle that returns counterexamples, and a loop that repairs the statement.

Code is organized by component (see folder → role):
  * ``core``       - the shared spine: Verdict, Oracle, audit/report.
  * ``montecarlo`` - numerical falsification of math statements.
  * ``speccheck``  - offline code-spec oracle (soundness/completeness/vacuity).
  * ``live``       - live spec-faithfulness audit of real Verina over AXLE.
  * ``repair``     - counterexample-guided spec repair.
"""

from .core.oracle import Oracle, OracleResult, Verdict
from .core.audit import AuditReport, run_audit
from .montecarlo.numerical import NumericalOracle, Statement, information_theory_library
from .speccheck.task import Task, SpecCheckResult, MockAxleClient
from .speccheck.codespec import CodeSpecOracle
from .speccheck.fixtures import verina_like_tasks
from .live.axle import AxleClient
from .live.verina import VerinaTask, list_task_ids, load_task, run_live_audit
from .repair.repair import (
    RepairTrace, Repairer, TemplateRepairer, FunctionalSpecRepairer,
    ChainRepairer, default_repairer, repair_loop, LLMRepairer,
)
from .scale import (
    ScoredClaim, SearchResult, UniformFalsifier, AdaptiveFalsifier,
    AdaptiveOracle, sleeper_claims,
    RewardHackReport, hacker_candidates, probe_reward_hacks,
    FaithfulnessScore, score_task, SAFE_THRESHOLD,
    DebateTranscript, run_debate,
    JudgeCalibration, calibrate_judge, ensemble_verdict,
    EvalCard, GateDecision, build_eval_card,
    BugRateBound, bug_rate_upper_bound, weighted_bug_rate_bound, certify_result,
    AdaptiveHackPolicy, WitnessMemory, TriggerStructure, family_of, FAMILIES,
    probe_reward_hacks_learned, naive_evaluations, conjunctive_trigger_search,
)
from .smt import (
    Var, SymbolicClaim, symbolic_library, LinCon, con, fm_solve,
    SMTOracle, EnumBackend, LinearBackend, Z3Backend, default_backends,
)
from .speccheck.typegen import (
    TInt, TNat, TBool, TList, TTuple, gen, enumerate_small,
    parse_signature, gen_inputs_for, small_inputs_for, GeneratedInputs,
)

__version__ = "0.5.0"

__all__ = [
    "Oracle", "OracleResult", "Verdict",
    "AuditReport", "run_audit",
    "NumericalOracle", "Statement", "information_theory_library",
    "Task", "SpecCheckResult", "MockAxleClient",
    "CodeSpecOracle", "verina_like_tasks",
    "AxleClient", "VerinaTask", "list_task_ids", "load_task", "run_live_audit",
    "RepairTrace", "Repairer", "TemplateRepairer", "FunctionalSpecRepairer",
    "ChainRepairer", "default_repairer", "repair_loop", "LLMRepairer",
    # falsify.scale - AI-safety / RLHF principles ported to spec faithfulness
    "ScoredClaim", "SearchResult", "UniformFalsifier", "AdaptiveFalsifier",
    "AdaptiveOracle", "sleeper_claims",
    "RewardHackReport", "hacker_candidates", "probe_reward_hacks",
    "FaithfulnessScore", "score_task", "SAFE_THRESHOLD",
    "DebateTranscript", "run_debate",
    "JudgeCalibration", "calibrate_judge", "ensemble_verdict",
    "EvalCard", "GateDecision", "build_eval_card",
    "BugRateBound", "bug_rate_upper_bound", "weighted_bug_rate_bound", "certify_result",
    "AdaptiveHackPolicy", "WitnessMemory", "TriggerStructure", "family_of", "FAMILIES",
    "probe_reward_hacks_learned", "naive_evaluations", "conjunctive_trigger_search",
    # falsify.smt - exact falsification (M4 idea 1)
    "Var", "SymbolicClaim", "symbolic_library", "LinCon", "con", "fm_solve",
    "SMTOracle", "EnumBackend", "LinearBackend", "Z3Backend", "default_backends",
    # falsify.speccheck.typegen - type-directed generation (M4 idea 2)
    "TInt", "TNat", "TBool", "TList", "TTuple", "gen", "enumerate_small",
    "parse_signature", "gen_inputs_for", "small_inputs_for", "GeneratedInputs",
]

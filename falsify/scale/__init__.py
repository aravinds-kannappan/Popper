"""falsify.scale - scaling Popper with AI-safety / RLHF research principles.

Popper's whole job is *spec faithfulness*: deciding whether a formal statement
says what its author meant, before any expensive proof compute is spent. That is
the same object the alignment literature studies under a different name. A reward
model is a spec for "good behaviour"; a too-weak reward is a spec that accepts
wrong answers; a model that games it is a wrong implementation the spec failed to
reject. So the techniques that scale reward modelling and oversight are exactly
the techniques that scale a faithfulness oracle. This package ports six of them.

  * ``importance``  - adaptive, trigger-aware search (Sleeper Agents: rare
    triggers). Cross-Entropy-Method falsification that finds measure-zero spec
    bugs with one to two orders of magnitude fewer draws than uniform sampling.
  * ``rewardhack``  - active reward-hack synthesis (Natural Emergent
    Misalignment from Reward Hacking). Searches a family of cheap adversarial
    implementations for one the spec accepts but that disagrees with intent.
  * ``constrained`` - Safe-RLHF faithfulness score. Decouples a *reward* (accept
    correct answers) from a *cost* (accept wrong answers) and combines them with
    a Lagrangian, turning a discrete verdict into a tunable RL reward.
  * ``debate``      - doubly-efficient debate (Scalable AI Safety via Debate). A
    cheap verifier adjudicates an adversarial Falsifier vs Defender to recover
    the missing premise of a broken statement.
  * ``calibration`` - Bridge-style LLM-judge calibration. Anchors a guessing
    LLM judge to the executable oracle's ground truth and measures the gap.
  * ``evalcard``    - Model-Eval-for-extreme-risks gate. Aggregates the above
    into a graded risk card and a PROVE / REPAIR / REJECT decision.
"""

from .importance import (
    ScoredClaim, SearchResult, UniformFalsifier, AdaptiveFalsifier,
    AdaptiveOracle, sleeper_claims,
)
from .rewardhack import RewardHackReport, hacker_candidates, probe_reward_hacks
from .constrained import FaithfulnessScore, score_task, SAFE_THRESHOLD
from .debate import DebateTranscript, run_debate
from .calibration import JudgeCalibration, calibrate_judge, ensemble_verdict
from .evalcard import EvalCard, GateDecision, build_eval_card
from .certify import (
    BugRateBound, bug_rate_upper_bound, weighted_bug_rate_bound, certify_result,
)
from .adversary import (
    AdaptiveHackPolicy, WitnessMemory, TriggerStructure, family_of, FAMILIES,
    probe_reward_hacks_learned, naive_evaluations, conjunctive_trigger_search,
)

__all__ = [
    "ScoredClaim", "SearchResult", "UniformFalsifier", "AdaptiveFalsifier",
    "AdaptiveOracle", "sleeper_claims",
    "RewardHackReport", "hacker_candidates", "probe_reward_hacks",
    "FaithfulnessScore", "score_task", "SAFE_THRESHOLD",
    "DebateTranscript", "run_debate",
    "JudgeCalibration", "calibrate_judge", "ensemble_verdict",
    "EvalCard", "GateDecision", "build_eval_card",
    # M4 idea 1b: statistical certificate
    "BugRateBound", "bug_rate_upper_bound", "weighted_bug_rate_bound", "certify_result",
    # M4 idea 3: a trained adversary
    "AdaptiveHackPolicy", "WitnessMemory", "TriggerStructure", "family_of", "FAMILIES",
    "probe_reward_hacks_learned", "naive_evaluations", "conjunctive_trigger_search",
]

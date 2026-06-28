"""Anchor a guessing LLM judge to the executable oracle's ground truth.

*Bridging Human and LLM Judgments* (Maia Polo et al. 2025) shows that LLM-as-a-
judge ratings diverge from the ground-truth signal in *systematic*, measurable
ways (length bias, over-generous flagging, order effects), and that you can fit
those deviations and correct for them rather than trusting the judge raw. Popper
already ships the relevant ground truth: its executable oracle returns a verdict
*with a witness*, so when it flags a spec it is not guessing. The README's own
benchmark contrasts the two - Popper at F1 0.99 with a counterexample every time,
the LLM judge "guesses, no execution".

This module makes that contrast quantitative and, more usefully, *combines* the
two. ``calibrate_judge`` treats the oracle's verdict as the anchor and measures
how the judge deviates from it: agreement, a confusion matrix, Cohen's kappa, the
judge's systematic flag-rate bias, and a Brier score when the judge reports a
confidence. ``ensemble_verdict`` is the Bridge correction applied online: when the
oracle hands back an executable counterexample, trust the oracle (it cannot be
wrong about a witness it can run); only fall back to the judge's guess where the
oracle is silent, and down-weight it by the bias we measured. The judge stays
useful for the semantic cases the oracle cannot reach, without being trusted
where it is known to drift.

Runs fully offline. ``synthetic_judge`` fabricates a judge with a *declared*
bias so the calibration math can be exercised and tested without an API key; it
is clearly labelled synthetic and is not a stand-in for a real model.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from ..core.oracle import OracleResult, Verdict


def _flagged(v: Verdict) -> bool:
    """Binarize a verdict to the positive ('unfaithful') class, as the benchmark does."""
    return v.is_falsified


@dataclass
class JudgeCalibration:
    judge: str = "llm"
    n: int = 0
    agree: int = 0
    tp: int = 0   # both flag
    fp: int = 0   # judge flags, oracle does not
    fn: int = 0   # oracle flags, judge does not
    tn: int = 0   # neither flags
    brier_sum: float = 0.0
    brier_n: int = 0

    @property
    def accuracy(self) -> float:
        return self.agree / self.n if self.n else 0.0

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    @property
    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    @property
    def flag_bias(self) -> float:
        """Judge flag-rate minus oracle flag-rate. >0 = over-flags, <0 = under-flags."""
        if not self.n:
            return 0.0
        judge_rate = (self.tp + self.fp) / self.n
        oracle_rate = (self.tp + self.fn) / self.n
        return judge_rate - oracle_rate

    @property
    def kappa(self) -> float:
        """Cohen's kappa between judge and oracle on the flag/no-flag decision."""
        n = self.n
        if not n:
            return 0.0
        po = (self.tp + self.tn) / n
        p_yes = ((self.tp + self.fp) / n) * ((self.tp + self.fn) / n)
        p_no = ((self.fn + self.tn) / n) * ((self.fp + self.tn) / n)
        pe = p_yes + p_no
        return (po - pe) / (1 - pe) if (1 - pe) > 1e-12 else 1.0

    @property
    def brier(self) -> Optional[float]:
        """Mean squared error of the judge's confidence vs the oracle outcome."""
        return self.brier_sum / self.brier_n if self.brier_n else None

    def as_dict(self) -> dict:
        d = {
            "judge": self.judge, "n": self.n,
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "flag_bias": round(self.flag_bias, 4),
            "kappa": round(self.kappa, 4),
            "confusion": {"tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn},
        }
        if self.brier is not None:
            d["brier"] = round(self.brier, 4)
        return d

    def one_line(self) -> str:
        bias = ("over-flags" if self.flag_bias > 0.02 else
                "under-flags" if self.flag_bias < -0.02 else "well-matched")
        return (f"{self.judge}: acc={self.accuracy:.2f} kappa={self.kappa:.2f} "
                f"flag_bias={self.flag_bias:+.2f} ({bias}) vs the executable oracle")


def calibrate_judge(pairs: list[tuple[OracleResult, OracleResult]],
                    judge_name: str = "llm") -> JudgeCalibration:
    """Measure how a judge deviates from the executable oracle.

    ``pairs`` is a list of ``(oracle_result, judge_result)`` over the same items.
    The oracle's verdict is the anchor (ground truth); the judge is scored
    against it. A confidence in ``judge_result.details['confidence']`` feeds the
    Brier score.
    """
    cal = JudgeCalibration(judge=judge_name, n=len(pairs))
    for oracle_r, judge_r in pairs:
        o = _flagged(oracle_r.verdict)
        j = _flagged(judge_r.verdict)
        cal.agree += int(o == j)
        if o and j:
            cal.tp += 1
        elif j and not o:
            cal.fp += 1
        elif o and not j:
            cal.fn += 1
        else:
            cal.tn += 1
        conf = judge_r.details.get("confidence") if judge_r.details else None
        if isinstance(conf, (int, float)):
            cal.brier_sum += (float(conf) - (1.0 if o else 0.0)) ** 2
            cal.brier_n += 1
    return cal


def ensemble_verdict(oracle_r: OracleResult, judge_r: Optional[OracleResult],
                     cal: Optional[JudgeCalibration] = None) -> OracleResult:
    """Combine an oracle result and a judge guess, Bridge-style.

    Rule: an executable counterexample is incontrovertible, so when the oracle
    returns one, it wins outright. Where the oracle is silent (FAITHFUL or
    INCONCLUSIVE and no witness), defer to the judge only if its measured bias
    does not undercut the call - an over-flagging judge's lone flag is treated as
    INCONCLUSIVE rather than accepted.
    """
    if oracle_r.counterexample and oracle_r.verdict.is_falsified:
        return _tag(oracle_r, "oracle-witness")

    if judge_r is None:
        return _tag(oracle_r, "oracle-only")

    if oracle_r.verdict.is_falsified and not oracle_r.counterexample:
        # oracle flagged without a witness (e.g. replayed); a concurring judge strengthens it
        if _flagged(judge_r.verdict):
            return _tag(oracle_r, "oracle+judge-concur")
        return _tag(oracle_r, "oracle-only")

    # oracle is silent: consider the judge, discounted by its bias
    if _flagged(judge_r.verdict):
        bias = cal.flag_bias if cal else 0.0
        if bias > 0.05:
            r = OracleResult(name=oracle_r.name, verdict=Verdict.INCONCLUSIVE,
                             reason="judge flags but it is a known over-flagger; needs a witness",
                             counterexample=None, trials=oracle_r.trials)
            return _tag(r, "judge-discounted")
        r = OracleResult(name=oracle_r.name, verdict=judge_r.verdict,
                         reason=f"oracle silent; judge flags ({judge_r.reason})",
                         counterexample=None, trials=oracle_r.trials)
        return _tag(r, "judge-fallback")

    return _tag(oracle_r, "both-clear")


def _tag(r: OracleResult, source: str) -> OracleResult:
    det = dict(r.details or {})
    det["ensemble_source"] = source
    return OracleResult(name=r.name, verdict=r.verdict, reason=r.reason,
                        counterexample=r.counterexample, trials=r.trials, details=det)


# --------------------------------------------------------------------------- #
# A synthetic, declared-bias judge so the calibration math is testable offline.
# --------------------------------------------------------------------------- #
def synthetic_judge(oracle_r: OracleResult, *, over_flag: float = 0.18,
                    miss: float = 0.15, seed: int = 0) -> OracleResult:
    """Fabricate a judge result with a known bias. SYNTHETIC - not a real model.

    Mimics the documented LLM-judge failure modes: it sometimes flags faithful
    specs (over_flag) and sometimes misses true bugs (miss), and it never
    produces a witness. Useful only to exercise/test :func:`calibrate_judge`.
    """
    rng = random.Random(hash((oracle_r.name, seed)) & 0xFFFFFFFF)
    truly_flagged = oracle_r.verdict.is_falsified
    if truly_flagged:
        verdict = Verdict.FAITHFUL if rng.random() < miss else Verdict.FALSIFIED
    else:
        verdict = Verdict.FALSIFIED if rng.random() < over_flag else Verdict.FAITHFUL
    conf = 0.5 + 0.4 * rng.random()
    return OracleResult(name=oracle_r.name, verdict=verdict,
                        reason="synthetic judge guess (no execution)", counterexample=None,
                        details={"judge": "synthetic", "confidence": round(conf, 3)})

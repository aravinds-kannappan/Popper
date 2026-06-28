"""Turn "survived N draws" into a quantified bug-rate certificate.

A sampling oracle's FAITHFUL verdict is honest but soft: "no counterexample in N
draws" is not "no counterexample exists". The exact SMT engine closes that gap
for the decidable fragment; for everything else (nonlinear shadows, black-box
specs) we can still upgrade the soft verdict into a statistical one, the way a
reliability test reports a confidence bound rather than a bare pass.

If a claim survives ``n`` independent uniform draws with ``failures`` observed
counterexamples, the Clopper-Pearson upper confidence bound gives the largest
bug rate ``eps`` consistent with that outcome at confidence ``1 - delta``: it is
the ``p`` for which the probability of seeing at most ``failures`` hits in ``n``
draws is exactly ``delta``. With zero failures this collapses to the rule of
three, ``eps = 1 - delta**(1/n)`` (about ``-ln(delta)/n``), so 3,000 clean draws
certify, at 95% confidence, a bug rate under about one in a thousand.

Adaptive (importance) search breaks the independence/uniformity assumption, so a
plain binomial bound does not apply to it; :func:`weighted_bug_rate_bound` gives
the corresponding Hoeffding bound for a uniform sweep whose per-draw indicator is
reweighted, with the bounded-weight assumption stated explicitly. Pure stdlib.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from ..core.oracle import OracleResult, Verdict


@dataclass
class BugRateBound:
    n: int
    failures: int
    delta: float
    eps: float                 # upper bound on the true bug rate at confidence 1 - delta
    method: str = "clopper-pearson"

    @property
    def confidence(self) -> float:
        return 1.0 - self.delta

    def as_dict(self) -> dict:
        return {"n": self.n, "failures": self.failures, "delta": self.delta,
                "confidence": round(self.confidence, 4), "bug_rate_upper": round(self.eps, 6),
                "method": self.method}

    def one_line(self) -> str:
        return (f"with {self.confidence:.0%} confidence, bug rate <= {self.eps:.2g} "
                f"({self.failures} hits in {self.n} draws, {self.method})")


def _binom_cdf_le(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p), computed in log space for stability."""
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if k >= n else 0.0
    lp, lq = math.log(p), math.log1p(-p)
    total = 0.0
    for i in range(0, k + 1):
        log_c = (math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1))
        total += math.exp(log_c + i * lp + (n - i) * lq)
    return min(1.0, total)


def bug_rate_upper_bound(n: int, failures: int = 0, delta: float = 0.05) -> BugRateBound:
    """Clopper-Pearson upper confidence bound on the bug rate.

    Returns the largest ``p`` with ``P(X <= failures; n, p) >= delta``; for
    ``failures == 0`` this is the exact rule-of-three bound.
    """
    if n <= 0:
        return BugRateBound(n=0, failures=failures, delta=delta, eps=1.0)
    if failures >= n:
        return BugRateBound(n=n, failures=failures, delta=delta, eps=1.0)
    if failures == 0:
        eps = 1.0 - delta ** (1.0 / n)
        return BugRateBound(n=n, failures=0, delta=delta, eps=eps)
    # bisection: find p where the lower-tail CDF crosses delta (CDF decreasing in p)
    lo, hi = failures / n, 1.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if _binom_cdf_le(failures, n, mid) > delta:
            lo = mid
        else:
            hi = mid
    return BugRateBound(n=n, failures=failures, delta=delta, eps=0.5 * (lo + hi))


def weighted_bug_rate_bound(n: int, weight_cap: float = 1.0, delta: float = 0.05,
                            failures: int = 0) -> BugRateBound:
    """Hoeffding bound for a reweighted uniform sweep (bounded weights in [0, cap]).

    Assumes each draw contributes an importance-weighted indicator in
    ``[0, weight_cap]``; with zero observed hits the bound is
    ``weight_cap * sqrt(ln(1/delta) / (2n))``. Stated assumption: weights are
    bounded by ``weight_cap`` and the sweep is otherwise uniform.
    """
    if n <= 0:
        return BugRateBound(n=0, failures=failures, delta=delta, eps=1.0, method="hoeffding")
    emp = failures / n
    eps = min(1.0, emp + weight_cap * math.sqrt(math.log(1.0 / delta) / (2.0 * n)))
    return BugRateBound(n=n, failures=failures, delta=delta, eps=eps, method="hoeffding")


def certify_result(result: OracleResult, delta: float = 0.05) -> Optional[BugRateBound]:
    """Attach a bug-rate bound to a sampling oracle's FAITHFUL verdict.

    Reads the draw count from ``result.trials``. Returns ``None`` for verdicts
    that are not a budget-limited "survived" (a FALSIFIED result already has a
    witness; an exact SMT certificate needs no statistical bound).
    """
    if result.verdict is not Verdict.FAITHFUL:
        return None
    if result.details.get("certificate"):     # already an exact certificate
        return None
    n = int(result.trials or 0)
    return bug_rate_upper_bound(n, failures=0, delta=delta)

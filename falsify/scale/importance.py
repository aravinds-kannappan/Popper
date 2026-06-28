"""Adaptive, trigger-aware falsification search.

Popper's honest limitation, documented in the README, is that uniform
Monte-Carlo can miss a bug that hides on a tiny fraction of inputs (the 2 of 178
specs it misses; the "subtle bug" recall that only reaches 100% at 10,000 draws).
That failure mode is not a quirk, it is the *Sleeper Agents* result (Hubinger et
al. 2024) restated for specs. A backdoor that fires only when the prompt says the
year is 2024 survives safety training because uniform sampling almost never lands
on the trigger. A faithfulness bug that fires on 1 input in 10,000 is the same
object: a sleeper in the statement. Uniform search needs about 1/p draws to see a
trigger of probability p, so the rarer the bug the more compute Popper burns, and
the README's recall table is exactly that 1 - (1 - p)^N curve.

The fix is to stop sampling uniformly. Falsification is an optimization problem:
drive the claim's *margin* (how comfortably the conclusion holds) below zero. The
Cross-Entropy Method (Rubinstein 1997) turns that into importance sampling that
steers draws toward the low-margin boundary where a counterexample, if one
exists, must live. On the same rare-edge claims it finds the trigger with one to
two orders of magnitude fewer draws than uniform, which is the concrete way to
scale the oracle's recall without scaling its budget.

A :class:`ScoredClaim` is the smooth analogue of a montecarlo ``Statement``: it
exposes a real-valued ``margin`` instead of a boolean ``claim``, and a
deterministic ``build`` from a latent point ``u`` in the unit cube so a search can
*move* through input space rather than only sample it.

Pure standard library: no numpy.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from ..core.oracle import Oracle, OracleResult, Verdict

EPS = 1e-9
Instance = dict


@dataclass
class ScoredClaim:
    """A claim whose conclusion has a continuous margin over the unit cube.

    The claim is satisfied on an instance iff ``margin(inst) >= 0``. ``build``
    maps a latent point ``u`` in ``[0, 1]^dim`` to an instance, so a search can
    deterministically reach any input by choosing ``u``.
    """

    name: str
    description: str
    dim: int
    build: Callable[[Sequence[float]], Instance]
    margin: Callable[[Instance], float]
    summarize: Optional[Callable[[Instance], str]] = None
    expected: Optional[Verdict] = None
    tags: tuple = ()

    def margin_at(self, u: Sequence[float]) -> tuple[float, Instance]:
        inst = self.build(u)
        return self.margin(inst), inst

    def render_ce(self, inst: Instance) -> str:
        if self.summarize is not None:
            return self.summarize(inst)
        return repr(inst)


@dataclass
class SearchResult:
    found: bool
    draws_used: int
    best_margin: float
    witness: Optional[Instance] = None
    iterations: int = 0
    history: list[float] = field(default_factory=list)  # best margin per iteration


def _clamp01(x: float) -> float:
    return min(1.0 - 1e-6, max(1e-6, x))


# --------------------------------------------------------------------------- #
# Falsifiers
# --------------------------------------------------------------------------- #
class UniformFalsifier:
    """The baseline: draw the latent point uniformly, exactly like Monte-Carlo."""

    name = "uniform"

    def __init__(self, budget: int = 2000, seed: int = 0):
        self.budget = budget
        self.seed = seed

    def search(self, claim: ScoredClaim) -> SearchResult:
        rng = random.Random(self.seed)
        best = math.inf
        best_inst: Optional[Instance] = None
        for i in range(self.budget):
            u = [rng.random() for _ in range(claim.dim)]
            m, inst = claim.margin_at(u)
            if m < best:
                best, best_inst = m, inst
            if m < -EPS:
                return SearchResult(True, i + 1, m, inst, iterations=i + 1)
        return SearchResult(False, self.budget, best, best_inst)


class AdaptiveFalsifier:
    """Cross-Entropy-Method falsification: importance-sample toward low margin.

    Keeps a per-coordinate Gaussian proposal over the unit cube. Each round it
    draws a batch, keeps the ``elite_frac`` with the smallest margin, and refits
    the proposal toward those elites (with smoothing, and a variance floor so the
    search never fully collapses and can still find a second, disjoint trigger).
    The moment any draw goes negative it returns that draw as the witness.
    """

    name = "adaptive-cem"

    def __init__(self, budget: int = 2000, batch: int = 64, elite_frac: float = 0.2,
                 smooth: float = 0.7, std_floor: float = 0.03, seed: int = 0):
        self.budget = budget
        self.batch = batch
        self.elite_frac = elite_frac
        self.smooth = smooth
        self.std_floor = std_floor
        self.seed = seed

    def search(self, claim: ScoredClaim) -> SearchResult:
        rng = random.Random(self.seed)
        d = claim.dim
        mean = [0.5] * d
        std = [0.3] * d
        best = math.inf
        best_inst: Optional[Instance] = None
        history: list[float] = []
        used = 0
        n_elite = max(2, int(self.batch * self.elite_frac))
        iters = 0

        while used < self.budget:
            iters += 1
            samples: list[tuple[float, list[float], Instance]] = []
            for _ in range(min(self.batch, self.budget - used)):
                u = [_clamp01(rng.gauss(mean[j], std[j])) for j in range(d)]
                m, inst = claim.margin_at(u)
                used += 1
                if m < best:
                    best, best_inst = m, inst
                if m < -EPS:
                    history.append(best)
                    return SearchResult(True, used, m, inst, iterations=iters, history=history)
                samples.append((m, u, inst))

            history.append(best)
            samples.sort(key=lambda t: t[0])
            elite = [u for _, u, _ in samples[:n_elite]]
            for j in range(d):
                col = [u[j] for u in elite]
                em = sum(col) / len(col)
                ev = sum((c - em) ** 2 for c in col) / len(col)
                mean[j] = self.smooth * em + (1 - self.smooth) * mean[j]
                std[j] = max(self.std_floor,
                             self.smooth * math.sqrt(ev) + (1 - self.smooth) * std[j])

        return SearchResult(False, used, best, best_inst, iterations=iters, history=history)


# --------------------------------------------------------------------------- #
# An Oracle wrapper so adaptive search plugs into the existing audit machinery
# --------------------------------------------------------------------------- #
class AdaptiveOracle(Oracle):
    """Drop-in oracle over :class:`ScoredClaim` that searches instead of samples."""

    name = "adaptive"

    def __init__(self, budget: int = 2000, seed: int = 0, falsifier=None):
        self.falsifier = falsifier or AdaptiveFalsifier(budget=budget, seed=seed)

    def audit(self, claim: ScoredClaim) -> OracleResult:  # type: ignore[override]
        res = self.falsifier.search(claim)
        if res.found:
            return OracleResult(
                name=claim.name, verdict=Verdict.FALSIFIED,
                reason="adaptive search drove the margin below zero",
                counterexample=claim.render_ce(res.witness) if res.witness else None,
                trials=res.draws_used,
                details={"best_margin": round(res.best_margin, 6),
                         "iterations": res.iterations, "strategy": self.falsifier.name},
            )
        return OracleResult(
            name=claim.name, verdict=Verdict.FAITHFUL,
            reason=f"survived {res.draws_used} adaptive draws (best margin {res.best_margin:.4g})",
            trials=res.draws_used,
            details={"best_margin": round(res.best_margin, 6), "strategy": self.falsifier.name},
        )


# --------------------------------------------------------------------------- #
# A library of "sleeper" claims: bugs that hide on a rare trigger region.
# --------------------------------------------------------------------------- #
def sleeper_claims(rare_ps: Sequence[float] = (0.05, 0.01, 0.002, 0.0005, 0.0001),
                   needle_dims: Sequence[int] = (3, 5)) -> list[ScoredClaim]:
    """Faithfulness bugs whose trigger has small measure, plus faithful twins.

    * ``rare_edge_p`` - a postcondition that fails only when a scalar score falls
      below ``p`` (trigger probability exactly ``p``). The 1-D sleeper.
    * ``needle_dim``  - a conjunctive trigger: the spec breaks only when *all*
      ``dim`` coordinates fall in a small corner (trigger volume ``t^dim``). The
      multi-dimensional sleeper where uniform search is hopeless but a steered
      search descends the margin coordinate by coordinate.
    * faithful twins that hold on every input, so the family also measures false
      alarms under adaptive search.
    """
    claims: list[ScoredClaim] = []

    for p in rare_ps:
        claims.append(ScoredClaim(
            name=f"rare_edge_p{p:g}",
            description=f"postcondition that fails on a {p:g} fraction of inputs",
            dim=1,
            build=lambda u: {"u": u[0]},
            margin=lambda inst, p=p: inst["u"] - p,
            summarize=lambda inst, p=p: f"input scored {inst['u']:.6f} <= {p:g}; the spec rejects it",
            expected=Verdict.FALSIFIED,
            tags=("rare-edge",),
        ))

    for dim in needle_dims:
        t = 0.2  # corner side; trigger volume t^dim
        claims.append(ScoredClaim(
            name=f"needle_dim{dim}",
            description=f"conjunctive trigger: spec breaks only when all {dim} coords < {t}",
            dim=dim,
            build=lambda u: {"u": list(u)},
            margin=lambda inst, t=t: max(inst["u"]) - t,
            summarize=lambda inst, t=t: (
                f"all {len(inst['u'])} coords in the corner "
                f"(max={max(inst['u']):.4f} < {t}); volume {t**len(inst['u']):.2g}"),
            expected=Verdict.FALSIFIED,
            tags=("needle",),
        ))

    claims.append(ScoredClaim(
        name="rare_edge_faithful",
        description="a postcondition that holds on every input",
        dim=1,
        build=lambda u: {"u": u[0]},
        margin=lambda inst: inst["u"],  # u in [0,1], never negative
        expected=Verdict.FAITHFUL,
        tags=("faithful",),
    ))
    return claims

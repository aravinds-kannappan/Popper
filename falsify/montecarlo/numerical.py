"""The numerical (math) falsification oracle.

Every theorem in analysis / probability / information theory has a *numerical
shadow*: an inequality can be Monte-Carlo checked on sampled distributions, an
identity can be checked by simulating the relevant process. If the formalized
statement dropped a hypothesis (normalization, a Markov-chain assumption,
integrability) or flipped a direction, the shadow breaks on some sample - and
we get a counterexample *for free*, before spending any proof compute.

A `Statement` carries:
  * ``claim(inst) -> bool``       : the conclusion C, evaluated numerically
  * ``hypothesis(inst) -> bool``  : the hypothesis H (optional)

and the *formalized predicate* the oracle actually tests is ``H → C`` (i.e.
``(not H) or C``). To model an **unfaithful** formalization that dropped a
hypothesis, you simply build the statement with ``hypothesis=None`` and a
sampler that ranges over the unrestricted space - then C fails on some draw and
the oracle falsifies it. To model a **vacuous** statement, give it a hypothesis
that is (almost) never satisfiable; the oracle reports INCONCLUSIVE because the
conclusion was never actually exercised.

Pure standard library: no numpy required.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..core.oracle import Oracle, OracleResult, Verdict

EPS = 1e-9
Instance = dict


# --------------------------------------------------------------------------- #
# small probability / information-theory helpers (stdlib only)
# --------------------------------------------------------------------------- #
def random_prob_vector(k: int, rng: random.Random) -> list[float]:
    v = [rng.random() + 1e-6 for _ in range(k)]
    s = sum(v)
    return [x / s for x in v]


def random_nonneg_vector(k: int, rng: random.Random, hi: float = 3.0) -> list[float]:
    """A non-normalized non-negative vector (NOT a probability distribution)."""
    return [rng.random() * hi + 1e-6 for _ in range(k)]


def entropy(p: list[float]) -> float:
    return -sum(pi * math.log(pi) for pi in p if pi > 0)


def kl_divergence(p: list[float], q: list[float]) -> float:
    return sum(pi * math.log(pi / qi) for pi, qi in zip(p, q) if pi > 0)


def _mi_from_pairs(pairs: dict) -> float:
    """Mutual information of a 2-D joint given as {(a, b): prob}."""
    pa: dict = {}
    pb: dict = {}
    for (a, b), p in pairs.items():
        pa[a] = pa.get(a, 0.0) + p
        pb[b] = pb.get(b, 0.0) + p
    mi = 0.0
    for (a, b), p in pairs.items():
        if p > 0:
            mi += p * math.log(p / (pa[a] * pb[b]))
    return mi


def _marginalize(joint: dict, keep: tuple) -> dict:
    """Marginalize a 3-D joint {(x, y, z): p} down to the axes in ``keep``."""
    out: dict = {}
    for (x, y, z), p in joint.items():
        key = tuple(v for v, axis in zip((x, y, z), ("x", "y", "z")) if axis in keep)
        out[key] = out.get(key, 0.0) + p
    return out


# --------------------------------------------------------------------------- #
# Statement model
# --------------------------------------------------------------------------- #
@dataclass
class Statement:
    name: str
    description: str
    lean: str                                   # the formal statement (for repair / display)
    sample: Callable[[random.Random], Instance]
    claim: Callable[[Instance], bool]           # conclusion C
    hypothesis: Optional[Callable[[Instance], bool]] = None  # H; predicate tested is H → C
    summarize: Optional[Callable[[Instance], str]] = None    # render a counterexample
    expected: Optional[Verdict] = None          # ground-truth label, for tests/leaderboard only
    tags: tuple = ()

    def render_ce(self, inst: Instance) -> str:
        if self.summarize is not None:
            return self.summarize(inst)
        return repr(inst)


# --------------------------------------------------------------------------- #
# the oracle
# --------------------------------------------------------------------------- #
class NumericalOracle(Oracle):
    name = "numerical"

    def __init__(self, n_trials: int = 2000, seed: int = 0, min_hypothesis_hits: int = 1):
        self.n_trials = n_trials
        self.seed = seed
        self.min_hypothesis_hits = min_hypothesis_hits

    def audit(self, stmt: Statement) -> OracleResult:  # type: ignore[override]
        rng = random.Random(self.seed)
        hyp_hits = 0
        for i in range(self.n_trials):
            inst = stmt.sample(rng)
            holds = True if stmt.hypothesis is None else bool(stmt.hypothesis(inst))
            if not holds:
                continue
            hyp_hits += 1
            if not stmt.claim(inst):
                return OracleResult(
                    name=stmt.name,
                    verdict=Verdict.FALSIFIED,
                    reason="counterexample found; the formalized statement is false as written",
                    counterexample=stmt.render_ce(inst),
                    trials=i + 1,
                    details={"hypothesis_hits": hyp_hits},
                )
        if hyp_hits < self.min_hypothesis_hits:
            return OracleResult(
                name=stmt.name,
                verdict=Verdict.INCONCLUSIVE,
                reason=(
                    f"hypothesis satisfied in {hyp_hits}/{self.n_trials} draws; "
                    "conclusion never exercised (possibly vacuous)"
                ),
                trials=self.n_trials,
                details={"hypothesis_hits": hyp_hits},
            )
        return OracleResult(
            name=stmt.name,
            verdict=Verdict.FAITHFUL,
            reason=f"survived {self.n_trials} Monte-Carlo draws ({hyp_hits} with hypothesis active)",
            trials=self.n_trials,
            details={"hypothesis_hits": hyp_hits},
        )


# --------------------------------------------------------------------------- #
# A curated information-theory ladder: faithful statements paired with the
# unfaithful formalizations Popper is designed to catch.
# --------------------------------------------------------------------------- #
def information_theory_library() -> list[Statement]:
    K = 3  # alphabet size

    # ---- 1. Gibbs / KL >= 0 ------------------------------------------------ #
    def sample_two_distributions(rng):
        return {"p": random_prob_vector(K, rng), "q": random_prob_vector(K, rng)}

    def sample_p_dist_q_unnormalized(rng):
        # The classic dropped hypothesis: q is non-negative but NOT a distribution.
        return {"p": random_prob_vector(K, rng), "q": random_nonneg_vector(K, rng)}

    def kl_claim(inst):
        return kl_divergence(inst["p"], inst["q"]) >= -EPS

    def kl_summary(inst):
        val = kl_divergence(inst["p"], inst["q"])
        return (f"q={[round(x,3) for x in inst['q']]} (Σq={sum(inst['q']):.3f}≠1) ⇒ "
                f"Σ pᵢ·log(pᵢ/qᵢ) = {val:.4f} < 0")

    kl_faithful = Statement(
        name="kl_nonneg",
        description="Gibbs' inequality: KL(p‖q) ≥ 0 for probability distributions p, q.",
        lean="theorem kl_nonneg (p q : Distribution) : 0 ≤ klDiv p q",
        sample=sample_two_distributions,
        claim=kl_claim,
        hypothesis=lambda inst: abs(sum(inst["q"]) - 1.0) < 1e-6,  # q is a distribution
        expected=Verdict.FAITHFUL,
        tags=("information-theory", "gibbs"),
    )
    kl_dropped_norm = Statement(
        name="kl_nonneg_DROPPED_normalization",
        description="Unfaithful: KL ≥ 0 stated for arbitrary non-negative q (forgot Σq = 1).",
        lean="theorem kl_nonneg (p q : ι → ℝ≥0) : 0 ≤ ∑ i, p i * log (p i / q i)",
        sample=sample_p_dist_q_unnormalized,
        claim=kl_claim,
        hypothesis=None,  # the hypothesis was dropped
        summarize=kl_summary,
        expected=Verdict.FALSIFIED,
        tags=("information-theory", "gibbs", "dropped-hypothesis"),
    )

    # ---- 2. Data-processing inequality ------------------------------------- #
    def _stoch(rows, cols, rng):
        return [random_prob_vector(cols, rng) for _ in range(rows)]

    def sample_markov(rng):
        nx = ny = nz = K
        px = random_prob_vector(nx, rng)
        pygx = _stoch(nx, ny, rng)
        pzgy = _stoch(ny, nz, rng)  # Z depends on X ONLY through Y  → Markov chain
        joint = {}
        for x in range(nx):
            for y in range(ny):
                for z in range(nz):
                    joint[(x, y, z)] = px[x] * pygx[x][y] * pzgy[y][z]
        return {"joint": joint}

    def sample_nonmarkov(rng):
        nx = ny = nz = K
        px = random_prob_vector(nx, rng)
        pygx = _stoch(nx, ny, rng)
        joint = {}
        for x in range(nx):
            for y in range(ny):
                # Z leaks X directly (nearly Z = x): this is what the dropped
                # Markov hypothesis would have forbidden.
                pz = [0.05 / (nz - 1)] * nz
                pz[x % nz] = 0.95
                for z in range(nz):
                    joint[(x, y, z)] = px[x] * pygx[x][y] * pz[z]
        return {"joint": joint}

    def dpi_claim(inst):
        xy = _mi_from_pairs(_marginalize(inst["joint"], ("x", "y")))
        xz = _mi_from_pairs(_marginalize(inst["joint"], ("x", "z")))
        return xz <= xy + EPS

    def dpi_summary(inst):
        xy = _mi_from_pairs(_marginalize(inst["joint"], ("x", "y")))
        xz = _mi_from_pairs(_marginalize(inst["joint"], ("x", "z")))
        return f"I(X;Z) = {xz:.4f} > I(X;Y) = {xy:.4f}  (Z leaks X directly)"

    dpi_faithful = Statement(
        name="data_processing",
        description="Data-processing inequality: X→Y→Z Markov ⇒ I(X;Z) ≤ I(X;Y).",
        lean="theorem data_processing (h : MarkovChain X Y Z) : I(X;Z) ≤ I(X;Y)",
        sample=sample_markov,
        claim=dpi_claim,
        hypothesis=None,  # sampler *constructs* the Markov chain, so the claim holds
        expected=Verdict.FAITHFUL,
        tags=("information-theory", "dpi"),
    )
    dpi_dropped_markov = Statement(
        name="data_processing_DROPPED_markov",
        description="Unfaithful: DPI stated without the Markov-chain hypothesis.",
        lean="theorem data_processing (X Y Z) : I(X;Z) ≤ I(X;Y)",
        sample=sample_nonmarkov,
        claim=dpi_claim,
        hypothesis=None,
        summarize=dpi_summary,
        expected=Verdict.FALSIFIED,
        tags=("information-theory", "dpi", "dropped-hypothesis"),
    )

    # ---- 3. Concavity of entropy (direction errors) ------------------------ #
    def sample_mix(rng):
        return {
            "p": random_prob_vector(K, rng),
            "q": random_prob_vector(K, rng),
            "lam": rng.uniform(0.1, 0.9),
        }

    def _mix(inst):
        lam, p, q = inst["lam"], inst["p"], inst["q"]
        return [lam * pi + (1 - lam) * qi for pi, qi in zip(p, q)]

    def concave_claim(inst):  # correct direction: entropy is concave
        lam, p, q = inst["lam"], inst["p"], inst["q"]
        return entropy(_mix(inst)) >= lam * entropy(p) + (1 - lam) * entropy(q) - EPS

    def convex_claim(inst):   # wrong direction
        lam, p, q = inst["lam"], inst["p"], inst["q"]
        return entropy(_mix(inst)) <= lam * entropy(p) + (1 - lam) * entropy(q) + EPS

    def concave_summary(inst):
        lam, p, q = inst["lam"], inst["p"], inst["q"]
        lhs = entropy(_mix(inst))
        rhs = lam * entropy(p) + (1 - lam) * entropy(q)
        return f"H(λp+(1-λ)q) = {lhs:.4f} > λH(p)+(1-λ)H(q) = {rhs:.4f}  (entropy is concave, not convex)"

    entropy_concave = Statement(
        name="entropy_concave",
        description="Concavity of Shannon entropy (Jensen).",
        lean="theorem entropy_concave (p q) (lam) : H(λ•p+(1-λ)•q) ≥ λ•H(p)+(1-λ)•H(q)",
        sample=sample_mix,
        claim=concave_claim,
        hypothesis=None,
        expected=Verdict.FAITHFUL,
        tags=("information-theory", "jensen"),
    )
    entropy_convex_wrong = Statement(
        name="entropy_concave_WRONG_direction",
        description="Unfaithful: entropy mistakenly formalized as convex (≤ instead of ≥).",
        lean="theorem entropy_concave (p q) (lam) : H(λ•p+(1-λ)•q) ≤ λ•H(p)+(1-λ)•H(q)",
        sample=sample_mix,
        claim=convex_claim,
        hypothesis=None,
        summarize=concave_summary,
        expected=Verdict.FALSIFIED,
        tags=("information-theory", "jensen", "direction-error"),
    )

    # ---- 4. A vacuity trap ------------------------------------------------- #
    entropy_uniform_vacuous = Statement(
        name="entropy_uniform_vacuous_guard",
        description="Vacuity trap: true claim guarded by a hypothesis nothing satisfies.",
        lean="theorem h_uniform (p) (h : p = uniform) (h2 : p ≠ uniform) : H(p) = log K",
        sample=sample_two_distributions,
        claim=lambda inst: abs(entropy(inst["p"]) - math.log(K)) < EPS,
        hypothesis=lambda inst: all(abs(pi - 1.0 / K) < 1e-9 for pi in inst["p"]),  # ~never true
        expected=Verdict.INCONCLUSIVE,
        tags=("information-theory", "vacuity"),
    )

    return [
        kl_faithful, kl_dropped_norm,
        dpi_faithful, dpi_dropped_markov,
        entropy_concave, entropy_convex_wrong,
        entropy_uniform_vacuous,
    ]

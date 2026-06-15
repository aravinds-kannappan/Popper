"""The labelled benchmark corpus.

Three surfaces:

  * ``math``   -- inequalities and identities from analysis, probability and
    information theory. Each faithful statement is paired with at least one
    unfaithful formalization (a dropped hypothesis, a flipped direction, an
    over-strong claim). All of these are checked by the Monte-Carlo oracle, which
    runs locally with no API key, so this part of the benchmark is fully
    reproducible offline.
  * ``code``   -- the offline code-spec fixtures (soundness / completeness /
    vacuity), with the oracle's real verdicts.
  * ``verina`` -- the real Verina tasks audited live over AXLE. These are
    presumed faithful (they ship in the benchmark), so they measure the false
    positive rate: how often a judge wrongly flags a good spec.

Every item carries a ``gold`` label so we can score any judge against ground
truth.
"""

from __future__ import annotations

import json
import math
import os
import random
from dataclasses import dataclass, field
from typing import Optional

from ..core.oracle import OracleResult, Verdict
from ..montecarlo.numerical import (
    EPS,
    Statement,
    entropy,
    information_theory_library,
    kl_divergence,
    random_prob_vector,
)

_HERE = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "results")


@dataclass
class Item:
    """One labelled claim in the benchmark."""

    name: str
    surface: str                 # "math" | "code" | "verina"
    intent: str                  # what the statement is supposed to mean
    statement: str               # the formal statement, as written
    gold: Verdict                # ground-truth label
    family: str                  # the kind of bug (or "faithful")
    math: Optional[Statement] = None         # for the math surface: the runnable Statement
    precomputed: Optional[dict] = None        # for code/verina: the oracle's recorded verdict

    @property
    def gold_unfaithful(self) -> bool:
        return self.gold.is_falsified


# --------------------------------------------------------------------------- #
# extra math statements (on top of the curated information-theory ladder)
# --------------------------------------------------------------------------- #
def _vec(rng: random.Random, k: int, lo: float, hi: float) -> list[float]:
    return [rng.uniform(lo, hi) for _ in range(k)]


def _pos_vec(rng: random.Random, k: int, hi: float = 3.0) -> list[float]:
    return [rng.uniform(1e-3, hi) for _ in range(k)]


def _joint_kk(rng: random.Random, k: int) -> dict:
    """A random joint distribution over a k x k alphabet, as {(x, y): p}."""
    flat = random_prob_vector(k * k, rng)
    out: dict = {}
    idx = 0
    for x in range(k):
        for y in range(k):
            out[(x, y)] = flat[idx]
            idx += 1
    return out


def _mi(joint: dict) -> float:
    pa: dict = {}
    pb: dict = {}
    for (a, b), p in joint.items():
        pa[a] = pa.get(a, 0.0) + p
        pb[b] = pb.get(b, 0.0) + p
    mi = 0.0
    for (a, b), p in joint.items():
        if p > 0:
            mi += p * math.log(p / (pa[a] * pb[b]))
    return mi


def extra_math_statements(k: int = 3) -> list[Statement]:
    """Faithful inequalities, each paired with an unfaithful twin the oracle catches."""
    out: list[Statement] = []

    # ---- Cauchy-Schwarz ---------------------------------------------------- #
    def cs_sample(rng):
        return {"a": _vec(rng, k, -1, 1), "b": _vec(rng, k, -1, 1)}

    def cs_lhs(inst):
        return sum(ai * bi for ai, bi in zip(inst["a"], inst["b"])) ** 2

    def cs_rhs(inst):
        return sum(ai * ai for ai in inst["a"]) * sum(bi * bi for bi in inst["b"])

    out += [
        Statement(
            name="cauchy_schwarz",
            description="Cauchy-Schwarz: (sum a_i b_i)^2 <= (sum a_i^2)(sum b_i^2).",
            lean="theorem cauchy_schwarz (a b : Fin n -> R) : (inner a b)^2 <= norm a ^2 * norm b ^2",
            sample=cs_sample,
            claim=lambda inst: cs_lhs(inst) <= cs_rhs(inst) + EPS,
            expected=Verdict.FAITHFUL,
            tags=("analysis", "cauchy-schwarz"),
        ),
        Statement(
            name="cauchy_schwarz_FLIPPED",
            description="Unfaithful: Cauchy-Schwarz with the inequality reversed.",
            lean="theorem cauchy_schwarz (a b) : (inner a b)^2 >= norm a ^2 * norm b ^2",
            sample=cs_sample,
            claim=lambda inst: cs_lhs(inst) >= cs_rhs(inst) - EPS,
            summarize=lambda inst: f"(a.b)^2={cs_lhs(inst):.4f} < |a|^2|b|^2={cs_rhs(inst):.4f}",
            expected=Verdict.FALSIFIED,
            tags=("analysis", "cauchy-schwarz", "direction-error"),
        ),
    ]

    # ---- AM-GM ------------------------------------------------------------- #
    def amgm_sample(rng):
        return {"x": _pos_vec(rng, k)}

    def am(inst):
        return sum(inst["x"]) / len(inst["x"])

    def gm(inst):
        return math.exp(sum(math.log(xi) for xi in inst["x"]) / len(inst["x"]))

    out += [
        Statement(
            name="am_gm",
            description="AM-GM: arithmetic mean >= geometric mean for positive reals.",
            lean="theorem am_gm (x : Fin n -> R) (h : forall i, 0 < x i) : geomMean x <= arithMean x",
            sample=amgm_sample,
            claim=lambda inst: am(inst) >= gm(inst) - EPS,
            expected=Verdict.FAITHFUL,
            tags=("analysis", "am-gm"),
        ),
        Statement(
            name="am_gm_FLIPPED",
            description="Unfaithful: AM-GM stated as arithmetic mean <= geometric mean.",
            lean="theorem am_gm (x) (h : forall i, 0 < x i) : arithMean x <= geomMean x",
            sample=amgm_sample,
            claim=lambda inst: am(inst) <= gm(inst) + EPS,
            summarize=lambda inst: f"AM={am(inst):.4f} > GM={gm(inst):.4f}",
            expected=Verdict.FALSIFIED,
            tags=("analysis", "am-gm", "direction-error"),
        ),
    ]

    # ---- triangle inequality ---------------------------------------------- #
    def tri_sample(rng):
        return {"x": rng.uniform(-5, 5), "y": rng.uniform(-5, 5)}

    out += [
        Statement(
            name="triangle_ineq",
            description="Triangle inequality: |x + y| <= |x| + |y|.",
            lean="theorem triangle (x y : R) : |x + y| <= |x| + |y|",
            sample=tri_sample,
            claim=lambda inst: abs(inst["x"] + inst["y"]) <= abs(inst["x"]) + abs(inst["y"]) + EPS,
            expected=Verdict.FAITHFUL,
            tags=("analysis", "triangle"),
        ),
        Statement(
            name="triangle_ineq_FLIPPED",
            description="Unfaithful: triangle inequality with >= instead of <=.",
            lean="theorem triangle (x y : R) : |x + y| >= |x| + |y|",
            sample=tri_sample,
            claim=lambda inst: abs(inst["x"] + inst["y"]) >= abs(inst["x"]) + abs(inst["y"]) - EPS,
            summarize=lambda inst: (f"x={inst['x']:.3f}, y={inst['y']:.3f}: "
                                    f"|x+y|={abs(inst['x']+inst['y']):.3f} < "
                                    f"|x|+|y|={abs(inst['x'])+abs(inst['y']):.3f}"),
            expected=Verdict.FALSIFIED,
            tags=("analysis", "triangle", "direction-error"),
        ),
    ]

    # ---- entropy subadditivity -------------------------------------------- #
    def sub_sample(rng):
        return {"joint": _joint_kk(rng, k)}

    def joint_entropy(inst):
        return entropy(list(inst["joint"].values()))

    def marg_entropies(inst):
        px: dict = {}
        py: dict = {}
        for (x, y), p in inst["joint"].items():
            px[x] = px.get(x, 0.0) + p
            py[y] = py.get(y, 0.0) + p
        return entropy(list(px.values())) + entropy(list(py.values()))

    out += [
        Statement(
            name="entropy_subadditive",
            description="Subadditivity: H(X, Y) <= H(X) + H(Y).",
            lean="theorem subadd (X Y) : H (X, Y) <= H X + H Y",
            sample=sub_sample,
            claim=lambda inst: joint_entropy(inst) <= marg_entropies(inst) + EPS,
            expected=Verdict.FAITHFUL,
            tags=("information-theory", "subadditivity"),
        ),
        Statement(
            name="entropy_subadditive_FLIPPED",
            description="Unfaithful: joint entropy claimed to dominate the sum of marginals.",
            lean="theorem subadd (X Y) : H (X, Y) >= H X + H Y",
            sample=sub_sample,
            claim=lambda inst: joint_entropy(inst) >= marg_entropies(inst) - EPS,
            summarize=lambda inst: f"H(X,Y)={joint_entropy(inst):.4f} < H(X)+H(Y)={marg_entropies(inst):.4f}",
            expected=Verdict.FALSIFIED,
            tags=("information-theory", "subadditivity", "direction-error"),
        ),
    ]

    # ---- mutual information sign ------------------------------------------ #
    def mi_sample(rng):
        return {"joint": _joint_kk(rng, k)}

    out += [
        Statement(
            name="mutual_info_nonneg",
            description="Mutual information is non-negative: I(X; Y) >= 0.",
            lean="theorem mi_nonneg (X Y) : 0 <= I X Y",
            sample=mi_sample,
            claim=lambda inst: _mi(inst["joint"]) >= -EPS,
            expected=Verdict.FAITHFUL,
            tags=("information-theory", "mutual-information"),
        ),
        Statement(
            name="mutual_info_nonpos_WRONG",
            description="Unfaithful: mutual information formalized with the wrong sign (I <= 0).",
            lean="theorem mi_sign (X Y) : I X Y <= 0",
            sample=mi_sample,
            claim=lambda inst: _mi(inst["joint"]) <= EPS,
            summarize=lambda inst: f"I(X;Y)={_mi(inst['joint']):.4f} > 0",
            expected=Verdict.FALSIFIED,
            tags=("information-theory", "mutual-information", "direction-error"),
        ),
    ]

    # ---- cross entropy >= entropy (Gibbs again, different surface) -------- #
    def ce_sample(rng):
        return {"p": random_prob_vector(k, rng), "q": random_prob_vector(k, rng)}

    def cross_entropy(inst):
        return -sum(pi * math.log(qi) for pi, qi in zip(inst["p"], inst["q"]) if pi > 0)

    out += [
        Statement(
            name="cross_entropy_ge_entropy",
            description="Cross entropy lower bound: H(p, q) >= H(p).",
            lean="theorem ce_ge_h (p q : Distribution) : H p <= crossEntropy p q",
            sample=ce_sample,
            claim=lambda inst: cross_entropy(inst) >= entropy(inst["p"]) - EPS,
            expected=Verdict.FAITHFUL,
            tags=("information-theory", "cross-entropy"),
        ),
        Statement(
            name="cross_entropy_ge_entropy_FLIPPED",
            description="Unfaithful: cross entropy claimed to be at most the entropy.",
            lean="theorem ce_le_h (p q) : crossEntropy p q <= H p",
            sample=ce_sample,
            claim=lambda inst: cross_entropy(inst) <= entropy(inst["p"]) + EPS,
            summarize=lambda inst: f"H(p,q)={cross_entropy(inst):.4f} > H(p)={entropy(inst['p']):.4f}",
            expected=Verdict.FALSIFIED,
            tags=("information-theory", "cross-entropy", "direction-error"),
        ),
    ]

    # ---- Jensen for log (concavity) --------------------------------------- #
    def jensen_sample(rng):
        return {"x": _pos_vec(rng, k, hi=5.0)}

    def mean(inst):
        return sum(inst["x"]) / len(inst["x"])

    def mean_log(inst):
        return sum(math.log(xi) for xi in inst["x"]) / len(inst["x"])

    out += [
        Statement(
            name="jensen_log_concave",
            description="Jensen for the logarithm: log(mean x) >= mean(log x).",
            lean="theorem jensen_log (x) (h : forall i, 0 < x i) : mean (log . x) <= log (mean x)",
            sample=jensen_sample,
            claim=lambda inst: math.log(mean(inst)) >= mean_log(inst) - EPS,
            expected=Verdict.FAITHFUL,
            tags=("analysis", "jensen"),
        ),
        Statement(
            name="jensen_log_concave_FLIPPED",
            description="Unfaithful: log treated as convex (direction reversed).",
            lean="theorem jensen_log (x) (h : forall i, 0 < x i) : log (mean x) <= mean (log . x)",
            sample=jensen_sample,
            claim=lambda inst: math.log(mean(inst)) <= mean_log(inst) + EPS,
            summarize=lambda inst: f"log(mean)={math.log(mean(inst)):.4f} > mean(log)={mean_log(inst):.4f}",
            expected=Verdict.FALSIFIED,
            tags=("analysis", "jensen", "direction-error"),
        ),
    ]

    # ---- a too-strong (unsound) over-claim on variance -------------------- #
    def var_sample(rng):
        return {"x": _vec(rng, k, -5, 5)}

    out += [
        Statement(
            name="variance_nonneg",
            description="Variance is non-negative.",
            lean="theorem var_nonneg (x) : 0 <= variance x",
            sample=var_sample,
            claim=lambda inst: (sum(xi * xi for xi in inst["x"]) / k - (sum(inst["x"]) / k) ** 2) >= -EPS,
            expected=Verdict.FAITHFUL,
            tags=("probability", "variance"),
        ),
        Statement(
            name="variance_mean_nonneg_WRONG",
            description="Unfaithful: claims the sample mean is always non-negative.",
            lean="theorem mean_nonneg (x) : 0 <= mean x",
            sample=var_sample,
            claim=lambda inst: (sum(inst["x"]) / k) >= -EPS,
            summarize=lambda inst: f"mean={sum(inst['x'])/k:.4f} < 0 for x={[round(v,2) for v in inst['x']]}",
            expected=Verdict.FALSIFIED,
            tags=("probability", "variance", "over-claim"),
        ),
    ]

    # ---- a second vacuity trap -------------------------------------------- #
    out += [
        Statement(
            name="self_successor_vacuous",
            description="Vacuity trap: a claim guarded by x = x + 1, which nothing satisfies.",
            lean="theorem v (x : R) (h : x = x + 1) : x = 0",
            sample=lambda rng: {"x": rng.uniform(-10, 10)},
            claim=lambda inst: abs(inst["x"]) < EPS,
            hypothesis=lambda inst: abs(inst["x"] - (inst["x"] + 1)) < EPS,  # never
            expected=Verdict.INCONCLUSIVE,
            tags=("vacuity",),
        ),
    ]

    return out


def math_items() -> list[Item]:
    statements = information_theory_library() + extra_math_statements()
    items: list[Item] = []
    for s in statements:
        gold = s.expected or Verdict.FAITHFUL
        family = (
            "faithful"
            if gold is Verdict.FAITHFUL
            else (s.tags[-1] if s.tags and gold is not Verdict.INCONCLUSIVE else "vacuity")
        )
        items.append(
            Item(
                name=s.name,
                surface="math",
                intent=s.description,
                statement=s.lean,
                gold=gold,
                family=family,
                math=s,
            )
        )
    return items


# --------------------------------------------------------------------------- #
# code + verina surfaces (recorded real verdicts)
# --------------------------------------------------------------------------- #
def _load(name: str) -> dict:
    path = os.path.join(_RESULTS, name)
    with open(path) as fh:
        return json.load(fh)


def code_items() -> list[Item]:
    data = _load("codespec_offline.json")
    items: list[Item] = []
    for r in data["results"]:
        verdict = Verdict(r["verdict"])
        items.append(
            Item(
                name=r["name"],
                surface="code",
                intent="code spec should accept the reference and reject every wrong impl",
                statement=r["name"],
                gold=verdict,
                family="faithful" if verdict is Verdict.FAITHFUL else verdict.value.lower(),
                precomputed=r,
            )
        )
    return items


def verina_items() -> list[Item]:
    data = _load("verina_live.json")
    items: list[Item] = []
    for r in data["results"]:
        # Real Verina tasks ship as faithful; treat them as the faithful ground
        # truth that measures each judge's false-positive rate.
        items.append(
            Item(
                name=r["name"],
                surface="verina",
                intent="real Verina postcondition, audited live over AXLE",
                statement=r["name"],
                gold=Verdict.FAITHFUL,
                family="faithful",
                precomputed=r,
            )
        )
    return items


def benchmark_corpus(surfaces: tuple[str, ...] = ("math", "code", "verina")) -> list[Item]:
    items: list[Item] = []
    if "math" in surfaces:
        items += math_items()
    if "code" in surfaces:
        items += code_items()
    if "verina" in surfaces:
        items += verina_items()
    return items

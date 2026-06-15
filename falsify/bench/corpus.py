"""The labelled benchmark corpus.

Three surfaces:

  * ``math``   -- inequalities and identities from analysis, probability and
    information theory. Each faithful statement is paired with at least one
    unfaithful formalization (a dropped hypothesis, a flipped direction, an
    over-strong claim). Every family is generated across a range of dimensions /
    alphabet sizes, so one idea ("Cauchy-Schwarz") turns into many distinct test
    cases. All of these are checked by the Monte-Carlo oracle, which runs locally
    with no API key, so this part of the benchmark is fully reproducible offline.
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
from dataclasses import dataclass
from typing import Optional

from ..core.oracle import Verdict
from ..montecarlo.numerical import EPS, Statement, entropy, random_prob_vector

_HERE = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "results")

# How wide to spread each family. Cheap families (cost grows like k) get a long
# range; the ones whose cost grows like k^2 or k^3 are kept smaller so the whole
# benchmark still runs in a few seconds.
KS_CHEAP = tuple(range(2, 15))   # 13 sizes
KS_MED = tuple(range(2, 8))      # 6 sizes  (k^2 families)
KS_DPI = tuple(range(2, 6))      # 4 sizes  (k^3 family)


@dataclass
class Item:
    """One labelled claim in the benchmark."""

    name: str
    surface: str                 # "math" | "code" | "verina"
    intent: str                  # what the statement is supposed to mean
    statement: str               # the formal statement, as written
    gold: Verdict                # ground-truth label
    family: str                  # the kind of bug (or "faithful")
    math: Optional[Statement] = None          # for the math surface: the runnable Statement
    precomputed: Optional[dict] = None         # for code/verina: the oracle's recorded verdict

    @property
    def gold_unfaithful(self) -> bool:
        return self.gold.is_falsified


# --------------------------------------------------------------------------- #
# small samplers (stdlib only)
# --------------------------------------------------------------------------- #
def _vec(rng, k, lo, hi):
    return [rng.uniform(lo, hi) for _ in range(k)]


def _pos_vec(rng, k, hi=3.0):
    return [rng.uniform(1e-3, hi) for _ in range(k)]


def _nonneg_vec(rng, k, hi=3.0):
    return [rng.random() * hi + 1e-6 for _ in range(k)]


def _joint(rng, k):
    flat = random_prob_vector(k * k, rng)
    out = {}
    i = 0
    for x in range(k):
        for y in range(k):
            out[(x, y)] = flat[i]
            i += 1
    return out


def _marginals(joint):
    px, py = {}, {}
    for (x, y), p in joint.items():
        px[x] = px.get(x, 0.0) + p
        py[y] = py.get(y, 0.0) + p
    return px, py


def _mi(joint):
    px, py = _marginals(joint)
    return sum(p * math.log(p / (px[a] * py[b])) for (a, b), p in joint.items() if p > 0)


def _F(name, k, intent, lean, sample, claim, gold, family, hypothesis=None, summarize=None):
    """Shorthand to build a labelled math Statement."""
    return Statement(
        name=f"{name}_k{k}",
        description=intent,
        lean=lean,
        sample=sample,
        claim=claim,
        hypothesis=hypothesis,
        summarize=summarize,
        expected=gold,
        tags=(family,),
    )


# --------------------------------------------------------------------------- #
# math families: each returns a faithful Statement plus its unfaithful twins
# --------------------------------------------------------------------------- #
def fam_kl(k):
    def s_dist(rng):
        return {"p": random_prob_vector(k, rng), "q": random_prob_vector(k, rng)}

    def s_unnorm(rng):
        return {"p": random_prob_vector(k, rng), "q": _nonneg_vec(rng, k)}

    def kl(inst):
        return sum(pi * math.log(pi / qi) for pi, qi in zip(inst["p"], inst["q"]) if pi > 0)

    return [
        _F("kl_nonneg", k, "Gibbs: KL(p||q) >= 0 for distributions.",
           "0 <= klDiv p q", s_dist, lambda i: kl(i) >= -EPS, Verdict.FAITHFUL, "faithful",
           hypothesis=lambda i: abs(sum(i["q"]) - 1.0) < 1e-6),
        _F("kl_DROPPED_norm", k, "Unfaithful: KL >= 0 with q not required to sum to 1.",
           "0 <= sum p_i log(p_i/q_i)", s_unnorm, lambda i: kl(i) >= -EPS,
           Verdict.FALSIFIED, "dropped-hypothesis",
           summarize=lambda i: f"sum q={sum(i['q']):.2f}!=1 => KL={kl(i):.3f} < 0"),
        _F("kl_FLIPPED", k, "Unfaithful: KL <= 0 (sign flipped).",
           "klDiv p q <= 0", s_dist, lambda i: kl(i) <= EPS, Verdict.FALSIFIED, "direction-error",
           summarize=lambda i: f"KL={kl(i):.3f} > 0"),
    ]


def fam_dpi(k):
    def stoch(rng, rows, cols):
        return [random_prob_vector(cols, rng) for _ in range(rows)]

    def s_markov(rng):
        px = random_prob_vector(k, rng)
        pygx = stoch(rng, k, k)
        pzgy = stoch(rng, k, k)
        j = {}
        for x in range(k):
            for y in range(k):
                for z in range(k):
                    j[(x, y, z)] = px[x] * pygx[x][y] * pzgy[y][z]
        return {"j": j}

    def s_nonmarkov(rng):
        px = random_prob_vector(k, rng)
        pygx = stoch(rng, k, k)
        j = {}
        for x in range(k):
            for y in range(k):
                pz = [0.05 / (k - 1)] * k
                pz[x % k] = 0.95
                for z in range(k):
                    j[(x, y, z)] = px[x] * pygx[x][y] * pz[z]
        return {"j": j}

    def marg(j, keep):
        out = {}
        for (x, y, z), p in j.items():
            key = tuple(v for v, a in zip((x, y, z), "xyz") if a in keep)
            out[key] = out.get(key, 0.0) + p
        return out

    def ixy(j):
        return _mi(marg(j, "xy"))

    def ixz(j):
        return _mi(marg(j, "xz"))

    return [
        _F("dpi", k, "Data processing: X->Y->Z implies I(X;Z) <= I(X;Y).",
           "I X Z <= I X Y", s_markov, lambda i: ixz(i["j"]) <= ixy(i["j"]) + EPS,
           Verdict.FAITHFUL, "faithful"),
        _F("dpi_DROPPED_markov", k, "Unfaithful: data processing without the Markov hypothesis.",
           "I X Z <= I X Y", s_nonmarkov, lambda i: ixz(i["j"]) <= ixy(i["j"]) + EPS,
           Verdict.FALSIFIED, "dropped-hypothesis",
           summarize=lambda i: f"I(X;Z)={ixz(i['j']):.3f} > I(X;Y)={ixy(i['j']):.3f}"),
    ]


def fam_concave(k):
    def s(rng):
        return {"p": random_prob_vector(k, rng), "q": random_prob_vector(k, rng),
                "lam": rng.uniform(0.1, 0.9)}

    def mix(i):
        return [i["lam"] * pi + (1 - i["lam"]) * qi for pi, qi in zip(i["p"], i["q"])]

    def rhs(i):
        return i["lam"] * entropy(i["p"]) + (1 - i["lam"]) * entropy(i["q"])

    return [
        _F("entropy_concave", k, "Concavity of entropy: H(mix) >= lam H(p) + (1-lam) H(q).",
           "lam*H p + (1-lam)*H q <= H (mix p q)", s, lambda i: entropy(mix(i)) >= rhs(i) - EPS,
           Verdict.FAITHFUL, "faithful"),
        _F("entropy_convex_WRONG", k, "Unfaithful: entropy treated as convex (direction flipped).",
           "H (mix p q) <= lam*H p + (1-lam)*H q", s, lambda i: entropy(mix(i)) <= rhs(i) + EPS,
           Verdict.FALSIFIED, "direction-error",
           summarize=lambda i: f"H(mix)={entropy(mix(i)):.3f} > rhs={rhs(i):.3f}"),
    ]


def fam_cauchy(k):
    def s(rng):
        return {"a": _vec(rng, k, -1, 1), "b": _vec(rng, k, -1, 1)}

    def lhs(i):
        return sum(a * b for a, b in zip(i["a"], i["b"])) ** 2

    def rhs(i):
        return sum(a * a for a in i["a"]) * sum(b * b for b in i["b"])

    return [
        _F("cauchy_schwarz", k, "Cauchy-Schwarz: (a.b)^2 <= |a|^2 |b|^2.",
           "(inner a b)^2 <= normSq a * normSq b", s, lambda i: lhs(i) <= rhs(i) + EPS,
           Verdict.FAITHFUL, "faithful"),
        _F("cauchy_schwarz_FLIPPED", k, "Unfaithful: Cauchy-Schwarz reversed.",
           "(inner a b)^2 >= normSq a * normSq b", s, lambda i: lhs(i) >= rhs(i) - EPS,
           Verdict.FALSIFIED, "direction-error",
           summarize=lambda i: f"(a.b)^2={lhs(i):.3f} < |a|^2|b|^2={rhs(i):.3f}"),
    ]


def fam_amgm(k):
    def s(rng):
        return {"x": _pos_vec(rng, k)}

    def am(i):
        return sum(i["x"]) / k

    def gm(i):
        return math.exp(sum(math.log(v) for v in i["x"]) / k)

    return [
        _F("am_gm", k, "AM-GM: geometric mean <= arithmetic mean for positive reals.",
           "geomMean x <= arithMean x", s, lambda i: am(i) >= gm(i) - EPS,
           Verdict.FAITHFUL, "faithful"),
        _F("am_gm_FLIPPED", k, "Unfaithful: AM-GM stated as arithmetic mean <= geometric mean.",
           "arithMean x <= geomMean x", s, lambda i: am(i) <= gm(i) + EPS,
           Verdict.FALSIFIED, "direction-error",
           summarize=lambda i: f"AM={am(i):.3f} > GM={gm(i):.3f}"),
    ]


def fam_triangle(k):
    def s(rng):
        return {"x": _vec(rng, k, -5, 5), "y": _vec(rng, k, -5, 5)}

    def nrm(v):
        return math.sqrt(sum(c * c for c in v))

    def lhs(i):
        return nrm([a + b for a, b in zip(i["x"], i["y"])])

    def rhs(i):
        return nrm(i["x"]) + nrm(i["y"])

    return [
        _F("triangle", k, "Triangle inequality: |x + y| <= |x| + |y|.",
           "norm (x + y) <= norm x + norm y", s, lambda i: lhs(i) <= rhs(i) + EPS,
           Verdict.FAITHFUL, "faithful"),
        _F("triangle_FLIPPED", k, "Unfaithful: triangle inequality reversed.",
           "norm (x + y) >= norm x + norm y", s, lambda i: lhs(i) >= rhs(i) - EPS,
           Verdict.FALSIFIED, "direction-error",
           summarize=lambda i: f"|x+y|={lhs(i):.3f} < |x|+|y|={rhs(i):.3f}"),
    ]


def fam_qmam(k):
    def s(rng):
        return {"x": _pos_vec(rng, k, hi=5.0)}

    def qm(i):
        return math.sqrt(sum(v * v for v in i["x"]) / k)

    def am(i):
        return sum(i["x"]) / k

    return [
        _F("qm_am", k, "Quadratic mean >= arithmetic mean.",
           "arithMean x <= quadMean x", s, lambda i: qm(i) >= am(i) - EPS,
           Verdict.FAITHFUL, "faithful"),
        _F("qm_am_FLIPPED", k, "Unfaithful: quadratic mean <= arithmetic mean.",
           "quadMean x <= arithMean x", s, lambda i: qm(i) <= am(i) + EPS,
           Verdict.FALSIFIED, "direction-error",
           summarize=lambda i: f"QM={qm(i):.3f} > AM={am(i):.3f}"),
    ]


def fam_jensen(k):
    def s(rng):
        return {"x": _pos_vec(rng, k, hi=5.0)}

    def lhs(i):
        return math.log(sum(i["x"]) / k)

    def rhs(i):
        return sum(math.log(v) for v in i["x"]) / k

    return [
        _F("jensen_log", k, "Jensen for log: log(mean x) >= mean(log x).",
           "mean (log . x) <= log (mean x)", s, lambda i: lhs(i) >= rhs(i) - EPS,
           Verdict.FAITHFUL, "faithful"),
        _F("jensen_log_FLIPPED", k, "Unfaithful: log treated as convex.",
           "log (mean x) <= mean (log . x)", s, lambda i: lhs(i) <= rhs(i) + EPS,
           Verdict.FALSIFIED, "direction-error",
           summarize=lambda i: f"log(mean)={lhs(i):.3f} > mean(log)={rhs(i):.3f}"),
    ]


def fam_variance(k):
    def s(rng):
        return {"x": _vec(rng, k, -5, 5)}

    def var(i):
        return sum(v * v for v in i["x"]) / k - (sum(i["x"]) / k) ** 2

    return [
        _F("variance_nonneg", k, "Variance is non-negative.",
           "0 <= variance x", s, lambda i: var(i) >= -EPS, Verdict.FAITHFUL, "faithful"),
        _F("mean_nonneg_WRONG", k, "Unfaithful: claims the sample mean is always non-negative.",
           "0 <= mean x", s, lambda i: (sum(i["x"]) / k) >= -EPS,
           Verdict.FALSIFIED, "over-claim",
           summarize=lambda i: f"mean={sum(i['x'])/k:.3f} < 0"),
    ]


def fam_cross_entropy(k):
    def s(rng):
        return {"p": random_prob_vector(k, rng), "q": random_prob_vector(k, rng)}

    def ce(i):
        return -sum(pi * math.log(qi) for pi, qi in zip(i["p"], i["q"]) if pi > 0)

    return [
        _F("cross_entropy_ge", k, "Cross entropy lower bound: H(p,q) >= H(p).",
           "H p <= crossEntropy p q", s, lambda i: ce(i) >= entropy(i["p"]) - EPS,
           Verdict.FAITHFUL, "faithful"),
        _F("cross_entropy_ge_FLIPPED", k, "Unfaithful: cross entropy <= entropy.",
           "crossEntropy p q <= H p", s, lambda i: ce(i) <= entropy(i["p"]) + EPS,
           Verdict.FALSIFIED, "direction-error",
           summarize=lambda i: f"H(p,q)={ce(i):.3f} > H(p)={entropy(i['p']):.3f}"),
    ]


def fam_entropy_upper(k):
    def s(rng):
        return {"p": random_prob_vector(k, rng)}

    return [
        _F("entropy_upper", k, "Entropy upper bound: H(p) <= log k.",
           "H p <= log k", s, lambda i: entropy(i["p"]) <= math.log(k) + EPS,
           Verdict.FAITHFUL, "faithful"),
        _F("entropy_lower_WRONG", k, "Unfaithful: claims H(p) >= log k (true only at the uniform).",
           "log k <= H p", s, lambda i: entropy(i["p"]) >= math.log(k) - EPS,
           Verdict.FALSIFIED, "over-claim",
           summarize=lambda i: f"H(p)={entropy(i['p']):.3f} < log k={math.log(k):.3f}"),
    ]


def fam_subadditive(k):
    def s(rng):
        return {"j": _joint(rng, k)}

    def hjoint(i):
        return entropy(list(i["j"].values()))

    def hmarg(i):
        px, py = _marginals(i["j"])
        return entropy(list(px.values())) + entropy(list(py.values()))

    return [
        _F("entropy_subadditive", k, "Subadditivity: H(X,Y) <= H(X) + H(Y).",
           "H (X, Y) <= H X + H Y", s, lambda i: hjoint(i) <= hmarg(i) + EPS,
           Verdict.FAITHFUL, "faithful"),
        _F("entropy_subadditive_FLIPPED", k, "Unfaithful: joint entropy >= sum of marginals.",
           "H X + H Y <= H (X, Y)", s, lambda i: hjoint(i) >= hmarg(i) - EPS,
           Verdict.FALSIFIED, "direction-error",
           summarize=lambda i: f"H(X,Y)={hjoint(i):.3f} < H(X)+H(Y)={hmarg(i):.3f}"),
    ]


def fam_mi_sign(k):
    def s(rng):
        return {"j": _joint(rng, k)}

    return [
        _F("mutual_info_nonneg", k, "Mutual information is non-negative: I(X;Y) >= 0.",
           "0 <= I X Y", s, lambda i: _mi(i["j"]) >= -EPS, Verdict.FAITHFUL, "faithful"),
        _F("mutual_info_nonpos_WRONG", k, "Unfaithful: mutual information with the wrong sign.",
           "I X Y <= 0", s, lambda i: _mi(i["j"]) <= EPS, Verdict.FALSIFIED, "direction-error",
           summarize=lambda i: f"I(X;Y)={_mi(i['j']):.3f} > 0"),
    ]


def fam_cond_entropy(k):
    def s(rng):
        return {"j": _joint(rng, k)}

    def hx(i):
        px, _ = _marginals(i["j"])
        return entropy(list(px.values()))

    def hxy(i):
        # H(X|Y) = H(X) - I(X;Y)
        return hx(i) - _mi(i["j"])

    return [
        _F("cond_reduces_entropy", k, "Conditioning reduces entropy: H(X|Y) <= H(X).",
           "H X given Y <= H X", s, lambda i: hxy(i) <= hx(i) + EPS,
           Verdict.FAITHFUL, "faithful"),
        _F("cond_increases_entropy_WRONG", k, "Unfaithful: conditioning claimed to increase entropy.",
           "H X <= H X given Y", s, lambda i: hxy(i) >= hx(i) - EPS,
           Verdict.FALSIFIED, "direction-error",
           summarize=lambda i: f"H(X|Y)={hxy(i):.3f} < H(X)={hx(i):.3f}"),
    ]


def fam_vacuity(k):
    return [
        _F("self_successor_vacuous", k, "Vacuity trap: claim guarded by x = x + 1, which nothing satisfies.",
           "x = x + 1 -> x = 0", lambda rng: {"x": rng.uniform(-10, 10)},
           lambda i: abs(i["x"]) < EPS, Verdict.INCONCLUSIVE, "vacuity",
           hypothesis=lambda i: abs(i["x"] - (i["x"] + 1)) < EPS),
    ]


# Subtle bugs: a spec that is wrong only on a small fraction p of inputs. The
# label is known (it is unfaithful), but whether Monte-Carlo finds the
# counterexample depends on how many draws it spends, since the probability of
# hitting the bad region in N draws is 1 - (1 - p)^N. These are what make the
# benchmark a real test of effort rather than a clean 100%: at a small budget
# Popper misses the rarest ones, and recall climbs toward 1 as the budget grows.
RARE_PS = (0.2, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001, 0.0005, 0.0002, 0.0001)


def rare_edge_statements() -> list[Statement]:
    out: list[Statement] = []
    for p in RARE_PS:
        out.append(Statement(
            name=f"rare_edge_p{p}",
            description=f"Subtle bug: a postcondition that fails on about a {p:g} fraction of inputs.",
            lean=f"theorem post (x) : score x > {p}",
            sample=lambda rng: {"u": rng.random()},
            claim=lambda i, p=p: i["u"] > p,
            summarize=lambda i, p=p: f"input scored {i['u']:.5f} <= {p:g} (the spec rejects it)",
            expected=Verdict.FALSIFIED,
            tags=("rare-edge",),
        ))
    # genuinely faithful twins (true on every input), so the subtle family also
    # contributes to the false-positive measurement.
    for j in range(2):
        out.append(Statement(
            name=f"rare_edge_faithful_{j}",
            description="A postcondition that holds on every input.",
            lean="theorem post (x) : score x >= 0",
            sample=lambda rng: {"u": rng.random()},
            claim=lambda i: i["u"] >= 0.0,
            expected=Verdict.FAITHFUL,
            tags=("faithful",),
        ))
    return out


_CHEAP = [fam_kl, fam_concave, fam_cauchy, fam_amgm, fam_triangle, fam_qmam,
          fam_jensen, fam_variance, fam_cross_entropy, fam_entropy_upper]
_MED = [fam_subadditive, fam_mi_sign, fam_cond_entropy]
_DPI = [fam_dpi]


def generate_math_statements() -> list[Statement]:
    out: list[Statement] = []
    for fam in _CHEAP:
        for k in KS_CHEAP:
            out += fam(k)
    for fam in _MED:
        for k in KS_MED:
            out += fam(k)
    for fam in _DPI:
        for k in KS_DPI:
            out += fam(k)
    for k in (2, 5, 9):           # a few vacuity traps
        out += fam_vacuity(k)
    out += rare_edge_statements()
    return out


def math_items() -> list[Item]:
    items: list[Item] = []
    for s in generate_math_statements():
        gold = s.expected or Verdict.FAITHFUL
        items.append(
            Item(name=s.name, surface="math", intent=s.description, statement=s.lean,
                 gold=gold, family=s.tags[0] if s.tags else "faithful", math=s)
        )
    return items


# --------------------------------------------------------------------------- #
# code + verina surfaces (recorded real verdicts)
# --------------------------------------------------------------------------- #
def _load(name: str) -> dict:
    with open(os.path.join(_RESULTS, name)) as fh:
        return json.load(fh)


def code_items() -> list[Item]:
    data = _load("codespec_offline.json")
    items: list[Item] = []
    for r in data["results"]:
        verdict = Verdict(r["verdict"])
        items.append(
            Item(name=r["name"], surface="code",
                 intent="code spec should accept the reference and reject every wrong impl",
                 statement=r["name"], gold=verdict,
                 family="faithful" if verdict is Verdict.FAITHFUL else verdict.value.lower(),
                 precomputed=r)
        )
    return items


def verina_items() -> list[Item]:
    data = _load("verina_live.json")
    items: list[Item] = []
    for r in data["results"]:
        items.append(
            Item(name=r["name"], surface="verina",
                 intent="real Verina postcondition, audited live over AXLE",
                 statement=r["name"], gold=Verdict.FAITHFUL, family="faithful", precomputed=r)
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

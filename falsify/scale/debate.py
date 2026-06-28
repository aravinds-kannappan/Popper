"""Doubly-efficient debate: a cheap verifier recovers the missing premise.

*Scalable AI Safety via Doubly-Efficient Debate* (Brown-Cohen, Irving, Piliouras
2023) formalizes the oversight bet behind Popper. A weak, cheap verifier can
correctly adjudicate claims made by far more powerful provers, as long as the
provers argue against each other and the verifier only has to *check* short steps
rather than *produce* the proof. That is the IP = PSPACE intuition turned into a
training protocol: the verifier's compute is tiny next to the prover's, yet the
honest side can always win.

Popper is that verifier. The expensive prover (AxiomProver) and a too-optimistic
author both assert "this statement is fine"; Popper's millisecond probes are the
linear-time checker that calls the bluff. This module stages the debate
explicitly as self-play around one statement:

  * the **Falsifier** uses adaptive search (see :mod:`.importance`) to produce a
    counterexample to the statement as written;
  * the **Defender** answers with a *rescue hypothesis* - the minimal premise
    that, if the author had stated it, would exclude that counterexample (the
    dropped ``sum q = 1``, the missing Markov assumption);
  * the **verifier** adjudicates by *executing*: it re-runs the Falsifier on the
    restricted space the premise defines. If the Falsifier still breaks it, the
    Defender's premise was a bluff; if it cannot, the premise is the genuine
    missing hypothesis and the debate has recovered the repair.

The output is not just a verdict but the recovered premise, which is the
actionable thing a prover or a human needs: "your theorem is false as written;
add this hypothesis and it holds."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from ..core.oracle import Verdict
from .importance import AdaptiveFalsifier, ScoredClaim, UniformFalsifier


@dataclass
class RescueHypothesis:
    """A premise the Defender can add to rescue a statement.

    ``holds`` tests whether an instance already satisfies the premise (used to
    check whether a counterexample *violates* it). ``restricted`` is the same
    claim restricted to the manifold where the premise holds - built
    constructively, exactly as the faithful montecarlo sampler constructs a
    Markov chain or a normalized distribution.
    """

    name: str
    holds: Callable[[dict], bool]
    restricted: ScoredClaim


@dataclass
class DebateMove:
    speaker: str   # "falsifier" | "defender" | "verifier"
    text: str


@dataclass
class DebateTranscript:
    claim: str
    moves: list[DebateMove] = field(default_factory=list)
    verdict: Verdict = Verdict.INCONCLUSIVE
    recovered_premise: Optional[str] = None
    counterexample: Optional[str] = None

    def say(self, speaker: str, text: str) -> None:
        self.moves.append(DebateMove(speaker, text))

    def render(self) -> str:
        head = f"=== debate: {self.claim} -> {self.verdict.value}" + (
            f" (premise: {self.recovered_premise})" if self.recovered_premise else "") + " ==="
        body = "\n".join(f"  [{m.speaker:<9}] {m.text}" for m in self.moves)
        return head + "\n" + body


def run_debate(claim: ScoredClaim, rescues: list[RescueHypothesis], *,
               budget: int = 2000, seed: int = 0) -> DebateTranscript:
    """Stage one falsifier/defender debate adjudicated by adaptive search."""
    t = DebateTranscript(claim=claim.name)

    # Falsifier opens: try to break the statement as written.
    opener = AdaptiveFalsifier(budget=budget, seed=seed).search(claim)
    if not opener.found:
        t.say("falsifier", f"no counterexample in {opener.draws_used} adaptive draws; I concede")
        t.say("verifier", "statement survives as written")
        t.verdict = Verdict.FAITHFUL
        return t

    witness = opener.witness or {}
    ce = claim.render_ce(witness)
    t.counterexample = ce
    t.say("falsifier", f"counterexample after {opener.draws_used} draws: {ce}")

    # Defender answers: which proposed premises does this witness violate?
    candidates = [r for r in rescues if not r.holds(witness)]
    if not candidates:
        t.say("defender", "no available premise excludes this witness; I concede")
        t.say("verifier", "statement is false as written and no premise rescues it")
        t.verdict = Verdict.FALSIFIED
        return t

    # Verifier adjudicates each proposed premise by executing the restricted search.
    for r in candidates:
        t.say("defender", f"add premise '{r.name}'; the witness violates it, so it was the missing hypothesis")
        check = AdaptiveFalsifier(budget=budget, seed=seed + 1).search(r.restricted)
        if check.found:
            t.say("verifier",
                  f"premise '{r.name}' rejected: still falsifiable ({claim.render_ce(check.witness or {})})")
            continue
        # double-check with an independent uniform sweep so the win is not an artefact
        confirm = UniformFalsifier(budget=budget, seed=seed + 2).search(r.restricted)
        if confirm.found:
            t.say("verifier", f"premise '{r.name}' rejected on uniform re-check")
            continue
        t.say("verifier",
              f"premise '{r.name}' holds up under {check.draws_used}+{confirm.draws_used} draws; Defender wins")
        t.verdict = Verdict.FALSIFIED  # the statement *as written* is still false
        t.recovered_premise = r.name
        return t

    t.say("verifier", "every proposed premise still breaks; statement is false as written")
    t.verdict = Verdict.FALSIFIED
    return t


# --------------------------------------------------------------------------- #
# A worked debate: Gibbs' inequality with the normalization premise dropped.
# --------------------------------------------------------------------------- #
def gibbs_debate(K: int = 3, hi: float = 3.0) -> tuple[ScoredClaim, list[RescueHypothesis]]:
    """KL(p||q) >= 0 stated for an unnormalized q, with candidate rescue premises.

    The true missing premise is ``sum q = 1``. A decoy premise the witness also
    violates does *not* rescue it, so the verifier must actually execute to tell
    them apart.
    """
    import math

    def _norm(xs):
        s = sum(xs)
        return [x / s for x in xs]

    def _kl(p, q):
        return sum(pi * math.log(pi / qi) for pi, qi in zip(p, q) if pi > 0)

    def build_unnorm(u):
        p = _norm([u[i] + 1e-6 for i in range(K)])
        q = [u[K + i] * hi + 1e-6 for i in range(K)]   # nonneg but NOT a distribution
        return {"p": p, "q": q}

    def margin(inst):
        return _kl(inst["p"], inst["q"])

    def summarize(inst):
        return (f"q={[round(x,3) for x in inst['q']]} (sum={sum(inst['q']):.3f} != 1) "
                f"=> KL={_kl(inst['p'], inst['q']):.4f} < 0")

    as_written = ScoredClaim(
        name="gibbs_dropped_normalization", dim=2 * K,
        description="KL(p||q) >= 0 stated for an arbitrary nonnegative q",
        build=build_unnorm, margin=margin, summarize=summarize,
        expected=Verdict.FALSIFIED, tags=("debate", "dropped-hypothesis"))

    # the genuine rescue: q is a distribution (constructed on the simplex)
    def build_norm(u):
        p = _norm([u[i] + 1e-6 for i in range(K)])
        q = _norm([u[K + i] + 1e-6 for i in range(K)])
        return {"p": p, "q": q}

    true_premise = RescueHypothesis(
        name="sum_q_eq_1",
        holds=lambda inst: abs(sum(inst["q"]) - 1.0) < 1e-6,
        restricted=ScoredClaim(name="gibbs_qnorm", dim=2 * K, description="KL with q on the simplex",
                               build=build_norm, margin=margin, summarize=summarize,
                               expected=Verdict.FAITHFUL))

    # a decoy the witness usually also violates, but which does NOT rescue the
    # claim: capping q's first coordinate leaves sum q != 1, so KL can still go
    # negative. The verifier must execute to reject it.
    def build_cap(u):
        inst = build_unnorm(u)
        inst["q"][0] = min(inst["q"][0], 0.1)
        return inst

    decoy = RescueHypothesis(
        name="q0_small",
        holds=lambda inst: inst["q"][0] < 0.1 + 1e-9,
        restricted=ScoredClaim(name="gibbs_q0cap", dim=2 * K, description="KL with q[0] capped",
                               build=build_cap, margin=margin, summarize=summarize,
                               expected=Verdict.FALSIFIED))

    return as_written, [decoy, true_premise]

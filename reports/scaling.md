# Scaling Popper with AI-safety research

Popper's job is spec faithfulness: deciding whether a formal statement says what
its author meant before any expensive proof compute is spent. The alignment
literature has been studying the same object under a different name for years. A
reward model is a specification for "good behaviour". A too-weak reward is a spec
that accepts wrong answers. A model that games the reward is a wrong
implementation the spec failed to reject. So the methods that scale reward
modelling and oversight are, almost line for line, the methods that scale a
faithfulness oracle.

This note takes six results from the AI-safety reading list and ports each one
into `falsify.scale`. Every module runs offline with no API key, has tests in
`tests/test_scale.py`, and is wired into the demo `examples/scale_demo.py`. The
mapping is the point: each paper closes a specific gap in how Popper scales.

| paper | the idea | the gap in Popper it closes | module |
|---|---|---|---|
| Sleeper Agents (Hubinger et al. 2024) | backdoors fire on a rare trigger and survive sampling | uniform Monte-Carlo misses measure-zero spec bugs (the documented 2/178) | `importance.py` |
| Natural Emergent Misalignment from Reward Hacking (MacDiarmid et al. 2025) | models game production rewards in ways nobody enumerated | completeness is only checked against a fixed, hand-written wrong-impl list | `rewardhack.py` |
| Safe RLHF (Dai et al. 2023) | decouple a reward from a cost, optimize under a hard cost constraint | the verdict is one bit, not a tunable training signal | `constrained.py` |
| Scalable AI Safety via Debate (Brown-Cohen, Irving, Piliouras 2023) | a cheap verifier adjudicates powerful adversarial provers | Popper falsifies, but does not localize the missing premise | `debate.py` |
| Bridging Human and LLM Judgments (Maia Polo et al. 2025) | LLM judges drift from ground truth in measurable ways | the LLM-judge baseline is trusted or discarded wholesale, never calibrated | `calibration.py` |
| Model Evaluation for Extreme Risks (Shevlane et al. 2023) | separate capability from propensity, gate on a threshold | the oracle returns a verdict, not a decision about the next stage | `evalcard.py` |

## 1. Sleeper Agents -> adaptive, trigger-aware search

The README is honest about Popper's one real weakness: uniform Monte-Carlo can
miss a bug that hides on a tiny fraction of inputs, and recall only reaches 100%
at 10,000 draws. That is not a quirk. It is the Sleeper Agents result restated
for specs. A backdoor that fires only when the prompt says the year is 2024
survives because uniform sampling almost never hits the trigger; a faithfulness
bug that fires on 1 input in 10,000 is the same object. Uniform search needs
about `1/p` draws to see a trigger of probability `p`, which is exactly the
`1 - (1 - p)^N` curve in the README's recall table.

The fix is to stop sampling uniformly. Falsification is an optimization problem:
drive the claim's margin (how comfortably the conclusion holds) below zero. The
Cross-Entropy Method turns that into importance sampling steered toward the
low-margin boundary where a counterexample, if one exists, must live. A
`ScoredClaim` is the smooth analogue of a Monte-Carlo `Statement`: a real-valued
`margin` instead of a boolean `claim`, and a deterministic `build` from a latent
point in the unit cube so the search can *move* through input space.

Averaged over 12 seeds at a 20,000-draw budget (`results/scale_sleeper.json`):

| trigger probability | uniform mean draws | adaptive mean draws | speedup |
|---|---|---|---|
| 0.05  | 16    | 15  | 1.1x |
| 0.01  | 70    | 21  | 3.4x |
| 0.002 | 364   | 22  | 16.7x |
| 0.0005 | 1,902 | 22  | 87.4x |
| 0.0001 | 7,237 | 22  | 327.7x |
| 5-D conjunctive needle (volume 3e-4) | 3,132 | 523 | 6.0x |

The rarer the bug, the larger the win, because adaptive draws cost stays roughly
flat (~22) while uniform cost grows like `1/p`. The faithful twin is never
falsely flagged by either method. This is how you raise the oracle's recall on
subtle bugs without paying for it linearly in budget.

## 2. Reward hacking -> active search for a spec-gaming implementation

Popper's offline code-spec oracle already checks completeness, but only against
`task.wrong_impls`, a fixed list authored by hand. That is precisely the part a
real adversary ignores: the dangerous hack is the one you did not enumerate. The
reward-hacking paper shows a model in a real RL environment finding exactly those
un-enumerated shortcuts and generalizing them to worse behaviour.

`rewardhack.py` turns completeness into an active search. It synthesizes a family
of cheap candidate implementations (constant answers lifted from the reference's
own outputs, identity and structural mutants, clamps and shifts) and looks for
any candidate the spec *accepts* while it *disagrees with the reference*. The
reported `hacking_margin = acceptance - agreement` is the free reward an
optimizer would collect for being wrong. On the fixtures it independently
rediscovers the vacuity of the length-only sort spec (a length-preserving
constant collects full reward) and the looseness of the lower-bound max spec.

## 3. Safe RLHF -> a constrained faithfulness score

Safe RLHF's one move is to refuse a single scalar reward. It splits preference
into a reward (helpfulness) and a separate cost (harmlessness), and optimizes
`max reward s.t. cost <= d` with an adapting Lagrangian. Popper's two failure
verdicts are exactly those axes:

- UNSOUND = the spec rejects the correct answer = a reward failure (not helpful).
- INCOMPLETE / VACUOUS = the spec accepts a wrong answer = a cost failure (unsafe).

`constrained.py` scores a spec that way. `reward` is the fraction of correct
outputs accepted (want 1.0); `cost` is the fraction of wrong outputs accepted
(want 0.0); the objective is `reward - lambda * cost`, and a spec is safe only if
`cost <= threshold`. The value over a one-bit verdict is that this is a smooth,
signed reward, so the repair loop (and, on the live path, an RL fine-tune) gets a
gradient instead of a yes/no. That is the concrete form of the README's claim
that "the counterexample doubles as a clean RL reward".

## 4. Scalable debate -> recover the missing premise

Doubly-efficient debate is the theory under Popper's whole pitch: a cheap
verifier can correctly adjudicate far more powerful provers as long as the provers
argue against each other and the verifier only checks short steps. `debate.py`
stages that explicitly. A Falsifier produces a counterexample to the statement as
written; a Defender answers with a rescue hypothesis (the minimal premise that
would exclude it); the verifier adjudicates by re-running the search on the
restricted space the premise defines. If the Falsifier still breaks it, the
premise was a bluff; if it cannot, the premise is the genuine missing hypothesis.

On Gibbs' inequality stated for an unnormalized `q`, the verifier rejects a decoy
premise (`q[0]` capped) because the claim is still falsifiable under it, then
accepts `sum q = 1` because the restricted search cannot break it. The output is
not just FALSIFIED but the recovered premise, which is the actionable thing a
prover or a human needs: "false as written; add this hypothesis and it holds".

## 5. Bridge -> calibrate the LLM judge instead of trusting or discarding it

The benchmark contrasts Popper (F1 0.99, a witness every time) with an LLM judge
that "guesses, no execution". Bridge shows the better move is neither to trust nor
to discard the judge but to *calibrate* it against ground truth. Popper ships that
ground truth: an executable verdict with a witness.

`calibration.py` treats the oracle's verdict as the anchor and measures how a
judge deviates (agreement, Cohen's kappa, a flag-rate bias, a Brier score), then
`ensemble_verdict` applies the correction online: an executable counterexample is
incontrovertible and wins outright, the judge is consulted only where the oracle
is silent, and its lone flags are discounted by the bias we measured. The judge
stays useful for the semantic cases the oracle cannot reach without being trusted
where it is known to drift. (The demo uses a synthetic judge with a declared bias
so the math runs with no API key; it is labelled synthetic, not a stand-in for a
real model.)

## 6. Model evaluation -> a risk card and a gate

An evaluation is only useful if it drives a decision. Model-Eval-for-extreme-risks
separates a capability axis from a propensity axis and gates on a threshold.
Popper sits in exactly that governance slot: it is the screen in front of an
expensive prover, so its output should be a graded card and a gate, not a lone
verdict. `evalcard.py` composes the other modules: capability is the Safe-RLHF
reward (does the spec pin the right answer); propensity is the cost and the
reward-hack margin (will a wrong answer slip through). The two yield a risk in
`[0,1]` and a decision:

- PROVE: low risk, send it to the expensive prover.
- REPAIR: a recoverable fault, run the counterexample-guided loop first.
- REJECT: vacuous or unsound, do not spend proof compute at all.

That is the concrete shape of "protect the expensive compute": a thresholded
decision with the witness attached, instead of a guess.

## How this answers "how would you scale Popper"

Three axes, each now backed by running code rather than a slide:

1. **Scale recall without scaling budget.** Replace uniform Monte-Carlo with
   margin-guided adaptive search (module 1). Rare-trigger bugs that cost the
   oracle thousands of draws now cost tens. This is the single highest-leverage
   change and it is measured, not asserted.
2. **Scale the adversary, not just the test set.** Stop enumerating wrong
   implementations by hand and search for them (module 2), exactly as a
   reward-hacking optimizer would. Completeness becomes an active game.
3. **Scale the interface to the rest of the stack.** A one-bit verdict does not
   compose. A reward/cost score (module 3) feeds an RL repair loop; a debate
   transcript (module 4) localizes the fix; a calibrated ensemble (module 5)
   makes a noisy LLM judge safely useful; a risk card (module 6) turns all of it
   into a PROVE / REPAIR / REJECT gate in front of AxiomProver.

Beyond what is implemented here, the same principles point at the live path:
drive the adaptive search through AXLE's Lean probes instead of the offline
margin, run the debate with two LLM provers and Popper as the executable
verifier, and use the reward/cost score as the actual objective for an RL
fine-tune of the spec writer. Each is a direct extension of a module that already
runs.

Reproduce:

```bash
python examples/scale_demo.py                      # all six, offline, no key
python examples/scale_demo.py --markdown           # the same as a report
python -m unittest tests.test_scale -v             # the properties above, pinned
```

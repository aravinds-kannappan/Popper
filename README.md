# Popper

**Falsify the spec, then verify the proof.**

> **Popper** is the project (the system in this repo). **`falsify`** is the Python
> package that implements it. *"Is Popper a package or the thing?"* — Popper is the
> thing; `falsify` is our code for it.

A Lean checker — and Axiom's [AXLE](https://axle.axiommath.ai) — answers one
question: *"is this proof valid?"* It is **silent on whether the statement means
what you intended.** A vacuous or too‑weak specification is trivially provable and
certifies nothing; a too‑strong one rejects correct code. So a fully formal,
100%‑green pipeline can still be **100% wrong** when the *spec* is unfaithful — and
a model that writes both the spec and the code will happily write a spec its own
bugs satisfy.

Popper adds the missing half: an **independent, executable oracle that
*falsifies* specifications** and returns a **counterexample** — the actionable
repair signal (and a clean reward) that proof‑checking alone cannot give — then a
loop that **repairs the statement** until it is faithful.

---

## Table of contents
- [Why this exists](#why-this-exists)
- [Why it differs from an LLM that writes proofs](#why-it-differs-from-an-llm-that-writes-proofs)
- [How it works](#how-it-works)
- [Results](#results)
- [Repository layout](#repository-layout)
- [Quickstart](#quickstart)
- [The numerical oracle (math)](#the-numerical-oracle-math)
- [The live Verina audit (code, over AXLE)](#the-live-verina-audit-code-over-axle)
- [M2 — counterexample-guided repair](#m2--counterexample-guided-repair)
- [Honesty: falsify ≠ certify](#honesty-falsify--certify)
- [Roadmap](#roadmap)
- [License & data](#license--data)

---

## Why this exists

The hard, unsolved problem in verified AI is **not proving** — it's **specifying**.
Provers are getting superhuman (AxiomProver: 120/120 Putnam; 99% on Verina's proof
task vs. a strong general model's ~5%). What remains underwater is **spec
faithfulness**: on the Verina benchmark, the best general model gets ~73% code
correctness but only **~52% specification soundness + completeness**. The spec is
the weak link, and the proof checker can't see it — because the checker validates
the proof *against the spec*, never the spec against intent.

Popper attacks exactly that gap, on the surface Axiom cares about (verified code,
the Verina benchmark), built on the engine Axiom ships (AXLE).

## Why it differs from an LLM that writes proofs

There are three rungs of trust. Most tools sit on rung 1; formal provers moved to
rung 2; **rung 3 is the open one, and it's where Popper lives.**

| Rung | What you get | What still fails *silently* |
|---|---|---|
| **1. LLM writes/explains a proof** | a fluent, plausible artifact | **No ground truth.** Unjustified steps, hidden cases, off‑by‑one, circular reasoning — invisible without an expert reader. RLHF optimizes *plausibility*, not *truth*. |
| **2. LLM + Lean / AXLE** | a deterministic proof that matches the statement | **Spec blindness.** A vacuous spec (`∀ x, True`) proves instantly; "sorted" specified as "same length" is satisfied by the identity function. The checker says nothing. |
| **3. + Popper** | proof matches statement **and** an independent oracle *tried and failed to break the statement* | the honest residual below — but dropped hypotheses, vacuity, wrong direction, too‑strong/too‑weak specs are exactly what it catches, **with a counterexample**. |

A plain LLM has no notion of being wrong. An LLM+Lean knows when a *proof* is
wrong but not when a *statement* is meaningless. Popper is the only rung that
attacks **"is the thing we're proving the right thing?"** — and, unlike a human
reviewer, it's cheap, automatable, and returns a counterexample you can act on.

## How it works

One abstraction (`falsify/core/oracle.py` → `Oracle`, `Verdict`, `OracleResult`),
two falsification engines, plus a repair loop:

```
  intent  ──►  formal statement / spec  ──►  ┌──────── FALSIFICATION ORACLE ────────┐
  (NL theorem | code+description)            │ MATH : Monte-Carlo over sampled       │
                                             │        distributions / processes      │
                                             │ CODE : AXLE check + native_decide on   │
                                             │        Verina expected/unexpected      │
                                             │        witnesses (+ disprove)          │
                                             └───────────────┬───────────────────────┘
                                  survives → PROVE (AXLE)     │ FALSIFIED → counterexample
                                                              ▼
                                                   COUNTEREXAMPLE-GUIDED REPAIR (M2)
                                                   (add the dropped hypothesis;
                                                    strengthen the vacuous spec)  ↺
```

- **Math.** Every inequality/identity has a numerical shadow. A `Statement` carries
  a hypothesis `H` and conclusion `C`; the oracle tests `H → C` over thousands of
  sampled instances. A *dropped hypothesis* or *flipped direction* breaks on some
  draw, yielding the violating instance.
- **Code.** Each Verina task ships correct `expected` and wrong `unexpected`
  outputs. Popper asks AXLE to check `<Name>_postcond <input> <output>` in Lean via
  `native_decide`: **unsound** ⇔ a correct output is rejected; **incomplete** ⇔ a
  wrong output is accepted; **vacuous** ⇔ even garbage is accepted. (AXLE's
  `disprove`, backed by `plausible`, is the same idea for free‑variable statements.)

## Results

All reports are in [`reports/`](./reports); machine‑readable copies (JSON + CSV) in
[`results/`](./results).

**Live Verina spec‑faithfulness audit over AXLE** — real tasks, real Lean:

```
✓ [FAITHFUL    ] verina_basic_1   correct outputs accepted; all wrong outputs rejected
✓ [FAITHFUL    ] verina_basic_2   ...
? [INCONCLUSIVE] verina_basic_3   spec not decidable on some witnesses (no Decidable instance)
... 10 claims | ✓ FAITHFUL 8  ? INCONCLUSIVE 2
```

**Numerical oracle** — faithful statements survive; unfaithful ones are falsified
*with the violating instance*:

```
✗ kl_nonneg_DROPPED_normalization  ⟵ q=[0.78,1.53,1.22] (Σq=3.53≠1) ⇒ Σ pᵢ·log(pᵢ/qᵢ) = -1.15 < 0
✗ data_processing_DROPPED_markov    ⟵ I(X;Z)=0.83 > I(X;Y)=0.05  (Z leaks X directly)
✗ entropy_concave_WRONG_direction   ⟵ H(λp+(1-λ)q)=1.08 > λH(p)+(1-λ)H(q)=1.06
```

**M2 repair** — every unfaithful spec driven to FAITHFUL by its counterexample:

```
✓ sort_by_length        ✗VACUOUS    → ✓FAITHFUL   (length-only spec → add sortedness ∧ permutation)
✓ max_lower_bound_only  ✗INCOMPLETE → ✓FAITHFUL   (out≥a∧out≥b → also require out ∈ {a,b})
✓ abs_strictly_positive ✗UNSOUND    → ✓FAITHFUL   (out>0 rejects abs(0)=0 → relax to ≥)
```

## Repository layout

Code is grouped by component (folder → role; milestone in parentheses):

```
falsify/             the implementation package
  core/        shared spine: Verdict · Oracle · audit/report
  montecarlo/  (M1) numerical falsification of math statements
  speccheck/   (M1) offline code-spec oracle + task model + fixtures + mutation
  live/        live Verina spec-faithfulness audit over AXLE (axle.py + verina.py)
  repair/      (M2) counterexample-guided spec repair
examples/      runnable CLIs (audit_math, audit_verina, verina_live_audit, repair_demo)
tests/         15 unit tests
reports/       rendered audit reports (markdown)
results/       machine-readable results (JSON + CSV)
notebook/      Popper.ipynb — end-to-end walkthrough with outputs
web/           interactive site + Claude agent chatbot (Vercel)
```

## Quickstart

Zero dependencies, Python ≥ 3.10:

```bash
python examples/audit_math.py        # numerical oracle, information-theory ladder
python examples/audit_verina.py      # code-spec oracle, offline fixtures
python examples/repair_demo.py       # M2: counterexample-guided spec repair
python -m unittest discover -s tests -t .   # 15 tests
```

Live audit of the **real 189‑task Verina** benchmark over AXLE:

```bash
pip install axiom-axle                                  # the official AXLE client
export AXLE_API_KEY=...                                 # https://axle.axiommath.ai/app/console
python examples/verina_live_audit.py --limit 8
python examples/verina_live_audit.py --tasks verina_basic_1,verina_advanced_1 --markdown
```

## The numerical oracle (math)

`falsify/montecarlo/numerical.py` ships a curated information‑theory ladder, each
faithful statement paired with the unfaithful formalization Popper is built to
catch:

| statement | faithful form | the trap it catches |
|---|---|---|
| Gibbs / KL ≥ 0 | `KL(p‖q) ≥ 0` for distributions | dropping `Σq = 1` (q not normalized) |
| Data‑processing | `X→Y→Z ⇒ I(X;Z) ≤ I(X;Y)` | dropping the Markov‑chain hypothesis |
| Entropy concavity | `H(λp+(1−λ)q) ≥ λH(p)+(1−λ)H(q)` | flipping the direction (convex) |
| Vacuity trap | claim guarded by a hypothesis nothing satisfies | reported INCONCLUSIVE (possibly vacuous) |

## The live Verina audit (code, over AXLE)

`falsify/live/verina.py` loads real tasks (fetched on demand into a git‑ignored
cache), builds the prelude from `task.lean`, and turns each task's `expected` /
`unexpected` outputs into `native_decide` witnesses checked through the official
`axiom-axle` client (concurrently). Verdicts: **FAITHFUL**, **UNSOUND** (too
strong), **INCOMPLETE** (too weak), **VACUOUS**, **INCONCLUSIVE** (not decidable
on a witness). No mutant generation needed — the wrong outputs are pre‑curated.

This goes beyond a benchmark *score*: it produces counterexamples, and feeds the
repair loop.

## M2 — counterexample-guided repair

`falsify/repair/repair.py`: `repair_loop` re‑audits after each fix until FAITHFUL
or budget. Repairers — `TemplateRepairer` (declarative fixes), `FunctionalSpecRepairer`
(generic fallback: pin output to the reference; always converges), and
`LLMRepairer` (asks a model for a repaired Lean postcondition; the path that
scales to real Verina — needs `ANTHROPIC_API_KEY`).

## Honesty: falsify ≠ certify

**Popper falsifies; it does not certify.** A FAITHFUL verdict means *no
counterexample was found within the search budget* — not a proof of faithfulness
(that's undecidable in general). It catches the dominant real‑world failures
cheaply; Lean/AXLE remains the ground truth for the *proof*. INCONCLUSIVE is
reported honestly when a spec isn't `Decidable` on a witness, rather than guessed.

## Roadmap

- LLM **declarative repair inside the live loop** (swap the repaired postcondition
  into the prelude and re‑audit).
- **Full‑benchmark sweep** across all 189 Verina tasks.
- API‑only **self‑improvement flywheel**: oracle‑reranked best‑of‑n + DPO pairs
  from oracle labels (no GPU).
- The interactive **web demo + Claude agent** in [`web/`](./web).

## License & data

Apache‑2.0 (see [`LICENSE`](./LICENSE)). The Verina benchmark is CC‑BY‑SA‑4.0 and
is **not** vendored here; it is fetched on demand from
[`sunblaze-ucb/verina`](https://github.com/sunblaze-ucb/verina) into a git‑ignored
cache. Built on the open [AXLE](https://github.com/AxiomMath/axiom-lean-engine)
engine and [Mathlib](https://github.com/leanprover-community/mathlib4).

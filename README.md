# Popper

**Falsify the spec, then verify the proof.**

Popper is the project in this repo. `falsify` is the Python package that
implements it. If you are wondering which name to use: Popper is the system,
`falsify` is the code.

A Lean checker, and Axiom's [AXLE](https://axle.axiommath.ai), answers one
question: is this proof valid? It says nothing about whether the statement means
what you intended. A vacuous or too-weak specification is easy to prove and
certifies nothing. A too-strong one rejects correct code. So a fully formal,
all-green pipeline can still be wrong when the spec is unfaithful, and a model
that writes both the spec and the code will happily write a spec that its own
bugs satisfy.

Popper adds the part that is missing: an independent, executable oracle that
tries to break a specification and returns a counterexample when it succeeds.
That counterexample is the thing proof checking alone cannot give you. It tells
you which input breaks the spec, and it doubles as a repair signal and a training
reward. On top of that there is a loop that uses the counterexample to repair the
statement until it holds up.

---

## Contents

- [Why this exists](#why-this-exists)
- [How it differs from a model that writes proofs](#how-it-differs-from-a-model-that-writes-proofs)
- [How it works](#how-it-works)
- [Benchmark](#benchmark)
- [Results](#results)
- [Repository layout](#repository-layout)
- [Quickstart](#quickstart)
- [The numerical oracle (math)](#the-numerical-oracle-math)
- [The live Verina audit (code, over AXLE)](#the-live-verina-audit-code-over-axle)
- [Counterexample-guided repair (M2)](#counterexample-guided-repair-m2)
- [Research write-up](#research-write-up)
- [Honesty: falsify is not certify](#honesty-falsify-is-not-certify)
- [Roadmap](#roadmap)
- [License and data](#license-and-data)

---

## Why this exists

The hard part of verified AI is not proving, it is specifying. Provers are
getting very good. AxiomProver solves 120 of 120 Putnam problems and around 99%
of Verina's proof task, against roughly 5% for a strong general model. What has
not kept pace is spec faithfulness. On the Verina benchmark the best general
model gets about 73% code correctness but only about 52% specification soundness
and completeness. The spec is the weak link, and the proof checker cannot see it,
because the checker validates the proof against the spec and never the spec
against your intent.

Popper goes after that gap, on the surface Axiom cares about (verified code, the
Verina benchmark) and on the engine Axiom ships (AXLE).

## How it differs from a model that writes proofs

There are three rungs of trust. Most tools sit on rung one. Formal provers moved
to rung two. Rung three is the open one, and it is where Popper lives.

| Rung | What you get | What still fails silently |
|---|---|---|
| 1. Model writes or explains a proof | a fluent, plausible artifact | No ground truth. Unjustified steps, hidden cases, off-by-one, circular reasoning, all invisible without an expert reader. |
| 2. Model plus Lean or AXLE | a real proof that matches the statement | Spec blindness. A vacuous spec proves instantly. "Sorted" written as "same length" is satisfied by the identity function. The checker says nothing. |
| 3. Plus Popper | proof matches statement, and an independent oracle tried and failed to break the statement, or broke it and showed you how | the honest residual below, but dropped hypotheses, vacuity, wrong direction, and too-strong or too-weak specs are exactly what it catches, with a counterexample. |

A plain model has no notion of being wrong. A model plus Lean knows when a proof
is wrong but not when a statement is meaningless. Popper is the rung that asks
whether the thing we are proving is the right thing, and unlike a human reviewer
it is cheap, automatable, and hands back a counterexample you can act on.

## How it works

One interface (`falsify/core/oracle.py`, with `Oracle`, `Verdict`, and
`OracleResult`), two engines, and a repair loop:

```
  intent  -->  formal statement / spec  -->  +-------- FALSIFICATION ORACLE --------+
  (theorem in NL | code + description)       | MATH : Monte-Carlo over sampled       |
                                             |        distributions and processes    |
                                             | CODE : AXLE check + native_decide on   |
                                             |        Verina expected/unexpected      |
                                             |        witnesses                       |
                                             +---------------+------------------------+
                          survives -> PROVE (AXLE)           | FALSIFIED -> counterexample
                                                             v
                                            COUNTEREXAMPLE-GUIDED REPAIR (M2)
                                            (add the dropped hypothesis,
                                             strengthen the vacuous spec)  -> re-audit
```

- **Math.** Every inequality or identity has a numerical shadow. A `Statement`
  carries a hypothesis `H` and a conclusion `C`, and the oracle tests `H` implies
  `C` over thousands of sampled instances. A dropped hypothesis or a flipped
  direction breaks on some draw, and that draw is the counterexample.
- **Code.** Each Verina task ships correct `expected` and wrong `unexpected`
  outputs. Popper asks AXLE to check `<Name>_postcond <input> <output>` in Lean
  through `native_decide`. A rejected correct output means the spec is too strong
  (unsound). An accepted wrong output means it is too weak (incomplete). An
  accepted garbage output means it is vacuous.

## Benchmark

The point of the benchmark is to put a number on the claim above: a proof checker
tells you a proof matches a statement, but it cannot tell you the statement is the
right one, and Popper can.

We labelled 38 formal claims as faithful or unfaithful (and recorded the kind of
bug), then ran three judges over the same corpus.

- **math, 24 items**: eleven faithful inequalities and identities, eleven
  unfaithful twins (a dropped hypothesis, a flipped direction, or an over-strong
  claim each), and two vacuity traps. Checked by the Monte-Carlo oracle, which
  runs locally with no API key.
- **code, 4 items**: the offline code-spec fixtures.
- **verina, 10 items**: real Verina tasks audited live over AXLE. These ship as
  faithful, so they measure the false positive rate.

| judge | unfaithful caught | false positives | counterexample yield | F1 |
|---|---|---|---|---|
| Popper | 14/14 (100%) | 0/22 (0%) | 100% | 1.00 |
| Proof checker (AXLE/Lean) | 0/14 (0%) | 0/22 (0%) | 0% | 0.00 |
| LLM judge | runnable live | runnable live | 0% (no witness) | runnable live |

The proof checker scores zero recall however strong the prover is, because
flagging an unfaithful spec is not something a proof checker does. The LLM judge
can guess, but it never returns an executable witness. For a published reference
point, the Verina paper reports the best general model near 52% combined spec
soundness and completeness. Run it yourself:

```bash
python examples/run_benchmark.py          # Popper and the proof-checker baseline, offline
python examples/run_benchmark.py --llm    # add a live LLM judge (needs ANTHROPIC_API_KEY)
```

Outputs go to `results/benchmark.json`, `results/benchmark.csv`, and
[`reports/benchmark.md`](./reports/benchmark.md).

## Results

All reports are in [`reports/`](./reports). Machine-readable copies (JSON and CSV)
are in [`results/`](./results).

Live Verina spec-faithfulness audit over AXLE, real tasks and real Lean:

```
✓ [FAITHFUL    ] verina_basic_1   correct outputs accepted; all wrong outputs rejected
✓ [FAITHFUL    ] verina_basic_2   ...
? [INCONCLUSIVE] verina_basic_3   spec not decidable on some witnesses (no Decidable instance)
... 10 claims | FAITHFUL 8  INCONCLUSIVE 2
```

Numerical oracle, faithful statements survive and unfaithful ones are falsified
with the violating instance:

```
✗ kl_nonneg_DROPPED_normalization   q=[0.78,1.53,1.22] (Sum q=3.53 != 1) => Sum p_i log(p_i/q_i) = -1.15 < 0
✗ data_processing_DROPPED_markov    I(X;Z)=0.83 > I(X;Y)=0.05  (Z leaks X directly)
✗ entropy_concave_WRONG_direction   H(lam p + (1-lam) q)=1.08 > lam H(p)+(1-lam) H(q)=1.06
```

M2 repair, every unfaithful spec driven to FAITHFUL by its counterexample:

```
✓ sort_by_length        VACUOUS    -> FAITHFUL   (length-only spec, add sortedness and permutation)
✓ max_lower_bound_only  INCOMPLETE -> FAITHFUL   (out>=a and out>=b, also require out in {a,b})
✓ abs_strictly_positive UNSOUND    -> FAITHFUL   (out>0 rejects abs(0)=0, relax to >=)
```

## Repository layout

Code is grouped by component (folder, then role, with the milestone in parentheses):

```
falsify/             the implementation package
  core/        shared spine: Verdict, Oracle, audit and report
  montecarlo/  (M1) numerical falsification of math statements
  speccheck/   (M1) offline code-spec oracle, task model, fixtures, mutation
  live/        live Verina spec-faithfulness audit over AXLE (axle.py + verina.py)
  repair/      (M2) counterexample-guided spec repair
  bench/       the spec-faithfulness benchmark (corpus, judges, metrics, runner)
examples/      runnable CLIs (audit_math, audit_verina, verina_live_audit, repair_demo, run_benchmark)
tests/         unit tests
reports/       rendered reports, including benchmark.md and research.md
results/        machine-readable results (JSON and CSV)
notebook/      Popper.ipynb, an end-to-end walkthrough with outputs
web/           the interactive site: overview, benchmark, audits, research, and a Claude agent
```

## Quickstart

No third-party dependencies for the core, Python 3.10 or newer:

```bash
python examples/audit_math.py        # numerical oracle, information-theory ladder
python examples/audit_verina.py      # code-spec oracle, offline fixtures
python examples/repair_demo.py       # M2: counterexample-guided spec repair
python examples/run_benchmark.py     # the benchmark (Popper vs the proof-checker baseline)
python -m unittest discover -s tests -t .   # the test suite
```

Live audit of the real 189-task Verina benchmark over AXLE:

```bash
pip install axiom-axle                                  # the official AXLE client
export AXLE_API_KEY=...                                 # https://axle.axiommath.ai/app/console
python examples/verina_live_audit.py --limit 8
python examples/verina_live_audit.py --tasks verina_basic_1,verina_advanced_1 --markdown
```

## The numerical oracle (math)

`falsify/montecarlo/numerical.py` ships a curated information-theory ladder, each
faithful statement paired with the unfaithful formalization Popper is built to
catch. `falsify/bench/corpus.py` extends it with more families (Cauchy-Schwarz,
AM-GM, the triangle inequality, entropy subadditivity, mutual information, the
cross entropy bound, Jensen for the logarithm, variance).

| statement | faithful form | the trap it catches |
|---|---|---|
| Gibbs / KL >= 0 | `KL(p, q) >= 0` for distributions | dropping `Sum q = 1` (q not normalized) |
| Data processing | `X -> Y -> Z implies I(X;Z) <= I(X;Y)` | dropping the Markov-chain hypothesis |
| Entropy concavity | `H(lam p + (1-lam) q) >= lam H(p) + (1-lam) H(q)` | flipping the direction (convex) |
| Vacuity trap | claim guarded by a hypothesis nothing satisfies | reported INCONCLUSIVE (possibly vacuous) |

## The live Verina audit (code, over AXLE)

`falsify/live/verina.py` loads real tasks (fetched on demand into a git-ignored
cache), builds the prelude from `task.lean`, and turns each task's `expected` and
`unexpected` outputs into `native_decide` witnesses checked through the official
`axiom-axle` client, concurrently. Verdicts: FAITHFUL, UNSOUND (too strong),
INCOMPLETE (too weak), VACUOUS, and INCONCLUSIVE (not decidable on a witness). No
mutant generation is needed because the wrong outputs are already curated. This is
more than a score: it produces counterexamples and feeds the repair loop.

## Counterexample-guided repair (M2)

`falsify/repair/repair.py`: `repair_loop` re-audits after each fix until FAITHFUL
or the budget runs out. The repairers are `TemplateRepairer` (declarative fixes),
`FunctionalSpecRepairer` (a generic fallback that pins the output to the
reference and always converges), and `LLMRepairer` (asks a model for a repaired
Lean postcondition, the path that scales to real Verina, needs `ANTHROPIC_API_KEY`).

## Research write-up

[`reports/research.md`](./reports/research.md) is a short report: the problem,
where Popper sits, the method, the benchmark, what Popper adds to the field, the
limitations, and the next steps. It is also on the Research tab of the site.

## Honesty: falsify is not certify

Popper falsifies; it does not certify. A FAITHFUL verdict means no counterexample
was found within the search budget, not a proof of faithfulness, which is
undecidable in general. It catches the common real-world failures cheaply. Lean
and AXLE remain the ground truth for the proof itself. When a spec is not
`Decidable` on a witness, Popper reports INCONCLUSIVE rather than guessing.

## Roadmap

- Run the declarative repair loop inside the live AXLE path: swap the repaired
  postcondition back into the prelude and re-audit.
- Sweep all 189 Verina tasks rather than a sample.
- Build the API-only self-improvement loop: rank best-of-n generations by the
  oracle and form preference pairs from oracle labels, no GPU needed.
- Keep growing the benchmark corpus into measure theory and linear algebra.

## License and data

Apache-2.0 (see [`LICENSE`](./LICENSE)). The Verina benchmark is CC-BY-SA-4.0 and
is not vendored here; it is fetched on demand from
[`sunblaze-ucb/verina`](https://github.com/sunblaze-ucb/verina) into a git-ignored
cache. Built on the open [AXLE](https://github.com/AxiomMath/axiom-lean-engine)
engine and [Mathlib](https://github.com/leanprover-community/mathlib4).

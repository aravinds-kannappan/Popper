# Popper

**A semantic-fault-tolerant pre-flight layer for formal provers. Break the statement before you pay to prove it.**

Popper is the system. [`falsify`](./falsify) is the Python package that runs it.
Popper sits in front of a prover like Axiom's [AXLE](https://axle.axiommath.ai) and
AxiomProver and answers the one question those engines structurally cannot: *is this
even the right statement to prove, and did the author write something a machine can read
at all?*

---

## TL;DR for the engineer evaluating this

- **The problem.** Formal provers are brittle at the front door. The moment a user hands
  them flawed, typo-heavy Lean or references a Mathlib term that does not exist, an engine
  like AxiomProver dies at the type-checking phase. It never sees the *mathematical
  intent*; it sees a parse failure and stops.
- **What Popper does.** Popper is a buffer in front of the prover. It reads between the
  lines to deduce what the user is *gesturing at* mathematically, intercepts the syntax
  errors before they reach the prover, and uses AXLE's substrate to run rapid-fire (~30
  ms/probe) adversarial fuzzing against the statement. This is its
  **semantic-fault-tolerance** layer.
- **The payoff.** It catches spec-faithfulness failures and weak premises, surfacing the
  actual matrix or graph counterexample that breaks the claim, *before* a single cycle of
  expensive, long-running, multi-agent proof search is spent on a theorem that is
  unprovable or vacuous.

---

## The problem: provers are blind in two directions

A modern prover is a verifier. Hand it a statement and a proof and it tells you, for
certain, whether the proof is valid. That is a strong guarantee, and it has two blind
spots that compound each other.

**1. It is blind to malformed intent.** The verifier only runs once the statement
type-checks. Real users do not write clean Lean. They write typos, they invent Mathlib
lemmas that were renamed three releases ago, they get an implicit argument wrong.
AxiomProver does not degrade gracefully on this input; it crashes at the
elaboration/type-checking phase and returns nothing useful. The mathematical idea the
user was reaching for is lost in a parse error.

**2. It is blind to the statement's faithfulness.** Even when the statement compiles, the
prover only ever checks the *proof* against the *statement*, never the statement against
the author's actual intent. So a statement that is too loose (accepts wrong answers), too
tight (rejects right ones), or vacuous (`∀ x, true`) still gets a clean, certified proof.
You walk away believing you verified something. You did not.

This is not a corner case. On Verina, a benchmark of code-with-specs, the best general
model writes correct *code* about 73% of the time but writes *specs* that are both sound
and complete only about 52% of the time. The spec, not the proof, is where the errors
live, and the verifier cannot see them.

## The solution: Popper as a semantic-fault-tolerant screen

Popper does not prove. It *breaks*. It sits in front of the prover as a cheap, fast
screen and does three things the prover cannot:

1. **Reads intent through noise.** Instead of rejecting malformed Lean, Popper's agent
   layer deduces what the user is gesturing at mathematically, recovering the claim behind
   the typo, the renamed Mathlib term, the off-by-one in an implicit argument, and
   reconstructs a checkable statement from it.
2. **Intercepts syntax faults before the prover.** Parse and elaboration failures are
   caught and repaired at the buffer, so they never reach (and never crash) the expensive
   multi-agent proof loop.
3. **Fuzzes the statement adversarially on AXLE's substrate.** Once there is a checkable
   statement, Popper runs rapid-fire adversarial probes (~30 ms each) to try to *falsify*
   it, driving thousands of Monte-Carlo draws for math, or evaluating the spec against
   known-good and known-bad witnesses for code. When it breaks the statement, it returns
   the concrete **counterexample**: the exact matrix, vector, or graph that exposes the
   weak premise.

The verdict vocabulary is deliberately small and honest: `FAITHFUL` (could not break it
within budget, *not* a certificate), `FALSIFIED`, `UNSOUND` (spec too strong),
`INCOMPLETE` (spec too weak), `VACUOUS` (spec constrains nothing), `INCONCLUSIVE`
(insufficient signal, reported rather than guessed).

## The value: protect the expensive compute

Proving is expensive. Multi-agent proof search burns a large, long-running budget.
Breaking is cheap. It is wasteful, and it is the failure mode in production today, to
point the expensive tool at a statement the cheap tool can already show is wrong.

- **Vacuous / too-weak specs prove easily and certify nothing.** AxiomProver would return
  a clean proof of `∀ x, true` or of "sorted means same length." Popper catches it before
  any proof compute is spent.
- **Wrong / too-strong specs are unprovable, and the prover grinds.** AxiomProver can
  exhaust a large search budget failing to prove something false because the *spec* has a
  bug. Popper finds the breaking input in milliseconds and says "fix the spec."
- **The counterexample is the repair signal.** Popper breaks the spec, a model (or a
  human) fixes it using the witness, and *then* AxiomProver proves the repaired statement.
  The counterexample doubles as a clean RL reward for the repair loop.

| | AxiomProver / AXLE | Popper |
|---|---|---|
| Question | Can this statement be proved? | Is this the right, well-formed statement to prove? |
| Method | Multi-agent search for a Lean proof | Recover intent, then adversarially fuzz the statement |
| Behavior on malformed input | Crashes at type-checking | Reads through it, repairs, continues |
| Output | A proof, or failure | A counterexample, or "no break found" |
| Cost | High, long-running | Low, ~30 ms/probe |
| Role | The verifier | The semantic-fault-tolerant screen in front of it |

The two are complementary. Popper keeps the prover's compute on statements that are
well-formed and worth proving; AxiomProver delivers the real proof once the statement
holds up.

---

## System design

Popper is built around one principle: **a cheap, executable falsification signal is worth
more than an expensive certificate when the input is untrusted.** Everything flows from
that.

```
        ┌──────────────────────── Popper ────────────────────────┐
 user   │                                                          │
 input  │   ┌────────────┐   ┌──────────────┐   ┌──────────────┐  │
 ─────► │   │ intent     │──►│ statement     │──►│ falsification │  │──► verdict
 (noisy │   │ recovery   │   │ reconstruction│   │ oracle        │  │   + counterexample
 Lean / │   │ (agent)    │   │ (checkable)   │   │ (engines)     │  │
 NL /   │   └────────────┘   └──────────────┘   └──────┬───────┘  │
 spec)  │                                              │          │
        │                                       ┌──────▼───────┐  │
        │                                       │ AXLE substrate│ │
        │                                       │ (~30ms probes)│ │
        │                                       └──────────────┘  │
        └──────────────────────────────────────────────────────────┘
                                                       │ FAITHFUL & well-formed
                                                       ▼
                                          ┌────────────────────────┐
                                          │ AxiomProver (expensive  │
                                          │ multi-agent proof loop) │
                                          └────────────────────────┘
```

The contract between layers is a single interface, `falsify/core/oracle.py`: an `Oracle`
takes a formalized claim and returns a `Verdict` plus an optional counterexample. Two
engines implement that interface, so the same audit, repair, and reporting machinery works
across both math and code surfaces.

## Architecture

There is one common interface and two falsification engines behind it.

- **`core/`** is the substrate. `oracle.py` defines the `Verdict` enum and the abstract
  `Oracle` (the only contract every engine honors). `audit.py` is the shared run/report
  machinery so a new engine inherits auditing for free.

- **`montecarlo/`** is the numerical engine (math). Most inequalities and identities are
  checkable with numbers. A statement carries an assumption and a conclusion; the engine
  draws thousands of random cases and checks the conclusion holds whenever the assumption
  does. Drop an assumption or flip a direction and some random draw breaks it, and that
  draw *is* the counterexample (e.g. a `q` with `∑q ≠ 1` driving KL divergence negative,
  or a non-Markov triple where `I(X;Z) > I(X;Y)`). Runs locally; **no prover, no API
  key.**

- **`speccheck/`** is the offline code-spec engine. A task model (`task.py`), fixtures
  (`fixtures.py`), and a mutation/fuzzing layer (`mutation.py`) that generates
  plausible-but-wrong implementations and adversarial inputs. The spec is evaluated against
  a correct reference and several wrong ones: a rejected correct answer ⇒ `UNSOUND`; an
  accepted wrong answer ⇒ `INCOMPLETE`; an accepted nonsense answer ⇒ `VACUOUS`.

- **`live/`** is the AXLE substrate. `axle.py` is a thin synchronous handle over the
  official async `axle` client (`pip install axiom-axle`); `verina.py` drives the real
  189-task Verina benchmark against live Lean. This is where the rapid-fire `check` /
  `disprove` probes run.

- **`repair/`** is the counterexample-driven repair loop (M2). Takes a falsifying witness,
  adjusts the statement, and re-checks until it holds up or the budget runs out. This is
  the "falsify the spec, then verify the proof" loop in code.

- **`bench/`** is the benchmark harness. `corpus.py` (the labelled set), `judges.py`
  (Popper, the proof-checker baseline, the LLM judge), `metrics.py`, and `run.py`.

- **`web/`** is the site. A live Popper agent (Opus + AXLE tools), the offline oracle
  benchmark with charts, the audit dashboard, and the research write-up. The agent's
  `check`/`disprove` tools call the same AXLE substrate; keys are server-side only.

## Repository structure

```
falsify/             the implementation package
  core/        shared substrate: Verdict, Oracle, audit + report machinery
  montecarlo/  (M1) numerical engine for math statements
  speccheck/   (M1) offline code-spec engine: task model, fixtures, mutation/fuzz
  live/        the live AXLE substrate (axle.py) + Verina driver (verina.py)
  repair/      (M2) counterexample-driven repair loop
  bench/       benchmark: corpus, judges, metrics, runner
examples/      runnable scripts (audit_math, audit_verina, verina_live_audit, repair_demo, run_benchmark)
tests/         unit tests
reports/       written reports, including benchmark.md and research.md
results/       machine-readable results (JSON and CSV)
notebook/      Popper.ipynb, a walkthrough with outputs
web/           the Next.js site: live agent, benchmark + charts, audits, research
```

## The benchmark

346 statements labelled by hand (faithful or unfaithful, and if unfaithful, the bug
kind), three checkers run over the same set.

- **math, 332 items**: families of inequalities (Cauchy–Schwarz, AM–GM, triangle,
  information-theoretic, and more) generated across sizes, with faithful and broken
  variants side by side, plus a batch of "subtle" bugs that fail on a tiny fraction of
  inputs. Run for real by the local Monte-Carlo engine; no API key.
- **code, 4 items**: offline code-spec fixtures.
- **verina, 10 items**: real Verina tasks, verdicts replayed from a live AXLE run; meant
  to be faithful, so they measure false-alarm rate.

| checker | unfaithful caught | false alarms | gives a counterexample | F1 |
|---|---|---|---|---|
| **Popper** | 176/178 (99%) | 0/165 (0%) | yes, every time | 0.99 |
| Proof checker (AXLE/Lean) | 0/178 (0%) | 0/165 (0%) | no | 0.00 |
| LLM judge (model reads spec, guesses) | runnable live | runnable live | no | runnable live |

The two specs Popper misses fail on ~1 input in 10,000; at a 2,000-draw budget the sampler
sometimes does not hit the bad input. That is an honest, documented limit, and it closes
with more draws:

| draws/statement | math recall | math F1 | subtle bugs caught | subtle-bug F1 |
|---|---|---|---|---|
| 100 | 98% | 0.99 | 6/10 (60%) | 0.75 |
| 500 | 99% | 0.99 | 8/10 (80%) | 0.89 |
| 2,000 | 99% | 0.99 | 8/10 (80%) | 0.89 |
| 10,000 | 100% | 1.00 | 10/10 (100%) | 1.00 |
| 50,000 | 100% | 1.00 | 10/10 (100%) | 1.00 |

The proof checker scores zero at every budget, by design, not weakness. Flagging a bad
spec is simply not a thing a proof checker does, because every spec in the set is valid as
far as the *proof* is concerned.

```bash
python examples/run_benchmark.py          # Popper vs proof-checker baseline, offline
python examples/run_benchmark.py --llm    # add a live LLM judge (needs ANTHROPIC_API_KEY)
```

Outputs: `results/benchmark.json`, `results/benchmark.csv`,
[`reports/benchmark.md`](./reports/benchmark.md). The site charts the same data.

## Tradeoffs

Engineering Popper meant choosing falsification over certification on purpose. The costs
of that choice, stated plainly:

- **Falsification is sound but not complete.** A `FAITHFUL` verdict means Popper could not
  find a counterexample within budget, *not* that none exists. Proving no counterexample
  exists is undecidable in general, so Popper never claims it. The value is asymmetric and
  that is fine: a cheap "this is definitely broken, here's why" is worth far more than an
  expensive "probably ok."
- **Sampling can miss measure-zero bugs.** Random draws can miss a bug that hides on a
  tiny set of inputs (the 2 of 178 above). The mitigation is budget: recall climbs to 100%
  with more draws, and the bugs that matter most in practice (dropped assumptions, flipped
  directions) fail on a large fraction of inputs and fall out immediately.
- **Intent recovery is best-effort.** Reading through malformed Lean is heuristic and
  agent-driven; it will not always reconstruct the user's idea. But the failure mode is
  graceful (`INCONCLUSIVE`, hand back to the user) rather than a hard crash, which is
  strictly better than the prover's parse-error wall.
- **Cheap probes, not formal models.** The ~30 ms adversarial probes are executable
  checks, not symbolic reasoning. They trade theoretical guarantees for throughput, which
  is exactly the right trade for a *screen* whose job is to protect the expensive layer
  behind it.
- **Honesty over coverage.** When a spec cannot be decided on a test case, Popper reports
  `INCONCLUSIVE` instead of guessing. This lowers headline "accuracy" versus a judge that
  always answers, and it is the correct behavior for a tool feeding a formal pipeline.

## Other results

All reports in [`reports/`](./reports); machine-readable copies in [`results/`](./results).

Live Verina spec check against AXLE (real tasks, real Lean):

```
[FAITHFUL    ] verina_basic_1   correct answers accepted; every wrong answer rejected
[INCONCLUSIVE] verina_basic_3   spec could not be decided on one of the test cases
... 10 claims | FAITHFUL 8  INCONCLUSIVE 2
```

Math engine (faithful statements survive; broken ones yield a counterexample):

```
kl_nonneg_DROPPED_norm    sum q = 3.53 (not 1) => KL = -1.15 < 0
dpi_DROPPED_markov        I(X;Z) = 0.83 > I(X;Y) = 0.05  (Z leaks X directly)
entropy_convex_WRONG      H(mix) = 1.08 > the average 1.06  (entropy is concave, not convex)
```

Repair loop (every broken spec driven back to faithful by its own counterexample):

```
sort_by_length        VACUOUS    -> FAITHFUL   (length-only spec, add sortedness and permutation)
max_lower_bound_only  INCOMPLETE -> FAITHFUL   (out >= a and out >= b, also require out in {a, b})
abs_strictly_positive UNSOUND    -> FAITHFUL   (out > 0 rejects abs(0) = 0, relax to >=)
```

## Quickstart

No third-party packages for the core, Python 3.10+:

```bash
python examples/audit_math.py        # math engine on an information-theory ladder
python examples/audit_verina.py      # code-spec engine on offline fixtures
python examples/repair_demo.py       # the repair loop
python examples/run_benchmark.py     # the benchmark (Popper vs proof-checker baseline)
python -m unittest discover -s tests -t .   # the tests
```

Live check of the real 189-task Verina benchmark against AXLE:

```bash
pip install axiom-axle                                  # the official AXLE client
export AXLE_API_KEY=...                                 # https://axle.axiommath.ai/app/console
python examples/verina_live_audit.py --limit 8
```

## The website and its API keys

The site in [`web/`](./web) has the Live demo, an Overview, the offline oracle benchmark
with charts, the audit results, and the Research write-up. The local math benchmark needs
no keys; the deployed site needs two (set as Vercel env vars):

- `ANTHROPIC_API_KEY` powers the Claude agent (`web/app/api/chat/route.ts`) and the live
  benchmark (`web/app/api/benchmark/route.ts`).
- `AXLE_API_KEY` powers the agent's live `disprove`/`check` tools against the Axiom Lean
  Engine (`web/app/lib/axle.ts`).

Both are read server-side only and never sent to the browser. The full list (including
optional `ANTHROPIC_MODEL`, `AXLE_ENVIRONMENT`, `AXLE_BASE_URL`) is in
[`web/.env.example`](./web/.env.example).

## License and data

Apache-2.0 (see [`LICENSE`](./LICENSE)). The Verina benchmark is CC-BY-SA-4.0 and is not
stored here; it is fetched on demand from
[`sunblaze-ucb/verina`](https://github.com/sunblaze-ucb/verina) into a git-ignored cache.
Built on the open [AXLE](https://github.com/AxiomMath/axiom-lean-engine) engine and
[Mathlib](https://github.com/leanprover-community/mathlib4).

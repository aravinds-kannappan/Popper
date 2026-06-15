# Popper

**Check that the statement is right, then prove it.**

Popper is the project in this repo. `falsify` is the Python package that runs it.
Popper is the system; `falsify` is the code.

## What Popper does, in one paragraph

When you prove something with a computer, you write down a statement (a "spec",
short for specification, which is just a precise description of what the code or
the math is supposed to do) and then you prove that your work matches that
statement. The catch is that the statement itself might be wrong. It might be too
loose, so it accepts wrong answers. It might be too tight, so it rejects right
ones. It might say nothing at all, so everything passes. In every one of those
cases the proof still goes through and the whole thing looks correct, and it
isn't. Popper is a small tool that goes after the statement directly. It tries to
break the statement by finding an input that makes it fail, and when it finds one
it hands you that input. I call this input a counterexample: a concrete case that
shows the statement is wrong. If Popper cannot break the statement after a lot of
trying, that is some evidence the statement is fine, but it is not a proof, and I
am careful to say so.

## Why I built it

I kept seeing the same gap. The tools that prove things have gotten very good. A
prover like Axiom's [AXLE](https://axle.axiommath.ai) can take a statement and a
proof and tell you, for certain, whether the proof is valid. What it cannot tell
you is whether the statement is the one you meant. It only ever checks the proof
against the statement, never the statement against your actual intent. So if the
statement is wrong, the prover happily certifies a proof of the wrong thing and
reports success.

This is not a small corner case. On Verina, a benchmark of code-with-specs, the
best general model writes code that is correct about 73% of the time but writes
specs that are both sound and complete only about 52% of the time. ("Sound" here
means the spec does not reject a correct answer; "complete" means it does not
accept a wrong one.) In other words the spec, not the proof, is where things go
wrong, and the prover is blind to it. That blind spot is the whole reason Popper
exists.

## How Popper compares to the tools people already use

I find it easiest to think about three levels of trust, and what each one still
misses.

- **A model writes or explains a proof.** You get something that reads well, and
  you get no guarantee. A wrong step, a skipped case, or an off-by-one error is
  invisible unless an expert reads it carefully. Popper is not trying to replace
  this; it is pointing out that fluent text is not the same as a correct result.
- **A model plus a prover like Lean or AXLE.** Now you get a real proof that
  matches the statement, which is a big step up. But you are still trusting the
  statement. A statement that says nothing (for example, "for all x, true") proves
  instantly. A statement that defines "sorted" as "same length as the input" is
  satisfied by code that does nothing at all. The prover will not complain, because
  there is nothing wrong with the proof. The thing being proved is the problem.
- **A model plus a prover plus Popper.** The proof matches the statement, and on
  top of that an independent check has actively tried to break the statement. If
  it could not, you have more reason to trust the spec. If it could, you get the
  exact input that breaks it, which tells you what to fix.

What Popper adds that the others do not have: it looks at the spec, not the proof,
and when it finds a problem it gives you a concrete counterexample instead of a
score or a shrug.

## How it works

There is one common interface (`falsify/core/oracle.py`) and two engines behind
it. An engine takes a statement, tries to break it, and reports a verdict:
FAITHFUL (could not break it within the budget), FALSIFIED, UNSOUND, INCOMPLETE,
VACUOUS, or INCONCLUSIVE (not enough signal to say, reported honestly rather than
guessed).

- **Math.** Most inequalities and identities can be checked with numbers. The
  statement carries an assumption and a conclusion, and the engine samples
  thousands of random cases and checks whether the conclusion holds whenever the
  assumption does. This is a Monte-Carlo check, which is just a fancy way of
  saying "try a lot of random inputs and see if anything breaks." If the statement
  dropped an assumption or flipped a direction, some random case breaks it, and
  that case is the counterexample. This engine runs locally with no prover and no
  API key.
- **Code.** Each Verina task comes with a correct answer and several wrong
  answers. Popper asks AXLE to evaluate the spec on each of them. If a correct
  answer is rejected, the spec is too tight (unsound). If a wrong answer is
  accepted, the spec is too loose (incomplete). If even nonsense is accepted, the
  spec is empty (vacuous).

A counterexample is more useful than a pass/fail bit. It tells you which input
breaks the spec, so it doubles as a repair hint. Popper's repair loop (milestone
M2) takes the counterexample, adjusts the statement, and checks again, until the
statement holds up or it runs out of budget.

## The benchmark

I wanted a number, not just an argument. So I built a benchmark: a set of 346
statements where I know the right answer ahead of time (faithful or unfaithful,
and if unfaithful, what kind of bug it is). Then I run three checkers over the
same set and see how many of the unfaithful ones each catches.

- **math, 332 items.** Many families of inequalities (Cauchy-Schwarz, AM-GM, the
  triangle inequality, several from information theory, and more), each generated
  across a range of sizes, with faithful versions and broken versions side by
  side, plus a batch of "subtle" bugs that only fail on a tiny fraction of inputs.
  These are run for real by the local Monte-Carlo engine every time, so this part
  needs no API key.
- **code, 4 items.** The offline code-spec fixtures.
- **verina, 10 items.** Real Verina tasks, with verdicts replayed from an earlier
  live AXLE run. They are meant to be faithful, so they measure how often a checker
  raises a false alarm.

| checker | unfaithful caught | false alarms | gives a counterexample | F1 |
|---|---|---|---|---|
| Popper | 176/178 (99%) | 0/165 (0%) | yes, every time | 0.99 |
| Proof checker (AXLE/Lean) | 0/178 (0%) | 0/165 (0%) | no | 0.00 |
| LLM judge (a model reads the spec and guesses) | runnable live | runnable live | no | runnable live |

**Why 99% and not 100%, and why the F1 is a real number.** The two specs Popper
misses at this setting are the rarest subtle bugs: they fail on roughly 1 input in
10,000, and at a budget of 2,000 random draws Popper sometimes does not hit the bad
input. That is honest, and it is exactly the limitation I document. Spend more
draws and it finds them. The benchmark records this as a sweep:

| draws per statement | math recall | math F1 | subtle bugs caught | subtle-bug F1 |
|---|---|---|---|---|
| 100 | 98% | 0.99 | 6/10 (60%) | 0.75 |
| 500 | 99% | 0.99 | 8/10 (80%) | 0.89 |
| 2,000 | 99% | 0.99 | 8/10 (80%) | 0.89 |
| 10,000 | 100% | 1.00 | 10/10 (100%) | 1.00 |
| 50,000 | 100% | 1.00 | 10/10 (100%) | 1.00 |

The proof checker catches none of them at any budget, and that is not a knock on
the prover. It is the point: catching a bad spec is simply not a thing a proof
checker does, because every spec in the set is valid as far as the proof is
concerned. The LLM judge can sometimes guess right, but it never hands you the
input that breaks the spec. For a published number, the Verina paper puts the best
general model around 52% on combined spec soundness and completeness. Run it
yourself:

```bash
python examples/run_benchmark.py          # Popper and the proof-checker baseline, offline
python examples/run_benchmark.py --llm    # add a live LLM judge (needs ANTHROPIC_API_KEY)
```

Outputs go to `results/benchmark.json`, `results/benchmark.csv`, and
[`reports/benchmark.md`](./reports/benchmark.md). The website draws charts from
the same data.

## Other results

All reports are in [`reports/`](./reports). Machine-readable copies (JSON and CSV)
are in [`results/`](./results).

Live Verina spec check against AXLE, real tasks and real Lean:

```
[FAITHFUL    ] verina_basic_1   correct answers accepted; every wrong answer rejected
[INCONCLUSIVE] verina_basic_3   spec could not be decided on one of the test cases
... 10 claims | FAITHFUL 8  INCONCLUSIVE 2
```

Math engine, faithful statements survive and broken ones get a counterexample:

```
kl_nonneg_DROPPED_norm    sum q = 3.53 (not 1) => KL = -1.15 < 0
dpi_DROPPED_markov        I(X;Z) = 0.83 > I(X;Y) = 0.05  (Z leaks X directly)
entropy_convex_WRONG      H(mix) = 1.08 > the average 1.06  (entropy is concave, not convex)
```

Repair loop, every broken spec driven back to faithful by its own counterexample:

```
sort_by_length        VACUOUS    -> FAITHFUL   (length-only spec, add sortedness and permutation)
max_lower_bound_only  INCOMPLETE -> FAITHFUL   (out >= a and out >= b, also require out in {a, b})
abs_strictly_positive UNSOUND    -> FAITHFUL   (out > 0 rejects abs(0) = 0, relax to >=)
```

## Repository layout

```
falsify/             the implementation package
  core/        shared pieces: Verdict, Oracle, audit and report
  montecarlo/  (M1) the numerical engine for math statements
  speccheck/   (M1) the offline code-spec engine, task model, fixtures, mutation
  live/        the live Verina check against AXLE (axle.py + verina.py)
  repair/      (M2) the counterexample-driven repair loop
  bench/       the benchmark (corpus, judges, metrics, runner)
examples/      runnable scripts (audit_math, audit_verina, verina_live_audit, repair_demo, run_benchmark)
tests/         unit tests
reports/       written reports, including benchmark.md and research.md
results/        machine-readable results (JSON and CSV)
notebook/      Popper.ipynb, a walkthrough with outputs
web/           the website: overview, benchmark with charts, audits, research, and a Claude agent
```

## Quickstart

No third-party packages for the core, Python 3.10 or newer:

```bash
python examples/audit_math.py        # the math engine on an information-theory ladder
python examples/audit_verina.py      # the code-spec engine on offline fixtures
python examples/repair_demo.py       # the repair loop
python examples/run_benchmark.py     # the benchmark (Popper vs the proof-checker baseline)
python -m unittest discover -s tests -t .   # the tests
```

Live check of the real 189-task Verina benchmark against AXLE:

```bash
pip install axiom-axle                                  # the official AXLE client
export AXLE_API_KEY=...                                 # https://axle.axiommath.ai/app/console
python examples/verina_live_audit.py --limit 8
```

## The website and its API keys

The site in [`web/`](./web) has an Overview, the Benchmark with charts, the audit
results, the Research write-up, and a live Claude agent. To be clear about keys:
the local math benchmark needs none, but the deployed site does need two, set as
environment variables (on Vercel, in the project settings):

- `ANTHROPIC_API_KEY` powers the Claude agent (`web/app/api/chat/route.ts`).
- `AXLE_API_KEY` powers the agent's live disprove and check tools against the
  Axiom Lean Engine (`web/app/lib/axle.ts`).

Both are read server-side only and are never sent to the browser. The full list,
including the optional `ANTHROPIC_MODEL`, `AXLE_ENVIRONMENT`, and `AXLE_BASE_URL`,
is in [`web/.env.example`](./web/.env.example). I did not change any of this
wiring, so if those keys are already set on Vercel the agent and live AXLE keep
working.

## A note on honesty

Popper breaks statements; it does not certify them. A FAITHFUL verdict means
Popper could not find a counterexample within its budget, not that none exists.
Proving that no counterexample exists is undecidable in general, so I do not claim
it. What Popper does catch is the common, real failure: a dropped assumption, a
flipped direction, a spec that is too loose or too tight. Lean and AXLE remain the
final word on the proof itself. When a spec cannot be decided on a test case,
Popper says INCONCLUSIVE instead of guessing.

## License and data

Apache-2.0 (see [`LICENSE`](./LICENSE)). The Verina benchmark is CC-BY-SA-4.0 and
is not stored here; it is fetched on demand from
[`sunblaze-ucb/verina`](https://github.com/sunblaze-ucb/verina) into a git-ignored
cache. Built on the open [AXLE](https://github.com/AxiomMath/axiom-lean-engine)
engine and [Mathlib](https://github.com/leanprover-community/mathlib4).

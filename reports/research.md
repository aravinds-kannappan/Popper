# Checking the statement, not just the proof

A short report on what Popper adds, written in plain English, with a benchmark
that measures it.

## The short version

When you verify code or math with a computer, you write a statement of what is
supposed to be true (people call this a "specification", or "spec" for short) and
then prove your work matches it. The weak spot is the statement itself. It can be
too loose and accept wrong answers, too tight and reject right ones, or empty and
accept anything. In all three cases the proof still passes and the result is still
wrong.

I built Popper to attack that weak spot. Popper is an "oracle", which here just
means a separate checker you can ask a yes-or-no question. The question is: can I
break this statement? Popper tries hard to find an input that makes the statement
fail, and when it finds one it gives you that input, which I call a
counterexample. On a benchmark of 346 statements I labelled by hand, Popper flags
176 of the 178 broken ones with a counterexample and raises no false alarms on the
165 good ones. The two it misses are subtle bugs that only fail on about one input
in ten thousand, and with a larger search budget it finds those too. A proof
checker on its own flags none of them, because flagging a bad statement is not
something a proof checker can do.

## 1. The problem, and why the proof checker misses it

The proving side has gotten very strong. Modern provers clear hard competition
math and discharge most of the proof goals in code-verification benchmarks. The
specifying side has not kept up. On Verina, a benchmark of code paired with specs,
the best general model writes correct code about 73% of the time but writes specs
that are both sound and complete only about 52% of the time. ("Sound" means the
spec does not reject a correct answer. "Complete" means it does not accept a wrong
one.)

The reason a proof checker cannot help here is structural. A checker takes a
statement and a proof and confirms the proof matches the statement. It never
looks at whether the statement matches what you meant. So a wrong statement just
yields a valid proof of the wrong thing, and the checker reports success. Worse,
when one model writes both the spec and the code, it tends to write a spec its own
code already satisfies, bugs included. The failure is silent, and silence is the
last thing you want from a verification tool.

## 2. Where Popper sits next to the usual tools

Three levels of trust, and what each one still misses.

1. A model writes a proof in words. It reads well and guarantees nothing. A
   skipped case is invisible without an expert reader.
2. A model plus a prover (Lean or AXLE). You get a real proof that matches the
   statement, and you are still trusting the statement. A statement that says
   nothing proves instantly. "Sorted" defined as "same length" is satisfied by
   code that does nothing.
3. A model plus a prover plus Popper. The proof matches the statement, and an
   independent oracle has tried to break the statement. If it could not, that is
   evidence the spec is fine. If it could, you get the input that breaks it.

Provers live on level two. Level three is the open part, and that is where Popper
works.

## 3. How Popper works

One interface, two engines.

**Math.** Most inequalities can be checked with numbers. A statement has an
assumption and a conclusion, and the engine draws thousands of random cases and
checks that the conclusion holds whenever the assumption does. This is a
Monte-Carlo check, which is just "try many random inputs and watch for a break".
For example, Gibbs' inequality says the KL divergence (a standard measure of how
different two probability distributions are) is never negative: KL(p, q) >= 0. It
holds when q is a real distribution, but the moment you forget that q has to sum
to 1, it fails, and the engine finds a q that drives the value below zero. This
engine needs no prover and no API key.

**Code.** Each Verina task ships a correct answer and several wrong ones. Popper
asks AXLE to evaluate the spec on each. A rejected correct answer means the spec
is too tight. An accepted wrong answer means it is too loose. An accepted nonsense
answer means it is empty.

The counterexample is the part that makes this practical. A pass/fail bit tells
you a spec is probably wrong. A counterexample tells you which input breaks it,
which is what you actually need to fix it. The same input also works as a clean
training signal, a reward an automated loop can optimize against with no human in
the loop. Popper's repair loop uses the counterexample to adjust the statement and
check again, until it holds up or the budget runs out.

## 4. The benchmark

I labelled 346 statements ahead of time as faithful or unfaithful, and for the
unfaithful ones I recorded the kind of bug. Then I ran three checkers over the
same set.

- **math, 332 items.** Families of inequalities (Cauchy-Schwarz, AM-GM, the
  triangle inequality, and several from information theory), each generated across
  a range of sizes, with faithful and broken versions side by side, a few "empty
  statement" traps, and a batch of subtle bugs that only fail on a small fraction
  of inputs. Run for real by the local Monte-Carlo engine.
- **code, 4 items.** The offline code-spec fixtures.
- **verina, 10 items.** Real tasks, with verdicts replayed from an earlier live
  AXLE run, all meant to be faithful, which measures the false-alarm rate.

The three checkers are the proof checker (accepts anything that is valid as a
proof), an LLM judge (a model reads the statement and guesses, with no execution),
and Popper.

| checker | unfaithful caught | false alarms | counterexample | F1 |
|---|---|---|---|---|
| Popper | 176/178 (99%) | 0/165 (0%) | every time | 0.99 |
| Proof checker | 0/178 (0%) | 0/165 (0%) | never | 0.00 |
| LLM judge | runnable live | runnable live | never | runnable live |

The score is 0.99 rather than a clean 1.00 on purpose, and that is the more
honest result. Easy bugs, like a flipped inequality, fail on about half of all
random inputs, so Popper catches them after a couple of draws. The subtle bugs
fail on a tiny fraction of inputs, so finding them is a question of how many draws
you spend. The benchmark records this as a sweep:

| draws per statement | math recall | math F1 | subtle bugs caught | subtle-bug F1 |
|---|---|---|---|---|
| 100 | 98% | 0.99 | 6/10 | 0.75 |
| 500 | 99% | 0.99 | 8/10 | 0.89 |
| 2,000 | 99% | 0.99 | 8/10 | 0.89 |
| 10,000 | 100% | 1.00 | 10/10 | 1.00 |
| 50,000 | 100% | 1.00 | 10/10 | 1.00 |

So F1 is a real number that moves with effort, not a fixed 1.00. The proof checker
scores zero at every budget, because flagging a bad spec is outside what it does.
The LLM judge can guess, but it never returns the input that breaks the spec. For
a published number, the Verina paper puts the best general model near 52% on
combined soundness and completeness. The full per-item table and the charts are in
the repo and on the website.

## 5. What Popper adds

1. A checker for the statement, not the proof. Everything else checks the proof
   against the statement; Popper checks the statement against intent.
2. A counterexample, not a score. A number says a spec is probably wrong; a
   counterexample says which input breaks it.
3. A clean training signal. The same counterexample that fixes a spec is a reward
   an automated loop can use, with no human and no separate reward model.
4. Honest "I don't know". When a spec cannot be decided on a test case, Popper says
   INCONCLUSIVE instead of pretending.

## 6. Popper and AxiomProver

Axiom Math ships two pieces I build on. AXLE is the Lean engine: the API that
type-checks a statement and runs the counterexample search. AxiomProver is the
prover, an agent that takes a statement and searches for a full Lean proof, and it
is very strong at that step. Popper is not a competitor to either. It answers a
different question and belongs in front of the prover.

The two answer different questions. AxiomProver answers "can this statement be
proved, and here is the proof." It is the verifier, and its blind spot is the
statement: it will prove whatever it is handed, faithful or not. Popper answers "is
this the right statement to prove." It is the screen, it does not produce proofs,
and it tries to break the spec and return a witness.

The practical reason to run Popper first is compute. Proof search is expensive;
breaking a statement with sampling or a few witness checks is cheap, so pointing
the expensive tool at a statement the cheap tool already refutes is waste. Two
failure modes make this concrete. A vacuous or too-weak spec proves easily and
certifies nothing, so AxiomProver would hand back a clean proof of a statement that
guarantees nothing, and the work looks done when it is not. A wrong or too-strong
spec is unprovable, so AxiomProver can spend a large budget failing to prove
something that is false because the spec has a bug. In both cases Popper settles it
cheaply up front: it flags the empty spec before any proof is attempted, and it
finds the breaking input for the wrong one and says to repair the spec rather than
chase a proof that cannot exist.

| | AxiomProver | Popper |
|---|---|---|
| Question | Can this be proved? | Is this the right statement? |
| Method | Search for a Lean proof | Try to break the statement |
| Output | A proof, or failure | A counterexample, or no break |
| Cost | High | Low |
| Blind to | Whether the statement is faithful | It does not prove or certify |
| Role | Verifier | Screen in front of the verifier |

So the loop is: Popper breaks the spec, the witness drives a repair, and
AxiomProver proves the statement once it holds up. Popper keeps the prover's
compute on statements that are worth proving, and the prover gives the real proof.

## 7. Limits

Popper breaks statements; it does not certify them. A FAITHFUL verdict means no
counterexample was found within the budget, not that none exists, and proving none
exists is undecidable in general. Random sampling can miss a bug that hides on a
tiny set of inputs, though dropped assumptions and flipped directions are exactly
the bugs that show up under sampling. Lean and AXLE stay the final word on the
proof itself.

## 8. Next

- Run the repair loop inside the live AXLE path, swapping the fixed spec back in
  and checking again.
- Sweep all 189 Verina tasks instead of a sample.
- Build the self-improvement loop: rank a model's tries by the oracle and form
  training pairs from the labels.
- Grow the math benchmark into measure theory and linear algebra.

## Reproduce

```bash
python examples/run_benchmark.py            # Popper and the proof-checker baseline
python examples/run_benchmark.py --llm      # add a live LLM judge (needs ANTHROPIC_API_KEY)
python -m unittest discover -s tests -t .   # the tests
```

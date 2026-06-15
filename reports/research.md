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
counterexample. On a benchmark of 334 statements I labelled by hand, Popper flags
every one of the 168 broken ones with a counterexample and raises no false alarms
on the 163 good ones. A proof checker on its own flags none of them, because
flagging a bad statement is not something a proof checker can do.

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

I labelled 334 statements ahead of time as faithful or unfaithful, and for the
unfaithful ones I recorded the kind of bug. Then I ran three checkers over the
same set.

- **math, 320 items.** Families of inequalities (Cauchy-Schwarz, AM-GM, the
  triangle inequality, and several from information theory), each generated across
  a range of sizes, with faithful and broken versions side by side, plus a few
  "empty statement" traps. Checked by the local Monte-Carlo engine.
- **code, 4 items.** The offline code-spec fixtures.
- **verina, 10 items.** Real tasks checked live against AXLE, all meant to be
  faithful, which measures the false-alarm rate.

The three checkers are the proof checker (accepts anything that is valid as a
proof), an LLM judge (a model reads the statement and guesses, with no execution),
and Popper.

| checker | unfaithful caught | false alarms | counterexample | F1 |
|---|---|---|---|---|
| Popper | 168/168 (100%) | 0/163 (0%) | every time | 1.00 |
| Proof checker | 0/168 (0%) | 0/163 (0%) | never | 0.00 |
| LLM judge | runnable live | runnable live | never | runnable live |

The proof checker scores zero no matter how strong the prover behind it is,
because flagging a bad spec is outside what it does. The LLM judge can guess, but
it never returns the input that breaks the spec. For a published number, the
Verina paper puts the best general model near 52% on combined soundness and
completeness. The full per-item table and the charts are in the repo and on the
website.

## 5. What Popper adds

1. A checker for the statement, not the proof. Everything else checks the proof
   against the statement; Popper checks the statement against intent.
2. A counterexample, not a score. A number says a spec is probably wrong; a
   counterexample says which input breaks it.
3. A clean training signal. The same counterexample that fixes a spec is a reward
   an automated loop can use, with no human and no separate reward model.
4. Honest "I don't know". When a spec cannot be decided on a test case, Popper says
   INCONCLUSIVE instead of pretending.

## 6. Limits

Popper breaks statements; it does not certify them. A FAITHFUL verdict means no
counterexample was found within the budget, not that none exists, and proving none
exists is undecidable in general. Random sampling can miss a bug that hides on a
tiny set of inputs, though dropped assumptions and flipped directions are exactly
the bugs that show up under sampling. Lean and AXLE stay the final word on the
proof itself.

## 7. Next

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

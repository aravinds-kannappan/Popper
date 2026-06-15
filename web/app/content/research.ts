// The research write-up, rendered on the Research tab through the shared
// Markdown component (Markdown + KaTeX). A fuller version lives in
// reports/research.md in the repository.

export const research = String.raw`
# Checking the statement, not just the proof

**What Popper adds, in plain English, with a benchmark that measures it.**

## The short version

When you verify code or math with a computer, you write down a statement of what
is supposed to be true (people call this a "specification", or "spec") and then
prove your work matches it. The weak spot is the statement itself. It can be too
loose and accept wrong answers, too tight and reject right ones, or empty and
accept anything. In all three cases the proof passes and the result is still
wrong.

I built Popper to attack that weak spot. Popper is an "oracle", which here just
means a separate checker you can ask one question: can I break this statement? It
tries hard to find an input that makes the statement fail, and when it finds one
it gives you that input, which I call a counterexample. On a benchmark of 346
statements I labelled by hand, Popper flags 176 of the 178 broken ones with a
counterexample and raises no false alarms on the 165 good ones. The two it misses
are subtle bugs that only fail on about one input in ten thousand, and with more
search it finds those too. A proof checker on its own flags none, because flagging
a bad statement is not something a proof checker can do.

## Why the proof checker misses this

The proving side is strong now. The specifying side is not. On Verina, a benchmark
of code paired with specs, the best general model writes correct code about 73% of
the time but writes specs that are both sound and complete only about 52% of the
time. "Sound" means the spec does not reject a correct answer; "complete" means it
does not accept a wrong one.

A proof checker cannot help here, and the reason is structural. It takes a
statement and a proof and confirms the proof matches the statement. It never asks
whether the statement matches what you meant. So a wrong statement just yields a
valid proof of the wrong thing.

## Three levels of trust

1. A model writes a proof in words. It reads well and guarantees nothing.
2. A model plus a prover (Lean or AXLE). You get a real proof that matches the
   statement, and you are still trusting the statement. A statement that says
   nothing, like $\forall x,\ \text{true}$, proves instantly. "Sorted" defined as
   "same length" is satisfied by code that does nothing.
3. A model plus a prover plus Popper. The proof matches the statement, and an
   independent oracle has tried to break the statement and either failed or handed
   you the input that breaks it.

Provers live on level two. Level three is where Popper works.

## How it works

**Math.** Most inequalities can be checked with numbers. A statement has an
assumption and a conclusion, and the engine draws thousands of random cases and
checks that the conclusion holds whenever the assumption does. This is a
Monte-Carlo check, which is just "try many random inputs and watch for a break".
For example, Gibbs' inequality says the KL divergence (a standard way to measure
how different two probability distributions are) is never negative:
$$\mathrm{KL}(p \| q) = \sum_i p_i \log \frac{p_i}{q_i} \ge 0.$$
It holds when $q$ is a real distribution, but the moment you forget the assumption
$\sum_i q_i = 1$, it fails, and the engine finds a $q$ that drives the sum below
zero. The same thing happens with the data processing inequality
$X \to Y \to Z \Rightarrow I(X;Z) \le I(X;Y)$: drop the Markov assumption and the
engine exhibits a case where $Z$ copies $X$ directly. This engine needs no prover
and no API key.

**Code.** Each Verina task ships a correct answer and several wrong ones. Popper
asks AXLE to evaluate the spec on each. A rejected correct answer means the spec is
too tight. An accepted wrong answer means it is too loose. An accepted nonsense
answer means it is empty.

The counterexample is what makes this practical. A pass/fail bit tells you a spec
is probably wrong. A counterexample tells you which input breaks it, which is what
you need to fix it. The same input also works as a clean training signal for an
automated loop, with no human in the loop. Popper's repair loop uses it to adjust
the statement and check again until it holds up.

## The benchmark

I labelled 346 statements as faithful or unfaithful, recorded the kind of bug for
the broken ones, and ran three checkers over the same set: the proof checker
(accepts anything valid as a proof), an LLM judge (a model reads the statement and
guesses, with no execution), and Popper.

| checker | unfaithful caught | false alarms | counterexample | F1 |
|---|---|---|---|---|
| Popper | 176/178 (99%) | 0/165 (0%) | every time | 0.99 |
| Proof checker | 0/178 (0%) | 0/165 (0%) | never | 0.00 |
| LLM judge | runnable live | runnable live | never | runnable live |

The score is 0.99, not a flat 1.00, on purpose. Easy bugs fail on about half of
all random inputs, so Popper catches them in a couple of draws. The subtle bugs
fail on a tiny fraction of inputs, so finding them depends on how many draws you
spend: at 100 draws Popper catches 6 of 10 subtle bugs, and by 10,000 draws it
catches all 10. F1 is a real number that moves with effort, shown on the budget
chart on the Benchmark tab. The proof checker scores zero at every budget. The LLM
judge can guess, but it never returns the input that breaks the spec.

## What Popper adds

1. A checker for the statement, not the proof.
2. A counterexample, not a score. It says which input breaks the spec.
3. A clean training signal: the counterexample that fixes a spec is also a reward.
4. Honest "I don't know" when a spec cannot be decided on a case, instead of a guess.

## Limits

Popper breaks statements; it does not certify them. A FAITHFUL verdict means no
counterexample was found within the budget, not that none exists. Random sampling
can miss a bug that hides on a tiny set of inputs, though dropped assumptions and
flipped directions are exactly the bugs that show up under sampling. Lean and AXLE
stay the final word on the proof itself.
`;

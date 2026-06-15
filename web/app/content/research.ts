// The research write-up, rendered on the Research tab through the shared
// Markdown component (Markdown + KaTeX). A fuller version lives in
// reports/research.md in the repository.

export const research = String.raw`
# Falsifying the specification

**An executable oracle for spec faithfulness, and a benchmark that measures it.**

## The gap

Formal verification gives you a proof that some code or some math matches a
written statement. It says nothing about whether that statement is the one you
meant. A specification can be too weak, so it accepts wrong answers. It can be
too strong, so it rejects right ones. It can be vacuous, so it accepts
everything. In all three cases the proof checker is satisfied and the pipeline is
green, and the result is still wrong.

The proving step has moved fast. Provers now clear competition mathematics and
discharge most of the proof obligations in code verification benchmarks. The
specifying step has not kept pace. On the Verina benchmark the best general model
writes code that is correct about 73% of the time but writes specifications that
are sound and complete only about 52% of the time. The specification, not the
proof, is the weak link, and the checker cannot see it: it validates a proof
against a specification, so a wrong specification just yields a valid proof of the
wrong thing.

## Three rungs of trust

1. A model writes a proof. You get a fluent artifact and no ground truth.
2. A model plus Lean or AXLE. You get a real proof that matches the statement,
   and you are still blind to whether the statement is faithful. A vacuous
   statement such as $\forall x,\ \top$ proves instantly. "Sorted" written as
   "same length" is satisfied by the identity function.
3. A model plus Lean plus Popper. The proof matches the statement, and an
   independent oracle has either failed to break the statement or has broken it
   and handed you the counterexample.

Formal provers live on rung two. Rung three is the open problem, and it is where
Popper operates.

## Method

Popper exposes one interface, a falsification oracle, with two engines behind it.

**Math.** Every inequality or identity has a numerical shadow. A statement
carries a hypothesis $H$ and a conclusion $C$, and the oracle tests $H \Rightarrow
C$ over thousands of sampled instances. A dropped hypothesis or a flipped
direction breaks on some draw, and that draw is the counterexample. For example,
Gibbs' inequality $\mathrm{KL}(p \| q) \ge 0$ holds for distributions, but the
moment you forget $\sum_i q_i = 1$ it fails, and the oracle finds a $q$ that drives
$\sum_i p_i \log \frac{p_i}{q_i}$ below zero. The data processing inequality
$X \to Y \to Z \Rightarrow I(X;Z) \le I(X;Y)$ fails without the Markov
hypothesis, and the oracle exhibits a joint where $Z$ leaks $X$ directly. This
engine runs locally with no prover and no API key.

**Code.** Each Verina task ships a postcondition, a correct output, and several
wrong outputs. Popper asks AXLE to evaluate the postcondition on those witnesses
through $\texttt{native\_decide}$. A rejected correct output means the spec is too
strong. An accepted wrong output means it is too weak. An accepted garbage output
means it is vacuous.

A counterexample is more than a failing test. It is a repair signal, and the same
signal is a clean reward for an automated loop. Popper's repair stage feeds the
counterexample back into the statement and re-audits until the spec is faithful or
the budget runs out.

## Benchmark

We labelled 38 formal claims ahead of time as faithful or unfaithful, recorded the
kind of bug, and ran three judges over the same corpus.

- **Math, 24 items.** Eleven faithful inequalities (Gibbs, data processing,
  entropy concavity, Cauchy-Schwarz, AM-GM, the triangle inequality, entropy
  subadditivity, non-negativity of mutual information, the cross entropy bound,
  Jensen for the logarithm, non-negativity of variance), eleven unfaithful twins,
  and two vacuity traps.
- **Code, 4 items.** The offline code-spec fixtures.
- **Verina, 10 items.** Real tasks audited live over AXLE, all faithful, which
  measures the false positive rate.

The judges are the proof checker, which accepts anything that type checks; an LLM
judge, which reads the statement and guesses with no execution; and Popper.

| judge | unfaithful caught | false positives | counterexample yield | F1 |
|---|---|---|---|---|
| Popper | 14/14 (100%) | 0/22 (0%) | 100% | 1.00 |
| Proof checker | 0/14 (0%) | 0/22 (0%) | 0% | 0.00 |
| LLM judge | live | live | 0% (no witness) | live |

The proof checker scores zero recall no matter how strong the prover is, because
flagging an unfaithful spec is outside what it does. The LLM judge can guess, but
it never returns an executable witness. The full numbers and the per-item table
are on the Benchmark tab.

## What Popper adds

1. An oracle for the specification, not the proof. Everything else checks the
   proof against the spec; Popper checks the spec against intent.
2. A counterexample, not a score. A number says a spec is probably wrong. A
   counterexample says which input breaks it, which is what you fix.
3. A clean training signal. The counterexample that repairs a spec is a reward an
   automated loop can optimize against, with no human and no GPU reward model.
4. Honest abstention. When a spec is not decidable on a witness, Popper reports
   INCONCLUSIVE rather than guessing.

## Limitations

Popper falsifies; it does not certify. A FAITHFUL verdict means no counterexample
was found within the search budget, not a proof of faithfulness, which is
undecidable in general. Monte-Carlo search can miss a bug that hides on a measure
zero set, though dropped hypotheses and flipped directions are exactly the
failures that surface under sampling. Lean and AXLE remain the ground truth for
the proof itself.
`;

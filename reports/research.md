# Falsifying the specification: an executable oracle for spec faithfulness

A short research report on what Popper adds, and a benchmark that measures it.

## Summary

Formal verification gives you a proof that some code or some math matches a
written statement. It says nothing about whether that statement is the one you
meant. A specification can be too weak (it accepts wrong answers), too strong (it
rejects right ones), or vacuous (it accepts everything). In all three cases the
proof checker is happy and the pipeline is green, and the result is still wrong.

Popper is an executable oracle that goes after that gap. Instead of trying to
prove a statement, it tries to break it, and when it succeeds it returns a
concrete counterexample. On a 38 item benchmark spanning math statements, code
specs, and real Verina tasks, Popper flags every one of the 14 unfaithful specs
with a counterexample and raises zero false alarms on the 22 faithful ones. A
proof checker alone flags none of them, because flagging them is not something a
proof checker can do.

## 1. The problem

The trustworthy side of verified AI has moved fast on the proving step. Provers
now clear competition level mathematics and solve most of the proof obligations
in code verification benchmarks. The specification step has not moved with it. On
the Verina benchmark the best general model writes code that is correct about 73%
of the time but writes specifications that are sound and complete only about 52%
of the time. The specification, not the proof, is the weak link.

This matters because the proof checker cannot see the weakness. A checker
validates a proof against a specification. If the specification is wrong, the
checker validates a proof of the wrong thing and reports success. Worse, when the
same model writes both the specification and the code, it tends to write a
specification that its own code already satisfies, bugs included. The failure is
silent, and silence is exactly what you do not want from a verification tool.

## 2. Where Popper sits

Think of three rungs of trust.

1. A model writes or explains a proof. You get a fluent artifact and no ground
   truth. Unjustified steps and missing cases are invisible without an expert
   reader.
2. A model plus Lean or AXLE. You get a real proof that matches the statement.
   You are still blind to whether the statement is faithful. A vacuous statement
   proves instantly. "Sorted" written as "same length" is satisfied by the
   identity function, and the checker will not complain.
3. A model plus Lean plus Popper. The proof matches the statement, and an
   independent oracle has tried and failed to break the statement, or has broken
   it and handed you the counterexample.

Rung two is where formal provers live today. Rung three is the open problem, and
it is where Popper operates.

## 3. Method

Popper has one interface and two engines. The interface is a falsification
oracle: given a formal claim, return a verdict and, on failure, a counterexample.
The verdicts are FAITHFUL (no counterexample found within budget), FALSIFIED,
UNSOUND, INCOMPLETE, VACUOUS, and INCONCLUSIVE (not enough signal, reported
honestly rather than guessed).

**Math.** Every inequality or identity in analysis and information theory has a
numerical shadow. A statement carries a hypothesis H and a conclusion C, and the
oracle tests H implies C over thousands of sampled instances. A dropped
hypothesis, a flipped inequality, or an over-strong claim breaks on some draw, and
the violating draw is the counterexample. This engine runs locally with no prover
and no API key.

**Code.** Each Verina task ships a postcondition, a correct output, and several
wrong outputs. Popper asks AXLE to evaluate the postcondition on those witnesses
through `native_decide`. If a correct output is rejected, the spec is too strong.
If a wrong output is accepted, the spec is too weak. If even garbage is accepted,
the spec is vacuous. No mutant generation is needed because the wrong answers are
already curated in the benchmark.

A counterexample is more than a failing test. It is a repair signal. Popper's M2
loop feeds the counterexample back into the statement, strengthens or relaxes the
relevant clause, and re-audits until the spec is faithful or the budget runs out.

## 4. The benchmark

We assembled a labelled corpus of 38 formal claims and tagged each one ahead of
time as faithful or unfaithful, with the kind of bug recorded.

- **Math, 24 items.** Eleven faithful inequalities and identities (Gibbs, the
  data processing inequality, entropy concavity, Cauchy-Schwarz, AM-GM, the
  triangle inequality, subadditivity of entropy, non-negativity of mutual
  information, the cross entropy bound, Jensen for the logarithm, non-negativity
  of variance), eleven unfaithful twins (a dropped hypothesis, a flipped
  direction, or an over-strong claim each), and two vacuity traps.
- **Code, 4 items.** The offline code-spec fixtures: one faithful, plus a
  vacuous, an incomplete, and an unsound spec.
- **Verina, 10 items.** Real Verina tasks audited live over AXLE. These ship as
  faithful, so they measure the false positive rate.

We run three judges over the same corpus.

- **Proof checker (AXLE or Lean alone).** It accepts any spec that type checks.
  Every spec in the corpus type checks, so it accepts all of them. This is not a
  straw man. It is exactly what a proof checker does, and the whole point is that
  an unfaithful spec still type checks.
- **LLM judge.** A model reads the intent and the statement and guesses, with no
  execution and no counterexample. The harness runs this live when an API key is
  present.
- **Popper.** The executable oracle in this repository.

### Results

| judge | unfaithful caught | false positives | counterexample yield | F1 |
|---|---|---|---|---|
| Popper | 14/14 (100%) | 0/22 (0%) | 100% | 1.00 |
| Proof checker | 0/14 (0%) | 0/22 (0%) | 0% | 0.00 |
| LLM judge | live, see note | live | 0% (no witness) | live |

The proof checker scores zero recall no matter how strong the underlying prover
is, because catching an unfaithful spec is outside what it does. The LLM judge can
guess, but it never returns an executable witness. For a published reference
point, the Verina paper reports the best general model reaching about 52%
combined specification soundness and completeness. Re-running the benchmark with
`--llm` fills that row from a live model.

The numbers are reproducible. The math half of the benchmark needs no API key and
no prover; it runs with `python examples/run_benchmark.py`.

## 5. What Popper adds to the field

1. **An oracle for the specification, not the proof.** Existing tooling checks the
   proof against the spec. Popper checks the spec against intent, which is the
   part nothing else covers.
2. **A counterexample, not a score.** A benchmark number tells you a spec is
   probably wrong. A counterexample tells you which input breaks it, which is what
   you need to fix it. Counterexample yield is the column where Popper is alone.
3. **A clean training signal.** The same counterexample that repairs a spec is a
   reward an automated loop can optimize against, without a human in the loop and
   without GPU based reward models.
4. **Honest abstention.** When a spec is not decidable on a witness, Popper
   reports INCONCLUSIVE rather than guessing. A faithfulness tool that pretends to
   certainty is worse than one that admits the gap.

## 6. Limitations

Popper falsifies; it does not certify. A FAITHFUL verdict means no counterexample
was found within the search budget, not a proof of faithfulness, which is
undecidable in general. The math oracle inherits the usual limits of Monte-Carlo
search: a bug that hides on a measure zero set can be missed, though dropped
hypotheses, flipped directions, and over-strong claims are exactly the failures
that show up under sampling. The code oracle depends on the quality of the wrong
outputs that come with each task. Lean and AXLE remain the ground truth for the
proof itself.

## 7. Next steps

- Run the declarative repair loop inside the live AXLE path, swapping the
  repaired postcondition back into the prelude and re-auditing.
- Sweep all 189 Verina tasks rather than a sample.
- Build the self improvement loop: rank best-of-n generations by the oracle and
  form preference pairs from oracle labels.
- Grow the math corpus beyond information theory into measure theory and linear
  algebra, where dropped hypotheses are common and easy to formalize wrong.

## Reproduce

```bash
python examples/run_benchmark.py            # Popper and the proof-checker baseline
python examples/run_benchmark.py --llm      # add a live LLM judge (needs ANTHROPIC_API_KEY)
python -m unittest discover -s tests -t .   # the full test suite
```

Outputs land in `results/benchmark.json`, `results/benchmark.csv`, and
`reports/benchmark.md`.

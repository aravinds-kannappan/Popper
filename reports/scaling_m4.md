# Scaling Popper M4: exact falsification, certificates, type-directed generation, a trained adversary

The M3 layer (`falsify.scale`) ported six AI-safety ideas onto Popper's
faithfulness surface. This M4 layer goes after the three deepest gaps those
modules left open: a `FAITHFUL` verdict that is still only "no counterexample in
budget", a search that only covers statements with a numerical shadow, and an
adversary written by hand. Each is now backed by running, tested code.

## Idea 1: close the measure-zero gap, fundamentally

### 1a. An exact engine that decides instead of samples (`falsify/smt/`)

The Monte-Carlo and adaptive engines search; they can only ever report "no
counterexample within budget". The new `SMTOracle` *decides* a `SymbolicClaim`
over the decidable fragment, and returns one of two things sampling cannot:

- an **exact counterexample** in the measure-zero region a sampler would miss, or
- a **real certificate** of faithfulness (the falsification target is provably
  unsatisfiable), not a budget-limited guess.

Three backends sit behind the shared `Oracle` interface:

| backend | fragment | result quality | dependency |
|---|---|---|---|
| `EnumBackend` | finite integer box | exact; certificate scoped to the box | stdlib |
| `LinearBackend` (Fourier-Motzkin) | linear arithmetic over Q | exact; unbounded UNSAT certificate | stdlib |
| `Z3Backend` | nonlinear arithmetic | exact via SMT | optional `pip install 'falsify[smt]'` |

Run on the symbolic library, every verdict is exact (`reports/exact.md`):

| claim | verdict | backend | certificate |
|---|---|---|---|
| `abs_strictly_positive` | FALSIFIED at `x=0` | enum | - |
| `abs_value_faithful` | FAITHFUL | enum | certified over the box |
| `max_lower_bound_only` | FALSIFIED at `a=b=-6` | enum | - |
| `rare_int_needle` (1 bad input in 20,001) | FALSIFIED at `n=7` | enum | - |
| `mean_nonneg_overclaim` | FALSIFIED at `x0=-1` | fourier-motzkin | - |
| `nonneg_sum_certificate` | FAITHFUL | fourier-motzkin | real UNSAT certificate |
| `amgm_flipped_nonlinear` | needs z3 (else INCONCLUSIVE) | z3 | - |

The `rare_int_needle` row is the point: uniform sampling at 2,000 draws misses a
1-in-20,001 bug about 90% of the time, while enumeration finds `n=7` exactly and
certifies the other 20,000 inputs clean. Everything runs in exact rational
arithmetic, so there is no floating-point slop in either the witness or the
certificate. The nonlinear row is handled honestly: without z3 the oracle returns
INCONCLUSIVE with a clear note rather than guessing.

### 1b. A statistical certificate for everything else (`falsify/scale/certify.py`)

Where exact decision does not apply (nonlinear shadows, black-box specs), a
survived sampling run can still be upgraded from a soft pass to a quantified one.
With zero counterexamples in `n` independent uniform draws, the Clopper-Pearson
upper bound (the rule of three, `1 - delta**(1/n)`) gives the largest bug rate
consistent with that outcome at confidence `1 - delta`:

| clean draws | bug-rate upper bound, 95% |
|---|---|
| 100 | 0.03 |
| 1,000 | 0.003 |
| 3,000 | 0.001 |
| 10,000 | 0.0003 |
| 50,000 | 0.00006 |

So a FAITHFUL verdict stops being "we looked and gave up" and becomes "with 95%
confidence the bug rate is under one in a thousand". `weighted_bug_rate_bound`
gives the Hoeffding analogue for a reweighted sweep, with the bounded-weight
assumption stated explicitly (adaptive search breaks plain-binomial independence,
so the soft bound is not silently misapplied to it).

## Idea 2: scale breadth with type-directed generation (`falsify/speccheck/typegen.py`)

The offline `Task` needed a hand-written `gen_input` and `test_inputs` per task,
which does not reach the full Verina set. Now both are derived from the type of
the signature, QuickCheck/SmallCheck style. `parse_signature` reads
`max2 : Int -> Int -> Int` into argument types; `gen` samples with edge-case bias;
`enumerate_small` yields every small-scope value (the empty list, the zero, the
negative, where bugs hide). Fed only generated inputs, the code-spec oracle catches
the too-weak `max` spec as INCOMPLETE with no bespoke generator at all. This is the
hook for auditing arbitrary signatures and, on the live path, driving the same
generation through AXLE's Lean probes.

## Idea 3: train the adversary (`falsify/scale/adversary.py`)

The reward-hack probe tried a fixed family of candidates in a fixed order, which
is exactly the enumeration a real optimizer ignores. Three changes make it adapt:

- **`AdaptiveHackPolicy`** - a UCB1 bandit over hacker families (constant,
  identity, negate, off-by-one, declared). Across a stream of 24 recurring spec
  shapes it cuts candidate evaluations before a catch by ~30% versus fixed order
  (216 -> 151), learning that the `declared` and `identity` families pay off while
  `const` does not on these specs.
- **`WitnessMemory`** - transfer keyed by the parsed signature shape, so a new
  task of a known shape replays the family that worked before and is caught first.
- **`conjunctive_trigger_search`** - reads the converged Cross-Entropy proposal to
  recover *which* coordinates a sleeper's trigger constrains. On the 5-D
  conjunctive needle it reports the full conjunction over all five coordinates
  (proposal mean ~0.2 each), i.e. the structure of the backdoor, not just one
  witnessing point.

## What this buys, in one line each

1. Exact decision turns "no counterexample in budget" into an exact witness or a
   real certificate for the decidable fragment.
2. A PAC bound makes the remaining (sampled) FAITHFUL verdicts quantitative.
3. Type-directed generation removes the per-task fixture and scales the surface.
4. A bandit + transfer memory makes the adversary cheaper the more specs it sees,
   and trigger search recovers the sleeper's structure.

Reproduce:

```bash
python examples/exact_demo.py                 # ideas 1-3, offline, no key
python examples/exact_demo.py --markdown      # the same as reports/exact.md
pip install 'falsify[smt]'                    # optional: enable the nonlinear Z3 backend
python -m unittest tests.test_m4 -v           # the properties above, pinned
```

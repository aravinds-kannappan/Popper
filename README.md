# Popper

**Falsify the spec, then verify the proof.**

A Lean checker (and Axiom's [AXLE](https://axle.axiommath.ai)) answers *"is this
proof valid?"* It is **silent on whether the statement means what you wanted.** A
vacuous or too-weak specification is trivially provable and certifies nothing; a
too-strong one rejects correct code. Even a 100%-green formal pipeline can be
100% wrong if the spec is unfaithful — and an LLM that writes both the spec and
the code will write a spec its own bugs satisfy.

Popper adds the missing half: an **independent, executable oracle that
*falsifies* specifications** and hands back a counterexample — the actionable
repair signal (and a clean RL reward) that proof-checking alone cannot give.

> Three rungs of trust. (1) LLM writes a proof → no ground truth, silent errors.
> (2) LLM + Lean/AXLE → knows when a *proof* is wrong, blind to spec faithfulness.
> (3) **LLM + Lean/AXLE + Popper** → the only rung that attacks *"is the thing
> we're proving the right thing?"* — the bottleneck Axiom
> [names itself](./PROPOSAL.md).

See [`PROPOSAL.md`](./PROPOSAL.md) for the full thesis, milestones, and how this
maps to Axiom's roadmap (the Verina code-verification frontier) and hiring.

---

## One idea, two surfaces

Both implement the same `Oracle` interface (`popper/oracle.py`), so one audit/
report pipeline serves both:

| Surface | Oracle | How it falsifies | Runs offline today? |
|---|---|---|---|
| **Math** (autoformalized statements) | `NumericalOracle` | Monte-Carlo: sample distributions/paths; does the inequality/identity break? | ✅ pure stdlib |
| **Code** (Verina-style specs) | `CodeSpecOracle` | soundness (reference must pass) · completeness (no wrong impl may pass, via mutation) · vacuity | ✅ via `MockAxleClient`; 🔌 live via `AxleClient` |

## Quickstart (zero dependencies, Python ≥ 3.10)

```bash
python examples/audit_math.py        # numerical oracle, information-theory ladder
python examples/audit_verina.py      # code-spec oracle, Verina-style tasks (offline)
python -m unittest discover -s tests -t .   # 11 tests
```

Run the code-spec audit against the **real Axiom Lean Engine** (free key at
<https://axle.axiommath.ai/app/console>):

```bash
export AXLE_API_KEY=...
python examples/audit_verina.py --live
```

## What it catches (actual output)

Numerical oracle on the information-theory ladder — faithful statements survive,
unfaithful ones are falsified *with the violating instance*:

```
✓ [FAITHFUL    ] kl_nonneg: survived 2000 Monte-Carlo draws
✗ [FALSIFIED   ] kl_nonneg_DROPPED_normalization  ⟵ q=[0.78,1.53,1.22] (Σq=3.53≠1) ⇒ Σ pᵢ·log(pᵢ/qᵢ) = -1.15 < 0
✗ [FALSIFIED   ] data_processing_DROPPED_markov    ⟵ I(X;Z)=0.83 > I(X;Y)=0.05  (Z leaks X directly)
✗ [FALSIFIED   ] entropy_concave_WRONG_direction   ⟵ H(λp+(1-λ)q)=1.08 > λH(p)+(1-λ)H(q)=1.06
? [INCONCLUSIVE] entropy_uniform_vacuous_guard      ⟵ hypothesis satisfied in 0/2000 draws (possibly vacuous)
```

Code-spec oracle on Verina-style tasks — all four faithfulness verdicts:

```
✗ [VACUOUS     ] sort_by_length          ⟵ even the throwaway impl 'all_zeros' satisfies the (length-only) spec
✗ [INCOMPLETE  ] max_lower_bound_only     ⟵ wrong impl 'max_plus_one' passes; spec never pins out ∈ {a,b}
✓ [FAITHFUL    ] abs_value
✗ [UNSOUND     ] abs_strictly_positive    ⟵ spec out>0 rejects the correct abs(0)=0
```

Pre-rendered Markdown in [`reports/`](./reports).

## Layout

```
popper/
  oracle.py      Verdict + Oracle interface (shared abstraction)
  numerical.py   NumericalOracle + the information-theory statement library
  codespec.py    CodeSpecOracle: soundness / completeness / vacuity
  axle.py        Task model + AxleClient (live HTTP) + MockAxleClient (offline)
  mutation.py    Lean mutation operators + input fuzzers (completeness search)
  fixtures.py    representative Verina-style tasks (real data: verina.io)
  audit.py       batch runner + Markdown/terminal reports
examples/  tests/  reports/
```

## Status & roadmap

Working PoC (this repo): the shared oracle + offline math and code audits + live
AXLE client. Next, per [`PROPOSAL.md`](./PROPOSAL.md): counterexample-guided spec
**repair**; audit the **real 189-task Verina** reference specs over live AXLE;
and an API-only self-improvement **flywheel** (oracle-reranked best-of-n + DPO
pairs from oracle labels — no GPU).

**Popper falsifies; it does not certify.** A FAITHFUL verdict means no
counterexample was found within budget. That honesty is the point: it catches the
dominant real-world failures (dropped hypotheses, vacuity, wrong direction,
too-strong/too-weak specs) cheaply, and Lean/AXLE remains the ground truth for
the proof.

## License

Apache-2.0 (see [`LICENSE`](./LICENSE)). The Verina benchmark is CC-BY-SA-4.0 and
is **not** vendored here; load it from <https://verina.io>.

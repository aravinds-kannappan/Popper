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
repair signal (and a clean RL reward) that proof-checking alone cannot give —
then **repairs the statement** until it is faithful.

> Three rungs of trust. (1) LLM writes a proof → no ground truth, silent errors.
> (2) LLM + Lean/AXLE → knows when a *proof* is wrong, blind to spec faithfulness.
> (3) **LLM + Lean/AXLE + Popper** → the only rung that attacks *"is the thing
> we're proving the right thing?"* — the bottleneck Axiom
> [names itself](./PROPOSAL.md).

See [`PROPOSAL.md`](./PROPOSAL.md) for the full thesis, milestones, and Axiom alignment.

---

## One idea, three surfaces

All implement the same `Oracle` interface (`popper/oracle.py`):

| Surface | What it falsifies | Backend | Runs |
|---|---|---|---|
| **Math** (`NumericalOracle`) | autoformalized statements, via Monte-Carlo | pure stdlib | offline now |
| **Code, offline** (`CodeSpecOracle`) | code specs: soundness / completeness / vacuity | executable model | offline now |
| **Code, live** (`popper/verina.py`) | the **real 189-task Verina** specs | **live AXLE** + `native_decide` | with an API key |
| **Repair** (`popper/repair.py`, M2) | drives unfaithful specs → FAITHFUL via counterexamples | — | offline now (+ LLM hook) |

## Quickstart (zero dependencies, Python ≥ 3.10)

```bash
python examples/audit_math.py        # numerical oracle, information-theory ladder
python examples/audit_verina.py      # code-spec oracle, offline fixtures
python examples/repair_demo.py       # M2: counterexample-guided spec repair
python -m unittest discover -s tests -t .   # 15 tests
```

Live audit of the **real Verina benchmark** over the Axiom Lean Engine
(free key at <https://axle.axiommath.ai/app/console>):

```bash
pip install axiom-axle
export AXLE_API_KEY=...
python examples/verina_live_audit.py --limit 8          # audit 8 real tasks
python examples/verina_live_audit.py --tasks verina_basic_1,verina_advanced_1
```

## What it catches (actual output)

**Live Verina spec-faithfulness audit over AXLE** — real tasks, real Lean:

```
✓ [FAITHFUL    ] verina_basic_1: correct outputs accepted; all wrong outputs rejected (on test witnesses)
✓ [FAITHFUL    ] verina_basic_2: correct outputs accepted; all wrong outputs rejected (on test witnesses)
? [INCONCLUSIVE] verina_basic_3: spec not decidable on some witnesses (no Decidable instance / timeout)
... 10 claims | ✓ FAITHFUL 8  ? INCONCLUSIVE 2
```

Each task ships correct `expected` and wrong `unexpected` outputs; Popper checks
`<Name>_postcond <input> <output>` in Lean — **unsound** ⇔ a correct output is
rejected, **incomplete** ⇔ a wrong output is accepted.

**Numerical oracle** — faithful statements survive, unfaithful ones are falsified
*with the violating instance*:

```
✗ [FALSIFIED ] kl_nonneg_DROPPED_normalization  ⟵ q=[0.78,1.53,1.22] (Σq=3.53≠1) ⇒ Σ pᵢ·log(pᵢ/qᵢ) = -1.15 < 0
✗ [FALSIFIED ] data_processing_DROPPED_markov    ⟵ I(X;Z)=0.83 > I(X;Y)=0.05  (Z leaks X directly)
✗ [FALSIFIED ] entropy_concave_WRONG_direction   ⟵ H(λp+(1-λ)q)=1.08 > λH(p)+(1-λ)H(q)=1.06
```

**M2 repair** — every unfaithful spec driven to FAITHFUL by its counterexample:

```
✓ sort_by_length:        ✗VACUOUS    → ✓FAITHFUL   (length-only spec; constant fn passes → add sortedness ∧ permutation)
✓ max_lower_bound_only:  ✗INCOMPLETE → ✓FAITHFUL   (out≥a∧out≥b → also require out ∈ {a,b})
✓ abs_strictly_positive: ✗UNSOUND    → ✓FAITHFUL   (out>0 rejects abs(0)=0 → relax to ≥)
```

Pre-rendered reports in [`reports/`](./reports).

## Layout

```
popper/
  oracle.py      Verdict + Oracle interface (shared abstraction)
  numerical.py   NumericalOracle + the information-theory statement library
  codespec.py    CodeSpecOracle: soundness / completeness / vacuity (offline)
  verina.py      live Verina loader + concurrent spec-faithfulness audit over AXLE
  repair.py      M2: counterexample-guided repair (template / functional / LLM)
  axle.py        Task model + AxleClient (live) + MockAxleClient (offline)
  mutation.py    Lean mutation operators + input fuzzers
  fixtures.py    representative offline tasks (real data: verina.io)
  audit.py       batch runner + Markdown/terminal reports
examples/  tests/  reports/
```

## Status & roadmap

Done: numerical oracle (M1 math) · offline code-spec oracle · **live Verina audit
over AXLE** · **M2 counterexample-guided repair** (offline + LLM hook).
Next ([`PROPOSAL.md`](./PROPOSAL.md)): LLM declarative repair in the *live* loop;
scale the audit across all 189 tasks; API-only self-improvement **flywheel**
(oracle-reranked best-of-n + DPO pairs from oracle labels — no GPU).

**Popper falsifies; it does not certify.** A FAITHFUL verdict means no
counterexample was found within budget — it catches the dominant real-world
failures (dropped hypotheses, vacuity, wrong direction, too-strong/too-weak
specs) cheaply; Lean/AXLE remains the ground truth for the proof.

## License

Apache-2.0 (see [`LICENSE`](./LICENSE)). The Verina benchmark is CC-BY-SA-4.0 and
is **not** vendored here; it is fetched on demand from
[`sunblaze-ucb/verina`](https://github.com/sunblaze-ucb/verina) into a git-ignored cache.

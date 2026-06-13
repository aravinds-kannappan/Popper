# Popper — *falsify the spec, then verify the proof*

**A spec-faithfulness engine that catches the silent failures formal verification can't.**

> Axiom's own thesis: *"Anything that can be specified can be proven. Humans are bad at specifying everything we want."* The proving is increasingly solved (AxiomProver: 120/120 Putnam; 99% on Verina ProofGen vs. o3's 4.9%). **The specification is the bottleneck — and it is the one Axiom named.** Popper attacks it directly, on Axiom's own benchmark, built on Axiom's own engine (AXLE), and generalizes the idea from math to the verified-code frontier they just raised $200M to build.

---

## 0. TL;DR

A Lean compiler tells you **"this proof matches this statement."** It does **not** tell you **"this statement means what you wanted."** That second gap is where verified AI silently fails: a *vacuous* or *too-weak* spec is trivially provable and certifies nothing; a *too-strong* spec rejects correct code. Even a fully formal, 100%-green pipeline can be 100% wrong if the spec is unfaithful.

**Popper adds an independent, executable oracle that *falsifies* specifications** — property-based testing + mutation/metamorphic testing for code, Monte-Carlo/numerical evaluation for math — *before and during* proving. It produces a **counterexample** (an actionable repair signal and a clean RL reward), repairs the *statement* rather than just the proof, and turns spec-faithfulness into a **self-improving flywheel** — a new flywheel layered on top of Axiom's proof-correctness one.

It is built **on the AXLE API** (`check`, `verify_proof`, `disprove`, `theorem2sorry`, `repair_proofs`, …), so it's a contribution to Axiom's ecosystem, not a competitor to it. AXLE answers *"is this proof valid?"* Popper adds the missing half: *"is this statement faithful and worth proving?"*

---

## Build status (this repo)

A working proof-of-concept ships alongside this proposal:
- ✅ **M1** — numerical oracle (information-theory ladder) + offline code-spec oracle (soundness / completeness / vacuity), shared `Oracle` abstraction, 15 tests.
- ✅ **Live Verina audit over AXLE** — the real 189-task benchmark, audited via `native_decide` on each task's `expected` / `unexpected` witnesses through the official `axiom-axle` client. Sample run: 10 tasks → 8 FAITHFUL, 2 INCONCLUSIVE.
- ✅ **M2** — counterexample-guided repair: the offline loop drives VACUOUS / INCOMPLETE / UNSOUND → FAITHFUL, with an `LLMRepairer` hook for live declarative repair.
- ⏳ Next: LLM declarative repair inside the live loop; full-benchmark sweep; API-only self-improvement flywheel.

See `README.md` and `reports/` for runnable demos and rendered output.

## 1. What Axiom actually is (and why this plan is pointed at their center of gravity)

| Signal | Implication for the project |
|---|---|
| **AXLE** = open Lean 4 engine API (MIT). Verbs: `check`, `verify_proof`, `disprove`, `repair_proofs`, `simplify_theorems`, `extract_theorems/decls`, `theorem2sorry`, `sorry2lemma`, `merge`, `normalize`. Python/CLI/HTTP/**MCP**. Free key. | Build *on* AXLE. No local Lean needed. Show fluency with their real product. `disprove` + `theorem2sorry` are the exact primitives a spec-falsifier wants. |
| **Bottleneck they name out loud:** *"anything that can be specified can be proven; humans are bad at specifying."* | The single highest-signal thing to work on is **specification faithfulness**, not "prove more theorems." |
| **$200M Series A (Mar 2026) to verify *AI-generated code*.** 99% (187/189) on **Verina** (codegen-with-proofs) vs. o3's 4.9%. | Bridge math → code. Anchor on **Verina** — *their* benchmark surface — so results land where they're looking. |
| **Philosophy:** *"verification, not vibes"*; Lean as **ground-truth RL reward** (not GRPO/RLHF plausibility); the **verified-data flywheel** (deterministic checks → clean training data → self-improvement). | Frame the oracle as a *new ground-truth signal* and a *new flywheel* for spec quality. Speaks directly to the RL hiring axis. |
| **Hiring:** *"math and AI, reinforcement learning, ML infrastructure, and formal methods … the frontier where mathematical proof meets machine intelligence."* | One project that visibly touches all four axes (below). |

**The Verina numbers are the whole argument in one line.** Best model o3: **72.6% code correct, 4.9% proofs, but only 52.3% spec soundness+completeness.** Axiom has crushed ProofGen (→99%). **The unsolved axis is spec faithfulness (~52%).** That is exactly the surface Popper targets.

---

## 2. The gap: verification proves the proof, not the intent

There are three rungs of trust. Most of the world is on rung 1; Axiom moved the field to rung 2; **rung 3 is open, and it's where Popper lives.**

| Rung | What you get | What still fails *silently* |
|---|---|---|
| **1. LLM writes/explains a proof** (Claude, GPT, Gemini, informal) | A fluent, plausible artifact | **No ground truth.** Errors are invisible: unjustified steps, hidden cases, off-by-one, circular reasoning. You need a human expert to find them — the attention bottleneck Axiom names. RLHF/GRPO optimize *plausibility*, not *truth*. |
| **2. LLM + Lean/AXLE** (Axiom today) | Deterministic proof: the proof *does* match the statement | **Spec blindness.** The checker is silent on whether the *statement* is faithful. A vacuous spec (`∀ x, True`) proves instantly. A too-weak spec ("output has same length as input") is satisfied by a sort that returns its input unchanged. **An LLM that writes both the spec *and* the code will write a spec its bugs happen to satisfy — green, and wrong.** |
| **3. LLM + Lean/AXLE + falsification oracle** (Popper) | Proof matches statement **and** an independent executable oracle has *tried and failed to break the statement* | The honest residual: falsification ≠ certification (see §5). But the dominant real-world failures — dropped hypotheses (integrability, measurability, no-arbitrage), vacuity, wrong direction, off-by-one bounds — are exactly what an executable oracle catches cheaply, *with a counterexample*. |

**This is the crisp answer to "why is this better than an LLM that writes proofs?"**
- Rung 1 has no notion of being wrong. Rung 2 knows when a *proof* is wrong but not when a *statement* is meaningless. Popper is the only rung that attacks "**is the thing we're proving the right thing?**" — which is precisely the bottleneck Axiom says is unsolved.
- And unlike a human reviewer, the oracle is **cheap, automatable, and returns a counterexample** — so it doubles as a *training signal*, not just a check.

> **Demo that motivates the whole project (cheap, day-1):** take *N* tasks, have a frontier model produce (a) informal proofs and (b) Lean specs+code+proofs. Measure: what fraction of informal proofs are silently wrong? What fraction of *formally green* specs are vacuous or too-weak under the oracle? Publishing that gap *is* the hook.

---

## 3. What changed from the "Doob" draft — and why it's stronger

Your instinct — **a numerical oracle as a second, independent ground truth** — is the best idea in the original plan. I kept it and sharpened *what it's pointed at*.

| Doob (original) | Popper (revised) | Why the change |
|---|---|---|
| Thesis = "autoformalize an **underserved math domain** (info theory / stochastic calc / quant)." | Thesis = "**spec faithfulness** is the named bottleneck; falsify specs with an executable oracle." | The domain isn't what Axiom cares about; the **spec problem is what they explicitly call hard.** Re-point at the bottleneck. |
| Oracle = "**dual verification**," implied to rival Lean. | Oracle = **independent falsifier of the *specification*** (a pre-filter + repair signal). Lean stays the ground truth for *proofs*. | Epistemically honest (falsify ≠ certify) and correctly positioned. Overclaiming "dual verification" to a sophisticated audience backfires. |
| Three theorem ladders across three fields; continuous-time Itô (M4) as a frontier flex. | **One math testbed** (probability/info-theory — where numerical shadows are natural), demoted to *a* domain, not *the* point. Itô calculus → "roadmap," not MVP. | Narrow + deep + complete beats broad + aspirational for an application. Continuous Itô in Lean is a multi-year library effort, not a solo demo. |
| Math only. | **Math *and* code**, unified by one idea (executable falsification of specs), with **Verina** as the code anchor. | Bridges their roots (math) to their funded future (verified code). This is the single biggest alignment upgrade. |
| Build a harness around the Lean REPL. | Build **on the AXLE API** (`disprove`, `theorem2sorry`, `repair_proofs`, MCP). | Uses their actual product; no local Lean; shows you'd be a contributor on day one. |
| Expert iteration as a heavy GPU milestone. | **Two-tier self-improvement:** cheap (oracle-reranked best-of-n, DPO pairs from oracle labels) → scalable (LoRA if compute exists). | Demonstrable without a cluster; scales if there's one. De-risks the RL story. |

Net: same beautiful core, re-aimed from "a niche math domain" to "**the bottleneck Axiom named, on the benchmark Axiom touts, via the engine Axiom ships, bridging to the market Axiom just funded.**"

---

## 4. The system

```
  intent (NL theorem  |  code+description)
        │
        ▼
  GENERATOR ── LLM writes Lean statement/spec  (+ code, if Verina)
        │
        ▼
  ┌───────────────── FALSIFICATION ORACLE (the differentiator) ─────────────────┐
  │  CODE  : property-based testing · fuzzing · mutation testing of the SPEC      │
  │          (does a deliberately-broken impl still satisfy it? → spec too weak)  │
  │          (does the reference impl violate it?            → spec too strong)   │
  │  MATH  : Monte-Carlo / numerical evaluation of the STATEMENT                  │
  │          (sample distributions/paths; does the inequality/identity break?)    │
  │  + vacuity probes (∃ a model where it's non-trivially true? is it ⇔ True?)    │
  └──────────────────────────────────────────────────────────────────────────────┘
        │                                   │
   survives (plausibly faithful)      FALSIFIED → counterexample
        ▼                                   │
  PROVER  (AXLE: check / verify_proof    ┌──┘
           / repair_proofs)              ▼
        │                          COUNTEREXAMPLE-GUIDED
   compiles & axiom-clean?          STATEMENT REPAIR   ↺
   (no sorry; #print axioms;        (add the dropped hypothesis;
    reject native_decide abuse)      tighten the vacuous spec)
        ├─ NO  → repair proof (AXLE) ↺
        └─ YES → VERIFIED + FAITHFUL ──► verified-spec dataset
                                              │
                                   SELF-IMPROVEMENT FLYWHEEL
                              (oracle labels → rerank / DPO / LoRA →
                               better GENERATOR; better spec-faithfulness)  ↺
```

**Anti-cheating is native to AXLE + the oracle.** Reject `sorry`/`admit`; run `#print axioms`; flag `native_decide` abuse and **vacuously-true statements** (the prime cheat in *these* settings is smuggling out a hypothesis — integrability/measurability/no-arbitrage in math, a permutation/termination clause in code — which the oracle is purpose-built to catch).

---

## 5. The oracle, precisely (honesty is the selling point)

**Claim:** the oracle is a cheap, automatable **falsifier** that returns counterexamples and catches the *dominant* spec-faithfulness failures.
**Not claimed:** it *certifies* faithfulness. (That's undecidable in general; a spec can pass all sampled cases and still be subtly wrong.) Lean remains the ground truth for the *proof*; the oracle is ground truth for *"this statement is breakable."*

Two falsification engines, one principle:

- **Code (Lean / Verina):**
  - *Too-strong (unsound):* run the **reference implementation** against the spec; if it violates, the spec over-constrains. (Verina pioneered this check.)
  - *Too-weak (incomplete/vacuous):* **mutation-test the spec** — auto-generate *wrong* implementations (mutants) and adversarial inputs (property-based/fuzzing); if a mutant *passes* the spec, the spec failed to constrain. **Going beyond Verina's fixed hand-written test suites to *active* counterexample search** is the methodological delta.
- **Math (Mathlib probability/info-theory testbed):** every inequality/identity has a numerical shadow. Estimate entropy/KL/MI from samples and check the inequality; simulate the relevant process and check the identity. A violation ⇒ the autoformalization dropped a hypothesis ⇒ repair the *statement*.
- **Both:** **vacuity/triviality probes** (is the statement provably equivalent to `True`? is there any model where it's non-trivially satisfied?), partly via AXLE `disprove` + lightweight model search.

**Relationship to Verina (credit + delta).** Verina already scores spec *soundness & completeness* with reference impls + fixed tests. Popper's contributions over it: (1) **active** falsification (mutation + fuzzing + numerical) instead of fixed tests; (2) **closing the loop** — counterexample-guided *repair*, not just a score; (3) **a self-improvement flywheel** that turns the metric into a training signal; (4) **generalization beyond code** to autoformalized math; (5) **delivered on AXLE** as reusable open tooling.

---

## 6. Self-improvement — the flywheel Axiom will care about

Axiom's flywheel: deterministic proof checks → clean verified data → better prover. **Popper adds a second flywheel for *spec quality*:**

- The oracle emits **ground-truth labels for free**: *faithful* (survives falsification, reference passes, mutants rejected, non-vacuous) vs. *unfaithful* (+ a counterexample).
- **Tier 1 (no GPU):** oracle-reranked **best-of-n** spec generation; collect **DPO/preference pairs** (faithful ≻ unfaithful) and counterexample→repair traces. Show pass@k and faithfulness rise from reranking alone.
- **Tier 2 (if compute):** **LoRA fine-tune** the spec/statement generator on the verified-faithful corpus + repair traces. Report base → +oracle-rerank → +repair → +fine-tune.

This is the **RL story in miniature, with a real reward**: not RLHF plausibility, but an executable, deterministic faithfulness signal — exactly Axiom's "verification, not vibes."

---

## 7. Headline results we'd report (shape, not bravado)

Not chasing SOTA. Claiming a **working, novel, reproducible spec-falsification + repair loop** with honest ablations:

1. **Spec-faithfulness audit of Verina (the wedge, day-1 artifact).** Run the active oracle over Verina's 189 **reference** specs *and* model-generated SpecGen outputs. Report: *X%* of generated specs (and possibly some **gold** specs) are unsound or incomplete, **with concrete counterexamples.** Finding faithfulness bugs in a respected benchmark's own specs is an attention-grabbing, thesis-proving result that costs almost nothing.
2. **Repair lift:** faithfulness rate **before vs. after** counterexample-guided repair (and downstream: does repairing the spec raise end-to-end verified-and-faithful rate?).
3. **Math testbed:** on a curated probability/info-theory ladder (Gibbs → KL≥0 → log-sum → data-processing → Fano), show the numerical oracle catches *Y%* of dropped-hypothesis autoformalizations that compile-checking alone passes.
4. **Flywheel:** base → +oracle-rerank → +repair → (+LoRA) on faithfulness and pass@k.
5. **Faithfulness reported as its own metric**, separate from compile-rate — because that separation *is* the point.

---

## 8. Milestones (each independently shippable; MVP highlighted)

- **M0 — credibility prereq (non-negotiable).** Lean 4 fluency; **1–2 merged Mathlib PRs** in `MeasureTheory`/`ProbabilityTheory`; *and/or* a contribution to Verina (e.g., a corrected/added reference spec found by the oracle). Cheap, high-trust, directly on-topic.
- ✅ **★ M1 — MVP: Verina spec-faithfulness oracle + audit (on AXLE).** Property-based + mutation + vacuity oracle for Lean specs, driven through the AXLE API. Ship the **audit report** (§7.1) + an open `popper` library + (stretch) an **MCP tool** so any agent can call "is this spec faithful?". *This alone is a stronger Axiom application than most will have.*
- ✅ **M2 — counterexample-guided spec repair.** Close the loop: oracle counterexample → statement repair → re-verify. Report repair lift (§7.2).
- ✅ **M3 — math testbed (numerical oracle).** The probability/info-theory ladder + Monte-Carlo oracle; autoformalize → falsify → repair → prove via AXLE. Proves the principle generalizes beyond code. *(Honors your original probability instinct, scoped to the achievable slice.)*
- **M4 — self-improvement flywheel.** Tier-1 reranking + DPO pairs from oracle labels; Tier-2 LoRA if compute. Base→+oracle→+repair→(+fine-tune) tables.
- **M5 — surface + writeup.** Wrap as `/spec`, `/falsify`, `/repair`, `/verify` (CLI + thin API + minimal playground) over AXLE; arXiv-style report leading with the **three-rung trust ladder** and the **Verina audit**. *Axiom's site references "selected papers" — give them a paper-shaped artifact.*

**MVP = M0 + M1 + M2 on Verina.** Math (M3) and flywheel (M4) are the upside; each milestone stands alone.

---

## 9. How it maps to what Axiom hires for

- **Formal methods:** the entire system is Lean/AXLE-native; the contribution is a missing piece of the verification stack (spec faithfulness).
- **Math + AI:** autoformalization + a measure-theory/probability testbed; the oracle's epistemics (falsify ≠ certify, vacuity, metamorphic relations) are mathematically substantive.
- **Reinforcement learning:** a *real, deterministic* reward for spec quality; reranking → DPO → LoRA with honest ablations — the verified-data flywheel applied to a new axis.
- **ML infrastructure:** a reproducible loop over a remote engine (AXLE) — batching, caching, rate-limit handling (AXLE caps: 20 concurrent w/ key), the eval harness + leaderboard, everything reproducible from configs.

---

## 10. Openness (Oumi-style, license-clean)

- **Code:** Apache-2.0 (patent grant; compatible with Lean/Mathlib/AXLE; avoid GPL contamination).
- **Data:** curated faithful/unfaithful spec corpus + counterexamples under CC-BY-4.0 (note: Verina itself is **CC-BY-SA-4.0** — keep derived data in a separate, share-alike-compatible bucket).
- **Weights:** any LoRA adapters on Hugging Face, Apache-2.0.
- **Eval:** open benchmark + leaderboard; reproducible from configs.

---

## 11. Honest scoping & risks

- **Falsification ≠ certification.** Stated up front, everywhere. The oracle catches the *dominant* failures cheaply; it is not a faithfulness proof. (This honesty is a feature to a research audience.)
- **Verina is small (189) and CC-BY-SA.** Good for a sharp result; respect the license; don't overfit claims to 189 tasks.
- **Mutation/property testing needs executable semantics.** Natural for Verina (it ships tests) and for numerical math; harder for purely abstract statements — scope the testbed to where executable shadows exist (which is most of probability/info-theory).
- **Continuous-time stochastic calculus stays on the roadmap, not the MVP** — the Mathlib library doesn't exist yet; treat as ambitious upside.
- **Model choice is modular.** Generator/repair can be a frontier API model (latest Claude is a strong default for NL→spec and repair) and/or an open prover (DeepSeek-Prover-style); the *contribution is the loop*, not the base model. Verification is always AXLE.
- **Due-diligence note:** the circulating claim that "AXLE is switching to Rocq (AXRE), translating proofs with GPT-2" appears to be **satire/not credible** (the GPT-2 detail is a tell; the live product, docs, and repo are all Lean 4). Plan stays on **Lean 4 / AXLE**. Worth a 1-line confirm with Axiom if you ever cite it.

---

## 12. Immediate next step

Build **M1's wedge** first: point the property/mutation/vacuity oracle at **Verina's reference specs** via the AXLE API and produce the audit. It's a few days of work, needs no GPU, runs on a free AXLE key, and either (a) finds faithfulness bugs in a respected benchmark — a genuine, citable result — or (b) cleanly validates the specs and still demonstrates the tooling. Either way it proves the thesis empirically before any heavy ML, and it's the most honest possible opening move.

---

### Sources
- Axiom — careers & philosophy: https://axiommath.ai/careers · Latent Space interview (Carina Hong): https://www.latent.space/p/axiom
- AXLE — engine/API: https://axle.axiommath.ai/v1/docs/ · repo (MIT): https://github.com/AxiomMath/axiom-lean-engine · MCP server: https://github.com/AxiomMath/axle-mcp-server
- Verified-code direction: https://menlovc.com/perspective/ai-will-write-all-the-code-mathematics-will-prove-it-works/ · https://siliconangle.com/2026/03/12/verifiable-ai-startup-axiom-raises-200m-prove-ai-generated-code-safe-use/
- Verina benchmark: https://arxiv.org/abs/2505.23135 · https://verina.io/
- Mathlib4: https://github.com/leanprover-community/mathlib4

// The research write-up, rendered on the Research tab through the shared
// Markdown component (Markdown + KaTeX). A fuller version lives in
// reports/research.md in the repository.

export const research = String.raw`
# Checking the statement, not just the proof

**What Popper contributes to a formal stack built on AXLE and AxiomProver, and the benchmark that measures it.**

## The structural gap Popper fills

A prover is a verifier. Given a statement $S$ and a candidate proof $\pi$, an engine
like AXLE decides whether $\pi : S$, that is, whether the proof inhabits the type the
statement denotes. That guarantee is real and it is the foundation everything else rests
on. It is also blind in two directions at once, and the two blind spots compound.

The first is **faithfulness**. The verifier checks $\pi$ against $S$; it never checks
$S$ against the author's intent $I$. So whenever $S \neq I$ (the statement is too loose,
too tight, or vacuous), the prover still certifies a valid $\pi : S$ and reports success.
You have proved the wrong theorem, soundly. The second is **well-formedness**. The
verifier only runs once $S$ elaborates. Real input rarely does: typo-heavy Lean,
references to Mathlib lemmas that were renamed or never existed, a wrong implicit
argument. AxiomProver does not degrade on this; it fails at the type-checking phase and
the mathematical idea behind the malformed term is discarded.

Popper is the layer that addresses both before the prover is ever invoked.

## Why the gap matters quantitatively

The proving side is strong; the specifying side is not. On Verina, code paired with
specifications, the strongest general model writes correct *code* roughly 73% of the time
but writes specs that are simultaneously sound and complete only about 52% of the time.
"Sound" means the spec does not reject a correct answer; "complete" means it does not
accept a wrong one. The error mass lives in the statement, and the verifier is
constitutionally unable to see it: it confirms $\pi$ matches $S$, it does not ask whether
$S$ matches $I$.

This is the economic case for a screen. Roughly half of the specifications a prover is
handed in practice are already wrong, and the prover's only response to a wrong spec is
to spend its full budget either (a) certifying a meaningless proof, or (b) failing to
find a proof that cannot exist.

## What Popper does

Popper does not produce proofs. It produces *refutations*. It sits in front of the
prover as a cheap, fast, fault-tolerant screen and performs three jobs the verifier
cannot.

**1. Intent recovery through noise.** Rather than rejecting malformed input, Popper's
agent layer infers the claim the author is gesturing at, recovering the statement behind
the typo, the renamed term, the off-by-one in an implicit argument, and reconstructs a
checkable $S'$ from it. The failure mode is graceful: when it cannot recover intent, it
returns INCONCLUSIVE and hands control back, rather than crashing.

**2. Syntactic interception.** Parse and elaboration faults are caught and repaired at
the buffer, so they never reach, and never stall, the expensive multi-agent proof loop.
The prover only sees statements that already type-check.

**3. Adversarial falsification on the AXLE substrate.** Given a checkable statement,
Popper runs rapid-fire adversarial probes (on the order of tens of milliseconds each)
that try to *break* it. For math this is a Monte-Carlo search; for code it is evaluation
of the spec against known-good and known-bad witnesses on AXLE. When a probe succeeds,
Popper returns the concrete counterexample: the exact vector, matrix, or graph that
exposes the weak premise.

## The falsification engines

**Math.** A statement carries an assumption $A(x)$ and a conclusion $C(x)$; the engine
draws thousands of random $x$ and checks $A(x) \Rightarrow C(x)$. Gibbs' inequality, for
instance, says the KL divergence, a standard measure of how far one distribution is from
another, is never negative:
$$\mathrm{KL}(p \,\|\, q) = \sum_i p_i \log \frac{p_i}{q_i} \ge 0.$$
This holds when $q$ is a genuine distribution, but drop the normalization assumption
$\sum_i q_i = 1$ and it fails; the engine exhibits a $q$ that drives the sum below zero.
The same pattern appears with the data-processing inequality
$X \to Y \to Z \Rightarrow I(X;Z) \le I(X;Y)$: remove the Markov hypothesis and the
engine produces a triple where $Z$ copies $X$ directly. No prover, no API key.

**Code.** Each Verina task ships a correct reference and several wrong implementations.
Popper asks AXLE to evaluate the spec against each. A rejected correct reference means
the spec is too tight (UNSOUND); an accepted wrong implementation means it is too loose
(INCOMPLETE); an accepted nonsense implementation means it constrains nothing (VACUOUS).

The counterexample is what makes this operational rather than diagnostic. A pass/fail
bit tells you a spec is *probably* wrong; a counterexample tells you *which input* breaks
it, which is exactly what is needed to repair it, and which doubles as a clean,
automatic training signal for a repair loop with no human in the path.

## How this changes the AXLE / AxiomProver pipeline

Place Popper before the prover and the compute profile of the whole stack changes.

- **Vacuous and too-weak specs are screened out for free.** AxiomProver would return a
  clean proof of $\forall x,\ \text{true}$ or of "sorted means same length," certifying
  nothing while consuming budget. Popper refutes these in milliseconds, before any proof
  search begins.
- **Unprovable-by-bug specs stop grinding.** A too-strong or simply wrong spec is
  unprovable; the prover can exhaust a long multi-agent search failing on a statement
  that is false because the *spec* has a defect. Popper returns the breaking witness
  immediately and redirects effort from proof search to spec repair.
- **The refutation becomes the repair signal.** The loop is: Popper breaks $S$, the
  witness repairs it to $S^\star$, AxiomProver proves $S^\star$ once it survives
  falsification. Popper keeps the prover's expensive compute on statements that are both
  well-formed and worth proving.

The division of labor is clean: AxiomProver answers "can this be proved, and here is the
proof"; Popper answers "is this a well-formed statement worth proving, and if not, here
is the input that shows why." They are complementary, not competing.

## How Popper differs from LLM approaches

The published numbers explain why Popper is a different kind of tool, not a better model.
The community has largely solved *proving a given statement* and left *checking the
statement* exposed.

**LLM theorem provers are strong, given a statement.** DeepSeek-Prover-V2 reaches 88.9% on
miniF2F-test and solves 49 of 658 PutnamBench problems [2]. Axiom's AxiomProver scored a
perfect 120/120 on Putnam 2025, ahead of the top human competitor (110) and the best
informal AI system (103) [4]. Once the statement is fixed and faithful, finding the proof
is increasingly tractable.

**The statement is where models fail.** On Verina, the strongest model (OpenAI o3) writes
correct code 72.6% of the time, writes specifications that are simultaneously sound and
complete only 52.3% of the time, and produces a complete proof on just 4.9% of tasks [1].
Direct autoformalization is harder still: the canonical study by Wu et al. translates only
25.3% of competition problems into a faithful formal statement [3]. Crucially, that same
work observes that no automated system verifies a translation is correct with high
certainty [3]. That sentence is the entire opening for Popper.

**An LLM-as-judge reads and guesses.** A model asked to grade a spec produces a verdict
with no execution and no witness; it cannot return the input that breaks the statement, and
its judgment inherits the same blind spots as the model that wrote the spec.

| tool | what it optimizes | representative result | counterexample |
|---|---|---|---|
| LLM theorem prover (DeepSeek-Prover-V2, AxiomProver) | a proof, given a statement | 88.9% miniF2F [2]; 120/120 Putnam 2025 [4] | no |
| LLM spec writer / autoformalizer | a formal statement from intent | 52.3% sound+complete [1]; 25.3% faithful autoformalization [3] | no |
| LLM-as-judge | a verdict by reading the spec | guesses, no execution | no |
| Popper | breaking the statement | 99% of planted bugs caught, 0 false alarms | every time |

Provers and judges sit downstream of a statement they assume is right. Popper is the only
one of these that attacks that assumption and the only one that returns the input proving
it wrong, which is why it belongs in front of AXLE and AxiomProver [5] rather than beside
them.

## Three levels of trust

1. A model writes a proof in prose. It reads well and guarantees nothing.
2. A model plus a prover (Lean or AXLE). You get a real proof that matches the statement,
   and you are still trusting the statement. $\forall x,\ \text{true}$ proves instantly;
   "sorted" defined as "same length" is satisfied by code that does nothing.
3. A model plus a prover plus Popper. The proof matches the statement *and* an independent
   oracle has tried to break the statement, either failing or returning the input that
   breaks it.

Provers live on level two. Popper is what makes level three possible.

## The benchmark

346 statements labelled by hand (faithful or unfaithful, with the bug kind recorded for
the broken ones), three checkers run over the same set: the proof checker (accepts
anything that is a valid proof), an LLM judge (a model reads the statement and guesses,
no execution), and Popper.

| checker | unfaithful caught | false alarms | counterexample | F1 |
|---|---|---|---|---|
| Popper | 176/178 (99%) | 0/165 (0%) | every time | 0.99 |
| Proof checker | 0/178 (0%) | 0/165 (0%) | never | 0.00 |
| LLM judge | runnable live | runnable live | never | runnable live |

The score is 0.99, not a flat 1.00, by design. Easy bugs fail on about half of all
inputs, so Popper catches them in a couple of draws. Subtle bugs fail on a tiny fraction
of inputs, so catching them scales with the draw budget: at 100 draws Popper catches 6 of
10 subtle bugs; by 10,000 draws it catches all 10. F1 is a real number that moves with
effort, plotted on the budget chart on the Benchmark tab. The proof checker scores zero
at every budget, which is not a weakness but the point, since refuting a bad spec is not
an operation a proof checker performs. The LLM judge can guess, but never returns the
input that breaks the spec.

## What Popper adds

1. A checker for the statement, not the proof.
2. Tolerance for malformed input, where the prover crashes at type-checking.
3. A counterexample, not a score: the concrete input that breaks the spec.
4. A clean training signal: the witness that fixes a spec is also a reward.
5. Honest INCONCLUSIVE when a spec cannot be decided on a case, instead of a guess.

## Limits

Popper breaks statements; it does not certify them. A FAITHFUL verdict means no
counterexample was found within the budget, not that none exists; proving the absence of
a counterexample is undecidable in general, so Popper never claims it. Random sampling can
miss a bug that hides on a measure-zero set of inputs, though dropped assumptions and
flipped directions, the bugs that dominate in practice, fail on a large fraction of
inputs and surface immediately. Intent recovery is best-effort and heuristic, but its
failure mode is graceful rather than a hard crash. Lean and AXLE remain the final word on
the proof itself.

## References

1. Z. Ye et al. **VERINA: Benchmarking Verifiable Code Generation.** arXiv:2505.23135.
   The source of the 72.6% code / 52.3% spec / 4.9% proof figures and the soundness and
   completeness definitions. [arxiv.org/abs/2505.23135](https://arxiv.org/abs/2505.23135)
2. DeepSeek-AI. **DeepSeek-Prover-V2: Advancing Formal Mathematical Reasoning via
   Reinforcement Learning for Subgoal Decomposition.** arXiv:2504.21801. 88.9% on
   miniF2F-test, 49/658 on PutnamBench.
   [arxiv.org/abs/2504.21801](https://arxiv.org/abs/2504.21801)
3. Y. Wu, A. Q. Jiang, W. Li, M. N. Rabe, C. Staats, M. Jamnik, C. Szegedy.
   **Autoformalization with Large Language Models.** arXiv:2205.12615. 25.3% faithful
   autoformalization, and the observation that no automated system verifies a translation
   with high certainty. [arxiv.org/abs/2205.12615](https://arxiv.org/abs/2205.12615)
4. Axiom Math. **AxiomProver and the AXLE Lean Engine.** The 120/120 Putnam 2025 result
   (top human 110, best informal AI 103) and the public Lean verification API Popper
   drives. [axiommath.ai](https://axiommath.ai) and
   [axle.axiommath.ai](https://axle.axiommath.ai)
5. AxiomMath. **AXLE: the Axiom Lean Engine (client and verification API).**
   [github.com/AxiomMath/axiom-lean-engine](https://github.com/AxiomMath/axiom-lean-engine)
   and [leanprover-community/mathlib4](https://github.com/leanprover-community/mathlib4),
   the Lean and Mathlib substrate underneath.
`;

// The research write-up, rendered on the Research tab through the shared
// Markdown component (Markdown + KaTeX). A fuller version lives in
// reports/research.md in the repository.
//
// NOTE: this is a String.raw template literal. Do not use backticks or
// dollar-brace interpolation anywhere in the content; KaTeX math uses single
// $ ... $ inline. Keep macros basic so nothing renders as a KaTeX error.

export const research = String.raw`
# Falsify the statement, then prove it

**A short research note on why checking the statement is a different problem from checking the proof, and how Popper attacks it. References at the end.**

## The idea

Popper is named after Karl Popper, and the name is the argument: a universal claim can
never be verified by piling up confirmations, only refuted by a single counterexample [6].
A specification is a universal claim, $\forall i,\ \mathrm{pre}(i) \Rightarrow \mathrm{post}(i, f(i))$,
so it has exactly that shape. Refuting it costs one bad input; confirming it would cost
checking them all. Popper the tool leans entirely on that asymmetry. It does not certify a
statement, it tries to break it, and a clean run means "survived," not "proven."

## Why the proof misses it

A proof checker decides whether a proof matches a statement: in type-theory terms, whether
a term inhabits the type, $\pi : S$ [9]. What it never checks is whether $S$ is the
statement you meant. That arrow, from intent to formal statement, is unverified, and it is
where models fail. A spec can be wrong in three ways, each one true yet unfaithful:

- too strong, when it rejects a correct program;
- too weak, when it accepts a wrong one;
- vacuous, when it constrains nothing, like $\forall x,\ \text{true}$.

A vacuous statement is a theorem, so the proof checker is perfectly happy. Being true and
being faithful are different properties, and certifying faithfulness is undecidable in
general (Rice's theorem [8]). That is why Popper refutes rather than certifies, and reports
INCONCLUSIVE when it genuinely cannot decide.

## Popper vs the LLM models

LLM provers are strong once the statement is fixed: DeepSeek-Prover-V2 reaches 88.9% on
miniF2F [2], and AxiomProver scored a perfect 120/120 on Putnam 2025, ahead of the top
human (110) and the best informal AI (103) [4]. The statement is the weak link. On Verina
the best model writes specs that are both sound and complete only 52.3% of the time [1],
and direct autoformalization is faithful only 25.3% of the time [3]. A model that writes or
grades a spec inherits those rates and hands back no witness. Popper is not a generator
scored by accuracy; it is an executable oracle that returns the input that breaks the spec,
catching 99% of planted bugs with zero false alarms.

## Popper vs AXLE

AXLE already exposes a disprove tool that returns counterexamples, so why a separate layer?
Because disprove answers "is this proposition false," a question about $S$ alone, while
faithfulness is a relation between $S$ and intent. A vacuous spec is true, so disprove finds
nothing to disprove, even though the spec is useless. Popper makes faithfulness falsifiable
by adding witnesses, a correct reference and known-wrong implementations, and asking AXLE to
evaluate the spec on each: reject the correct one means unsound, accept a wrong one means
incomplete, accept nonsense means vacuous. On math it skips AXLE entirely and samples
locally with no prover. And it classifies the failure, so each verdict names a different
repair, where disprove only ever says false or not.

## Popper vs AxiomProver

AxiomProver proves; Popper screens. Proof search is expensive and breaking is cheap, so the
order matters. A vacuous spec proves easily and certifies nothing; a buggy spec is
unprovable and burns a long search. Popper settles both up front, and its counterexample
drives the fix, after which AxiomProver proves the repaired statement. The screen keeps the
expensive prover pointed only at statements worth proving.

## References

1. Z. Ye et al. **VERINA: Benchmarking Verifiable Code Generation.** arXiv:2505.23135.
   [arxiv.org/abs/2505.23135](https://arxiv.org/abs/2505.23135)
2. DeepSeek-AI. **DeepSeek-Prover-V2.** arXiv:2504.21801. 88.9% miniF2F-test, 49/658 PutnamBench.
   [arxiv.org/abs/2504.21801](https://arxiv.org/abs/2504.21801)
3. Y. Wu et al. **Autoformalization with Large Language Models.** arXiv:2205.12615. 25.3%
   faithful autoformalization. [arxiv.org/abs/2205.12615](https://arxiv.org/abs/2205.12615)
4. Axiom Math. **AxiomProver and the AXLE Lean Engine.** Putnam 2025 result and the public
   Lean API Popper drives. [axiommath.ai](https://axiommath.ai),
   [axle.axiommath.ai](https://axle.axiommath.ai)
5. AxiomMath. **AXLE: the Axiom Lean Engine,** over
   [mathlib4](https://github.com/leanprover-community/mathlib4).
   [github.com/AxiomMath/axiom-lean-engine](https://github.com/AxiomMath/axiom-lean-engine)
6. K. Popper. **The Logic of Scientific Discovery.** 1959.
7. K. Popper. **Conjectures and Refutations.** 1963.
8. H. G. Rice. **Classes of Recursively Enumerable Sets and Their Decision Problems.** AMS, 1953.
9. W. A. Howard. **The Formulae-as-Types Notion of Construction.** 1980.
`;

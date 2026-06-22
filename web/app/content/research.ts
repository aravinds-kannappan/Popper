// The research write-up, rendered on the Research tab through the shared
// Markdown component (Markdown + KaTeX). A fuller version lives in
// reports/research.md in the repository.
//
// NOTE: this is a String.raw template literal. Do not use backticks or ${ }
// anywhere in the content below; KaTeX math uses $ ... $ and $$ ... $$.

export const research = String.raw`
# Falsify the statement, then prove it

**A long note on why checking the statement is a different problem from checking the proof, what logic says about that gap, and how Popper attacks it. Citations are at the end.**

## The name is the thesis

Popper is named after Karl Popper, and the name is the whole argument. Popper's claim
about scientific knowledge is that universal theories can never be *verified*, only
*falsified* [6, 7]. No number of confirming observations proves "all swans are white"; a
single black swan refutes it. A theory earns trust not by being proven but by surviving
honest attempts to break it, and Popper called the survivors *corroborated*, never
*verified*. He was strict about that difference.

Formal verification has the opposite instinct. It wants certificates, and for the *proof*
it can have one: a proof checker decides, with certainty, whether a proof is valid. But the
object that actually carries your meaning is not the proof, it is the *statement*, and a
statement is a universal claim about all inputs. That is exactly the kind of object Popper
said you cannot establish by accumulating confirmations. Popper the tool takes the
philosophy literally: it does not certify a statement, it tries to break it, and it reports
the survivors as corroborated rather than proven.

## The logical asymmetry that makes this work

Write a specification in its usual shape, a universally quantified implication over an
input domain $D$:
$$S \;\equiv\; \forall i \in D,\ \mathrm{pre}(i) \Rightarrow \mathrm{post}(i, f(i)).$$
By De Morgan over the quantifier, $S$ is equivalent to the *non-existence* of a
counterexample:
$$S \;\equiv\; \neg\,\exists\, i \in D,\ \big(\mathrm{pre}(i) \,\wedge\, \neg\,\mathrm{post}(i, f(i))\big).$$
The two directions cost wildly different amounts. To *refute* $S$ you need one witness $a$
with $\mathrm{pre}(a)$ true and $\mathrm{post}(a, f(a))$ false. To *confirm* $S$ you must
range over all of $D$, which is infinite or astronomically large. A single refutation is
decisive and cheap; confirmation is unbounded. This is the same asymmetry Popper built his
epistemology on, and it is why a tool that hunts for counterexamples can be fast and honest
where a tool that tries to certify cannot.

And the counterexample is not only a verdict, it is *information*. A pass or fail bit tells
you a spec is suspect. The witness $a$ tells you *which* input breaks it, which is exactly
the data a human or a model needs to repair the spec, and the same witness doubles as a
reward signal for an automated repair loop with no human in the path.

## Where the asymmetry bites: the statement, not the proof

It helps to be exact about what a proof checker guarantees. Under the Curry and Howard
correspondence [9], a proof $\pi$ of a proposition $S$ is a term inhabiting the type $S$:
the judgment is $\pi : S$. A checker like Lean or AXLE decides that inhabitation relation,
and that is a genuine, certain guarantee.

But the guarantee is *conditional on $S$ being the proposition you meant*. The type $S$ is
a formal object; whether its denotation carves out the behaviors you intended is a modeling
question that lives outside the proof system. Call the author's intent $I$. The real
pipeline is
$$I \;\rightsquigarrow\; S \;\rightarrow\; \pi,$$
and the checker only ever audits the second arrow. The first arrow, the autoformalization
of intent into a formal statement, is unchecked, and it is where the errors concentrate.

There are three ways that first arrow goes wrong, and each is a logical defect with its own
witness:

- **Too strong (unsound).** $S$ rejects a correct reference $f^\star$: there is an $i$ with
  $\mathrm{pre}(i) \wedge \neg\,\mathrm{post}(i, f^\star(i))$. The witness is a correct
  output the spec wrongly forbids.
- **Too weak (incomplete).** $S$ accepts a known-wrong implementation $f^-$: there is an
  $i$ with $\mathrm{pre}(i) \wedge \mathrm{post}(i, f^-(i))$. The witness is a wrong output
  the spec wrongly admits.
- **Vacuous.** The precondition is unsatisfiable, or the postcondition is trivially true,
  so $S$ constrains nothing and is satisfied by anything, including nonsense.

The decisive point is vacuity. A vacuous $S$ is *true*: $\forall x,\ \text{true}$ is a
theorem, and "sorted means the output has the same length as the input" is a perfectly
consistent proposition. A proof of a vacuous statement is valid. There is nothing for a
proof checker to object to, because *being true* and *being faithful* are different
properties, and the checker only sees the first. This is the formal restatement of the
Verina soundness and completeness conditions, $\hat\phi \subseteq \phi$ (do not reject a
correct program) and $\phi \subseteq \hat\phi$ (do not miss one) [1]: faithfulness is a
relation between the written spec $\hat\phi$ and the intended set $\phi$, and no inspection
of $\hat\phi$ in isolation can recover it.

## Why this is undecidable, and why that is fine

Could we just build a decision procedure for faithfulness? No, and the reason is
structural. Faithfulness of $S$ to intent is a non-trivial semantic property, and by Rice's
theorem every non-trivial semantic property of programs is undecidable [8]. Proving that
*no* counterexample to $S$ exists is, in general, equivalent to deciding such a property,
so no tool can certify faithfulness in the general case.

This is why Popper is deliberately a *refuter*, not a *certifier*. It is sound in the
direction that matters: every counterexample it returns is a real defect, reproducible on
demand. It is necessarily incomplete: a FAITHFUL verdict means "survived the budget," not
"no counterexample exists." That is not a weakness swept under the rug, it is the honest
shape of the problem, and it is Popper's corroboration-not-verification stance rendered in
code. When the signal is too thin to decide a case, Popper returns INCONCLUSIVE rather than
guessing.

## Why the imbalance matters: the numbers

The proving side is strong and getting stronger. DeepSeek-Prover-V2 reaches 88.9% on
miniF2F-test and solves 49 of 658 PutnamBench problems [2]; Axiom's AxiomProver scored a
perfect 120/120 on Putnam 2025, ahead of the top human competitor (110) and the best
informal AI system (103) [4]. Given a faithful statement, finding the proof is increasingly
tractable.

The specifying side is not. On Verina, the strongest model (OpenAI o3) writes correct code
72.6% of the time, writes specifications that are simultaneously sound and complete only
52.3% of the time, and produces a complete proof on just 4.9% of tasks [1]. Direct
autoformalization is harder still: Wu et al. translate only 25.3% of competition problems
into a faithful formal statement, and note that no automated system verifies a translation
is correct with high certainty [3]. Roughly half of real specifications are already wrong,
and the verifier is blind to every one of them.

## Popper versus the LLM models

An LLM that writes a proof in prose produces something that reads well and guarantees
nothing; fluent text is not a correct result. An LLM prover plus a checker gives a real
proof, but of the statement *as written*, faithful or not. An LLM that writes the spec
inherits the 52.3% and 25.3% failure rates above. An LLM-as-judge that grades a spec
produces a verdict with no execution and no witness, inheriting the same blind spots as the
model that wrote the spec, since both are the same kind of unanchored next-token guess.
None of these returns the input that breaks the statement.

Popper differs in *kind*, not degree. It is not a generator scored by accuracy; it is an
executable oracle scored by whether its counterexamples are real. On the labelled benchmark
it flags 99% of planted bugs with a witness every time and raises zero false alarms, against
a proof checker that flags none by construction.

## Popper versus AXLE

This comparison needs care, because AXLE already exposes a *disprove* tool that returns
counterexamples. So what does Popper add over calling disprove directly?

The difference is the *question being asked*. AXLE disprove takes a closed, type-checking
proposition $S$ and searches for a refutation, an input that makes $S$ false. That is a
question about $S$ alone. Faithfulness is not a property of $S$ alone; it is a *relation*
between $S$ and the intended behavior $I$. The gap shows up sharply at vacuity: a vacuous
spec is *true*, so there is nothing for disprove to disprove. Hand disprove the statement
$\forall x,\ \text{true}$ and it correctly reports no counterexample, which is precisely the
wrong answer for a screen, because the statement is useless. Disprove cannot see
uselessness, because uselessness is not falsity. Soundness and completeness failures sit in
the same blind spot: a too-weak spec is satisfiable, just by the wrong programs, and
satisfiability is not what disprove tests.

Popper reframes faithfulness so that it becomes falsifiable in the first place. It
introduces *witnesses*, a correct reference $f^\star$ and known-wrong implementations
$f^-$, and asks whether the spec sorts them the way intent demands. Now the failure modes
become refutations with concrete witnesses:
$$\underbrace{\exists i,\ \mathrm{pre}(i) \wedge \neg\,\mathrm{post}(i, f^\star(i))}_{\text{UNSOUND}},
\quad
\underbrace{\exists i,\ \mathrm{pre}(i) \wedge \mathrm{post}(i, f^-(i))}_{\text{INCOMPLETE}},
\quad
\underbrace{\text{accepts nonsense}}_{\text{VACUOUS}}.$$
On the code surface Popper drives AXLE to *evaluate* the spec on each witness, using AXLE as
a substrate rather than as the decision procedure. On the math surface Popper does not need
AXLE at all: a local Monte-Carlo engine draws thousands of samples and exhibits a violating
case with no prover and no API key. Three further differences follow:

1. **The verdict vocabulary maps to a repair.** Disprove returns "false, here is a witness"
   or "no counterexample." Popper returns UNSOUND, INCOMPLETE, VACUOUS, FALSIFIED,
   FAITHFUL, or INCONCLUSIVE, and each non-faithful verdict points at a *different* fix:
   relax the spec, strengthen it, add a missing constraint. Verdict plus witness is a repair
   instruction, not just a refutation.
2. **It runs before type-checking.** Disprove needs a well-formed proposition. Popper's
   intent-recovery layer sits in front, reading through typo-heavy Lean and non-existent
   Mathlib terms to reconstruct a checkable statement, so malformed input is repaired
   instead of crashing the pipeline at elaboration.
3. **It is a methodology, not a primitive.** Disprove is one powerful operation. Popper is
   the screening loop built around it: the oracle interface, witness construction, two
   engines, the repair loop, and honest INCONCLUSIVE reporting. AXLE is the engine Popper
   drives [4, 5]; Popper is the question asked with it.

## Popper versus AxiomProver

AxiomProver is the verifier, and a strong one: it answers "can this statement be proved, and
here is the proof" [4]. Popper answers "is this a well-formed statement worth proving, and
if not, here is the input that shows why." The two are complementary, and the order matters
for one reason, economics.

Proof search is expensive, breaking is cheap. A vacuous or too-weak spec proves *easily* and
certifies *nothing*: AxiomProver would return a clean proof of a statement that guarantees
nothing, spending a large budget to produce a worthless certificate. A wrong or too-strong
spec is *unprovable*, so AxiomProver can grind a long multi-agent search against a statement
that is false only because the spec has a bug. Popper settles both cheaply, up front, and
its counterexample drives the repair. The loop is: Popper breaks $S$, the witness repairs it
to $S^\star$, AxiomProver proves $S^\star$ once it survives falsification. Popper keeps the
expensive prover pointed only at statements that are well-formed and worth proving.

## How the engines work

**Math.** A statement carries an assumption $A(x)$ and a conclusion $C(x)$; the engine draws
thousands of random $x$ and checks $A(x) \Rightarrow C(x)$. Gibbs' inequality, for instance,
says the KL divergence, a standard measure of how far one distribution is from another, is
never negative:
$$\mathrm{KL}(p \,\|\, q) = \sum_i p_i \log \frac{p_i}{q_i} \ge 0.$$
It holds when $q$ is a genuine distribution, but drop the normalization assumption
$\sum_i q_i = 1$ and it fails; the engine exhibits a $q$ that drives the sum below zero. The
same pattern appears with the data-processing inequality
$X \to Y \to Z \Rightarrow I(X;Z) \le I(X;Y)$: remove the Markov hypothesis and the engine
produces a triple where $Z$ copies $X$ directly. No prover, no API key.

**Code.** Each Verina task ships a correct reference and several wrong implementations.
Popper asks AXLE to evaluate the spec against each. A rejected correct reference means
UNSOUND, an accepted wrong implementation means INCOMPLETE, an accepted nonsense
implementation means VACUOUS.

## The benchmark

346 statements labelled by hand (faithful or unfaithful, with the bug kind recorded for the
broken ones), three checkers run over the same set: the proof checker (accepts anything that
is a valid proof), an LLM judge (a model reads the statement and guesses, no execution), and
Popper.

| checker | unfaithful caught | false alarms | counterexample | F1 |
|---|---|---|---|---|
| Popper | 176/178 (99%) | 0/165 (0%) | every time | 0.99 |
| Proof checker | 0/178 (0%) | 0/165 (0%) | never | 0.00 |
| LLM judge | runnable live | runnable live | never | runnable live |

The score is 0.99, not a flat 1.00, by design. Easy bugs fail on about half of all inputs,
so Popper catches them in a couple of draws. Subtle bugs fail on a tiny fraction of inputs,
so catching them scales with the draw budget: at 100 draws Popper catches 6 of 10 subtle
bugs; by 10,000 draws it catches all 10. F1 is a real number that moves with effort, plotted
on the budget chart on the Benchmark tab. The proof checker scores zero at every budget,
which is the point, not a weakness, since refuting a bad spec is not an operation a proof
checker performs.

## What Popper adds

1. A checker for the statement, not the proof.
2. Tolerance for malformed input, where the prover crashes at type-checking.
3. A counterexample, not a score: the concrete input that breaks the spec.
4. A classification, not just a refutation: UNSOUND, INCOMPLETE, or VACUOUS, each a
   different repair.
5. Honest INCONCLUSIVE when a spec cannot be decided on a case, instead of a guess.

## Limits

Popper breaks statements; it does not certify them. A FAITHFUL verdict means no
counterexample was found within the budget, not that none exists; by Rice's theorem [8],
proving the absence of a counterexample is undecidable in general, so Popper never claims
it. Random sampling can miss a bug that hides on a measure-zero set of inputs, though
dropped assumptions and flipped directions, the bugs that dominate in practice, fail on a
large fraction of inputs and surface immediately. Intent recovery is best-effort and
heuristic, but its failure mode is graceful rather than a hard crash. Lean and AXLE remain
the final word on the proof itself.

## References

1. Z. Ye et al. **VERINA: Benchmarking Verifiable Code Generation.** arXiv:2505.23135.
   Source of the 72.6% code / 52.3% spec / 4.9% proof figures and the soundness and
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
   (top human 110, best informal AI 103) and the public Lean verification API Popper drives.
   [axiommath.ai](https://axiommath.ai) and
   [axle.axiommath.ai](https://axle.axiommath.ai)
5. AxiomMath. **AXLE: the Axiom Lean Engine (client and verification API),** over
   [leanprover-community/mathlib4](https://github.com/leanprover-community/mathlib4).
   [github.com/AxiomMath/axiom-lean-engine](https://github.com/AxiomMath/axiom-lean-engine)
6. K. Popper. **The Logic of Scientific Discovery.** 1959. Falsifiability as the criterion of
   demarcation; the impossibility of verifying universal statements.
7. K. Popper. **Conjectures and Refutations: The Growth of Scientific Knowledge.** 1963.
   Corroboration through surviving refutation, not verification.
8. H. G. Rice. **Classes of Recursively Enumerable Sets and Their Decision Problems.**
   Transactions of the AMS, 1953. Every non-trivial semantic property of programs is
   undecidable.
9. W. A. Howard. **The Formulae-as-Types Notion of Construction.** 1980 (circulated 1969).
   The Curry and Howard correspondence between proofs and programs, propositions and types.
`;

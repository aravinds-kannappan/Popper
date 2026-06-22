"use client";

import Ladder from "./Ladder";

export default function Overview({ go }: { go: (tab: string) => void }) {
  return (
    <div>
      <section className="hero">
        <div className="tag">falsify the statement, then prove it</div>
        <h1>Don&apos;t burn proof compute on a statement that was wrong to begin with</h1>
        <p>
          Provers like AXLE and AxiomProver crash at type-checking on typo-heavy Lean or
          non-existent Mathlib terms, and they will happily certify a flawless proof of a spec that
          was never the one you meant. Popper is the buffer in front of them. It reads through the
          noise to recover the claim you&apos;re gesturing at, intercepts the syntax faults, and runs
          rapid-fire (~30ms) adversarial fuzzing on AXLE&apos;s substrate to break weak premises. When
          it succeeds it hands back the exact matrix or graph counterexample, before a single cycle of
          expensive, long-running proof search is spent.
        </p>
        <div className="cta">
          <button className="btn" onClick={() => go("benchmark")}>
            See the benchmark
          </button>
          <button className="btn ghost" onClick={() => go("agent")}>
            Try the agent
          </button>
          <a className="btn ghost" href="https://github.com/aravinds-kannappan/Popper">
            View on GitHub
          </a>
        </div>
      </section>

      <section className="section">
        <h2>
          What the buffer does <span className="sub">three jobs the prover cannot</span>
        </h2>
        <p className="note" style={{ maxWidth: 760, marginBottom: 14 }}>
          A prover is a verifier: it only runs once a statement type-checks, and even then it checks
          the proof against the statement, never the statement against what you meant. Popper sits in
          front and closes both gaps before any proof compute is spent.
        </p>
        <div className="grid2">
          <div className="panel pad">
            <h3 className="h3">1. Recover intent through noise</h3>
            <p className="note">
              Instead of rejecting flawed Lean, Popper deduces the claim you are gesturing at,
              recovering the statement behind a typo, a renamed Mathlib term, or a wrong implicit
              argument, and reconstructs something checkable. When it cannot, it says so honestly
              rather than guessing.
            </p>
          </div>
          <div className="panel pad">
            <h3 className="h3">2. Intercept the syntax faults</h3>
            <p className="note">
              Parse and elaboration failures are caught and repaired at the buffer, so they never
              reach the expensive multi-agent proof loop. The prover only ever sees statements that
              already type-check.
            </p>
          </div>
          <div className="panel pad">
            <h3 className="h3">3. Fuzz the statement adversarially</h3>
            <p className="note">
              On AXLE&apos;s substrate, Popper fires rapid-fire (~30ms) probes that try to break the
              statement. When one lands, you get the concrete input that exposes the weak premise: the
              vector, matrix, or graph, not just a pass/fail bit.
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>
          Why it goes in front of the prover{" "}
          <span className="sub">proving is expensive, breaking is cheap</span>
        </h2>
        <p className="note" style={{ maxWidth: 760, marginBottom: 14 }}>
          AxiomProver answers &quot;can this statement be proved.&quot; Popper answers &quot;is this
          the right, well-formed statement to prove.&quot; Roughly half of real specs are already
          wrong, and the prover&apos;s only response to a wrong spec is to certify a meaningless proof
          or grind on one that cannot exist. Popper settles both cheaply, up front.
        </p>
        <div className="grid2">
          <div className="panel pad">
            <h3 className="h3">Vacuous and too-weak specs</h3>
            <p className="note">
              AxiomProver would return a clean proof of &quot;for all x, true&quot; or of &quot;sorted
              means same length,&quot; certifying nothing while spending budget. Popper refutes these
              in milliseconds, before any proof search begins.
            </p>
          </div>
          <div className="panel pad">
            <h3 className="h3">Wrong and too-strong specs</h3>
            <p className="note">
              A spec that is false because of a bug is unprovable, so the prover can exhaust a long
              search failing on it. Popper returns the breaking witness immediately, and that witness
              is also the repair signal: fix the spec, then prove the fixed one.
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>
          The three levels of trust <span className="sub">where Popper lives</span>
        </h2>
        <p className="note" style={{ maxWidth: 760, marginBottom: 14 }}>
          A prover like Lean or AXLE confirms a proof matches a statement. It never asks whether the
          statement is the one you meant, so a wrong statement just gives a valid proof of the wrong
          thing. Popper adds the missing check: it looks at the statement, not the proof, and returns
          a counterexample when the statement is broken.
        </p>
        <Ladder />
      </section>

      <section className="section">
        <h2>
          Two falsification engines <span className="sub">one common interface</span>
        </h2>
        <div className="grid2">
          <div className="panel pad">
            <h3 className="h3">Math</h3>
            <p className="note">
              Most inequalities can be checked with numbers. The engine draws thousands of random
              cases and watches for one that breaks the statement. This is a Monte-Carlo check, a
              fancy name for &quot;try a lot of random inputs and see if anything fails.&quot; If the
              statement dropped an assumption or flipped a direction, some case breaks it, and that
              case is the counterexample. Runs locally, no prover, no API key.
            </p>
          </div>
          <div className="panel pad">
            <h3 className="h3">Code</h3>
            <p className="note">
              Each Verina task comes with a correct answer and several wrong ones. Popper asks AXLE to
              evaluate the spec on each. A rejected correct answer means the spec is too tight. An
              accepted wrong answer means it is too loose. An accepted nonsense answer means it is
              empty.
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>
          The result <span className="sub">measured, not asserted</span>
        </h2>
        <div className="cards">
          <div className="card link" onClick={() => go("benchmark")}>
            <div className="k">0 vs 178</div>
            <div className="l">broken specs the proof checker catches, against the 178 Popper finds given enough search.</div>
          </div>
          <div className="card link" onClick={() => go("benchmark")}>
            <div className="k">every one</div>
            <div className="l">of Popper&apos;s detections comes with a concrete input that breaks the spec.</div>
          </div>
          <div className="card link" onClick={() => go("research")}>
            <div className="k">~52%</div>
            <div className="l">is how often the best general model writes a sound, complete spec on Verina.</div>
          </div>
        </div>
      </section>
    </div>
  );
}

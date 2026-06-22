"use client";

import Ladder from "./Ladder";

export default function Overview({ go }: { go: (tab: string) => void }) {
  return (
    <div>
      <section className="hero">
        <div className="tag">semantic-fault tolerance for formal provers</div>
        <h1>Don&apos;t burn proof compute on a statement that was wrong to begin with</h1>
        <p>
          Provers like AXLE and AxiomProver crash at type-checking on typo-heavy Lean or
          non-existent Mathlib terms, and they will happily certify a flawless proof of a spec that
          was never the one you meant. Popper is the buffer in front of them. It reads through the
          noise to recover the claim you&apos;re gesturing at, intercepts the syntax faults, and runs
          rapid-fire (~30ms) adversarial fuzzing on AXLE&apos;s substrate to break weak premises —
          handing back the exact matrix or graph counterexample before a single cycle of expensive,
          long-running proof search is spent.
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
          What Popper does that the usual tools cannot{" "}
          <span className="sub">three levels of trust</span>
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
          How it works <span className="sub">one checker, two engines</span>
        </h2>
        <div className="grid2">
          <div className="panel pad">
            <h3 className="h3">Math</h3>
            <p className="note">
              Most inequalities can be checked with numbers. The engine draws thousands of random
              cases and watches for one that breaks the statement. This is a Monte-Carlo check, which
              is just a fancy name for "try a lot of random inputs and see if anything fails". If the
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
            <div className="l">of Popper's detections comes with a concrete input that breaks the spec.</div>
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

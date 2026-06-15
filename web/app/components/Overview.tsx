"use client";

import Ladder from "./Ladder";

export default function Overview({ go }: { go: (tab: string) => void }) {
  return (
    <div>
      <section className="hero">
        <div className="tag">check that the statement is right, then prove it</div>
        <h1>The proof can be perfect and the result still wrong</h1>
        <p>
          When you verify code or math with a computer, you write a statement of what is supposed to
          be true (a "spec") and prove your work matches it. The weak spot is the statement itself:
          it can be too loose, too tight, or empty, and the proof still passes. I built Popper to go
          after the statement directly. It tries to break the statement, and when it succeeds it
          hands you the exact input that breaks it.
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

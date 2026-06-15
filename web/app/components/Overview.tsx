"use client";

import Ladder from "./Ladder";

export default function Overview({ go }: { go: (tab: string) => void }) {
  return (
    <div>
      <section className="hero">
        <div className="tag">falsify the spec, then verify the proof</div>
        <h1>Is the thing we are proving the right thing?</h1>
        <p>
          A Lean checker proves that a proof matches a statement. It is silent on whether the
          statement means what you intended. Popper adds an executable oracle that tries to{" "}
          <b>break</b> the statement and returns a concrete counterexample when it can, on math and
          on the real Verina code benchmark, over the Axiom Lean Engine (AXLE).
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
          Why this is different <span className="sub">three rungs of trust</span>
        </h2>
        <Ladder />
      </section>

      <section className="section">
        <h2>
          How it works <span className="sub">one oracle, two engines</span>
        </h2>
        <div className="grid2">
          <div className="panel pad">
            <h3 className="h3">Math</h3>
            <p className="note">
              Every inequality has a numerical shadow. A statement carries a hypothesis and a
              conclusion, and the oracle tests the implication over thousands of sampled instances. A
              dropped hypothesis or a flipped direction breaks on some draw, and that draw is the
              counterexample. Runs locally, no prover, no API key.
            </p>
          </div>
          <div className="panel pad">
            <h3 className="h3">Code</h3>
            <p className="note">
              Each Verina task ships a correct output and several wrong ones. Popper asks AXLE to
              evaluate the postcondition on those witnesses. A rejected correct output means the spec
              is too strong; an accepted wrong output means it is too weak; an accepted garbage output
              means it is vacuous.
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
            <div className="k">14/14</div>
            <div className="l">unfaithful specs caught by Popper. The proof checker catches zero.</div>
          </div>
          <div className="card link" onClick={() => go("benchmark")}>
            <div className="k">100%</div>
            <div className="l">of those detections came with a concrete counterexample.</div>
          </div>
          <div className="card link" onClick={() => go("research")}>
            <div className="k">~52%</div>
            <div className="l">spec soundness and completeness for the best general model on Verina.</div>
          </div>
        </div>
      </section>
    </div>
  );
}

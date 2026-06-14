import { results } from "./lib/results";
import Ladder from "./components/Ladder";
import Dashboard from "./components/Dashboard";
import Chat from "./components/Chat";

export default function Home() {
  return (
    <main className="wrap">
      <section className="hero">
        <div className="tag">Popper · falsify the spec, then verify the proof</div>
        <h1>Is the thing we&apos;re proving the right thing?</h1>
        <p>
          A Lean checker proves a proof matches a statement — it is silent on whether the
          statement means what you intended. <b>Popper</b> adds an executable oracle that{" "}
          <b>falsifies</b> specifications and returns counterexamples, on math and on the real
          Verina code benchmark, over the Axiom Lean Engine (AXLE). Below: the trust ladder, live
          audit results, and a Claude agent that reasons the Popper way and runs AXLE live.
        </p>
      </section>

      <section className="section">
        <h2>
          Why this is different <span className="sub">three rungs of trust</span>
        </h2>
        <Ladder />
      </section>

      <section className="section">
        <h2>
          Audit results <span className="sub">produced by the oracle</span>
        </h2>
        <Dashboard data={results as any} />
      </section>

      <section className="section">
        <h2>
          Ask the Popper agent <span className="sub">general-purpose Claude + live AXLE</span>
        </h2>
        <p className="note">
          Ask any math or coding question. The agent applies the Popper method — for checkable
          claims it tries to <b>falsify</b> via AXLE and reports the real counterexample instead
          of just asserting an answer.
        </p>
        <Chat />
      </section>

      <div className="foot">
        Built on <a href="https://axle.axiommath.ai">AXLE</a> and{" "}
        <a href="https://github.com/sunblaze-ucb/verina">Verina</a>. Popper falsifies; it does not
        certify — a FAITHFUL verdict means no counterexample was found within budget.
      </div>
    </main>
  );
}

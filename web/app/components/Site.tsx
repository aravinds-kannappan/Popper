"use client";

import { useState } from "react";
import Overview from "./Overview";
import Benchmark from "./Benchmark";
import Dashboard from "./Dashboard";
import Research from "./Research";
import Chat from "./Chat";
import { results } from "../lib/results";

const TABS: [string, string][] = [
  ["overview", "Overview"],
  ["benchmark", "Benchmark"],
  ["audits", "Audits"],
  ["research", "Research"],
  ["agent", "Agent"],
];

export default function Site() {
  const [tab, setTab] = useState("overview");

  return (
    <>
      <header className="nav">
        <div className="nav-inner">
          <div className="brand" onClick={() => setTab("overview")}>
            <span className="logo">◭</span> Popper
          </div>
          <nav className="nav-tabs">
            {TABS.map(([key, label]) => (
              <button
                key={key}
                className={`nav-tab ${tab === key ? "active" : ""}`}
                onClick={() => setTab(key)}
              >
                {label}
              </button>
            ))}
          </nav>
          <a className="nav-gh" href="https://github.com/aravinds-kannappan/Popper">
            GitHub
          </a>
        </div>
      </header>

      <main className="wrap">
        {tab === "overview" && <Overview go={setTab} />}

        {tab === "benchmark" && (
          <section className="section first">
            <h2>
              Benchmark <span className="sub">Popper vs the proof checker vs an LLM judge</span>
            </h2>
            <Benchmark />
          </section>
        )}

        {tab === "audits" && (
          <section className="section first">
            <h2>
              Audit results <span className="sub">produced by the oracle</span>
            </h2>
            <Dashboard data={results as any} />
          </section>
        )}

        {tab === "research" && (
          <section className="section first">
            <h2>
              Research <span className="sub">what Popper adds to the field</span>
            </h2>
            <Research />
          </section>
        )}

        {tab === "agent" && (
          <section className="section first">
            <h2>
              Ask the Popper agent <span className="sub">Claude with live AXLE tools</span>
            </h2>
            <p className="note">
              Ask any math or coding question. For a checkable claim the agent tries to{" "}
              <b>falsify</b> it through AXLE and reports the real counterexample instead of just
              asserting an answer. Math is typeset, so you see proper notation rather than raw LaTeX.
            </p>
            <Chat />
          </section>
        )}

        <div className="foot">
          Built on <a href="https://axle.axiommath.ai">AXLE</a> and{" "}
          <a href="https://github.com/sunblaze-ucb/verina">Verina</a>. Popper falsifies; it does not
          certify. A FAITHFUL verdict means no counterexample was found within the search budget.
        </div>
      </main>
    </>
  );
}

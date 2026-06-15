"use client";

import { useState } from "react";
import Overview from "./Overview";
import Benchmark from "./Benchmark";
import AgentLab from "./AgentLab";
import Dashboard from "./Dashboard";
import Research from "./Research";
import { results } from "../lib/results";

const TABS: [string, string][] = [
  ["agent", "Live demo"],
  ["overview", "Overview"],
  ["benchmark", "Oracle benchmark"],
  ["audits", "Audits"],
  ["research", "Research"],
];

export default function Site() {
  const [tab, setTab] = useState("agent");

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
              Oracle engine benchmark <span className="sub">the Monte-Carlo engine on a labelled set of bugs</span>
            </h2>
            <p className="note" style={{ marginBottom: 12 }}>
              This is the offline, reproducible benchmark of Popper&apos;s detection engine. For the
              live, conversation-driven benchmark against other models, use the Live demo tab and send
              a few messages.
            </p>
            <Benchmark />
          </section>
        )}

        {tab === "audits" && (
          <section className="section first">
            <h2>
              Audit results <span className="sub">what the checker found</span>
            </h2>
            <Dashboard data={results as any} />
          </section>
        )}

        {tab === "research" && (
          <section className="section first">
            <h2>
              Research <span className="sub">what Popper adds, in plain English</span>
            </h2>
            <Research />
          </section>
        )}

        {tab === "agent" && (
          <section className="section first">
            <h2>
              Popper in action <span className="sub">chat, then benchmark it against other models</span>
            </h2>
            <AgentLab />
          </section>
        )}

        <div className="foot">
          Built on <a href="https://axle.axiommath.ai">AXLE</a> and{" "}
          <a href="https://github.com/sunblaze-ucb/verina">Verina</a>. Popper breaks statements; it
          does not certify them. A FAITHFUL verdict means no counterexample was found within the
          budget, not that none exists.
        </div>
      </main>
    </>
  );
}

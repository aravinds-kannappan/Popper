"use client";

import { useState } from "react";
import bench from "../data/benchmark.json";

const PRETTY: Record<string, string> = {
  popper: "Popper",
  proof_checker: "Proof checker (AXLE / Lean)",
  llm_judge: "LLM judge",
};

function pct(x: number): string {
  return `${Math.round(x * 100)}%`;
}

function verdictClass(v: string): string {
  const u = (v || "").toUpperCase();
  if (u === "FAITHFUL") return "badge faithful";
  if (u === "INCONCLUSIVE") return "badge warn";
  return "badge bad";
}

type Surface = "all" | "math" | "code" | "verina";

export default function Benchmark() {
  const data: any = bench;
  const judges: string[] = data.judges;
  const scores: Record<string, any> = data.scores;
  const [surface, setSurface] = useState<Surface>("all");

  const rows: any[] = surface === "all" ? data.rows : data.rows.filter((r: any) => r.surface === surface);

  return (
    <div>
      <p className="note" style={{ marginBottom: 16 }}>
        {data.n_items} labelled claims across math, code, and live Verina tasks. The task is simple:
        flag the unfaithful specs and leave the faithful ones alone. Three judges run over the same
        corpus. The math half needs no API key and reproduces with{" "}
        <code>python examples/run_benchmark.py</code>.
      </p>

      <div className="cards" style={{ marginBottom: 20 }}>
        {Object.entries(data.surfaces).map(([name, s]: any) => (
          <div className="card" key={name}>
            <div className="k">{s.total}</div>
            <div className="l">
              {name}: {s.faithful} faithful, {s.unfaithful} unfaithful
              {s.vacuity ? `, ${s.vacuity} vacuity` : ""}
            </div>
          </div>
        ))}
      </div>

      <h3 className="h3">Headline</h3>
      <div className="panel" style={{ marginBottom: 8 }}>
        <table>
          <thead>
            <tr>
              <th>Judge</th>
              <th>Unfaithful caught (recall)</th>
              <th>False positives</th>
              <th>Counterexample yield</th>
              <th>F1</th>
            </tr>
          </thead>
          <tbody>
            {judges.map((j) => {
              const s = scores[j];
              return (
                <tr key={j}>
                  <td>{PRETTY[j] || j}</td>
                  <td className="mono">
                    {s.true_positives}/{s.n_unfaithful} ({pct(s.recall_unfaithful)})
                  </td>
                  <td className="mono">
                    {s.false_positives}/{s.n_faithful} ({pct(s.false_positive_rate)})
                  </td>
                  <td className="mono">{pct(s.counterexample_yield)}</td>
                  <td className="mono">{s.f1.toFixed(2)}</td>
                </tr>
              );
            })}
            {!data.llm_run && (
              <tr>
                <td>{PRETTY.llm_judge}</td>
                <td className="mono" style={{ color: "var(--muted)" }} colSpan={4}>
                  not run in this pass. The Verina paper reports the best general model near 52%
                  combined spec soundness and completeness, with no counterexample. Re-run with{" "}
                  <code>--llm</code> to fill this row from a live model.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="note" style={{ marginBottom: 24 }}>
        The proof checker scores zero recall no matter how strong the underlying prover is. Catching
        an unfaithful spec is not something a proof checker can do: every spec in the corpus type
        checks, so it accepts all of them. Only Popper returns a concrete counterexample for each
        bug it finds.
      </p>

      <h3 className="h3">Per-item verdicts</h3>
      <div className="tabs" style={{ marginTop: 8 }}>
        {(["all", "math", "code", "verina"] as Surface[]).map((s) => (
          <button key={s} className={`tab ${surface === s ? "active" : ""}`} onClick={() => setSurface(s)}>
            {s}
          </button>
        ))}
      </div>
      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th>Surface</th>
              <th>Gold</th>
              {judges.map((j) => (
                <th key={j}>{j === "proof_checker" ? "Proof checker" : PRETTY[j] || j}</th>
              ))}
              <th>Counterexample</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r: any, i: number) => (
              <tr key={i}>
                <td className="mono">{r.name}</td>
                <td>{r.surface}</td>
                <td>
                  <span className={verdictClass(r.gold)}>{r.gold}</span>
                </td>
                {judges.map((j) => (
                  <td key={j}>
                    <span className={verdictClass(r[`${j}_verdict`])}>{r[`${j}_verdict`]}</span>
                  </td>
                ))}
                <td className="mono" style={{ color: "var(--muted)", maxWidth: 320 }}>
                  {r.popper_counterexample || ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

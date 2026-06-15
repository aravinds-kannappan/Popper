"use client";

import { useState } from "react";
import type { Interaction } from "./Chat";

const COLORS: Record<string, string> = {
  "Popper agent": "#3fb950",
  "Opus (no tools)": "#7aa2ff",
  "AXLE alone": "#d29922",
};

type CI = { mean: number; lo: number; hi: number };
type Sys = {
  name: string;
  metrics: { accuracy: number; precision: number; recall: number; f1: number; mcc: number; counterexample_yield: number; avg_quality: number };
  ci: Record<string, CI>;
};
type Data = {
  model: string; ran_at: string; n_messages: number; n_scored: number;
  bootstrap_samples: number; axle_decided: number; axle_used: number; systems: Sys[]; items: any[];
};

const pct = (x: number) => `${Math.round(x * 100)}%`;
const f2 = (x: number) => x.toFixed(2);

// bar chart of one metric across the systems, with bootstrap error bars
function MetricBars({ title, sub, systems, metric, asPct = true, min = 0, max = 1 }: {
  title: string; sub: string; systems: Sys[]; metric: string; asPct?: boolean; min?: number; max?: number;
}) {
  const W = 440, H = 200, padL = 30, padB = 40, padT = 14, innerH = H - padB - padT, innerW = W - padL - 12;
  const slot = innerW / systems.length;
  const y = (v: number) => padT + innerH * (1 - (v - min) / (max - min));
  return (
    <div className="chart">
      <div className="chart-title">{title}</div>
      <div className="chart-sub">{sub}</div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={title}>
        {[min, (min + max) / 2, max].map((t) => (
          <g key={t}>
            <line x1={padL} y1={y(t)} x2={W - 12} y2={y(t)} stroke="#232a39" />
            <text x={padL - 5} y={y(t) + 3} textAnchor="end" fontSize="9" fill="#9aa4b2">{asPct ? Math.round(t * 100) : t.toFixed(1)}</text>
          </g>
        ))}
        {systems.map((s, i) => {
          const ci: CI = s.ci[metric] || { mean: (s.metrics as any)[metric], lo: (s.metrics as any)[metric], hi: (s.metrics as any)[metric] };
          const v = ci.mean;
          const bw = Math.min(70, slot * 0.5), x = padL + slot * i + (slot - bw) / 2;
          const top = y(Math.max(min, v));
          const base = y(min);
          return (
            <g key={s.name}>
              <rect x={x} y={Math.min(top, base)} width={bw} height={Math.abs(base - top)} rx={3} fill={COLORS[s.name] || "#7aa2ff"} />
              <line x1={x + bw / 2} y1={y(ci.lo)} x2={x + bw / 2} y2={y(ci.hi)} stroke="#e6e9ef" strokeWidth={1.5} />
              <line x1={x + bw / 2 - 5} y1={y(ci.lo)} x2={x + bw / 2 + 5} y2={y(ci.lo)} stroke="#e6e9ef" strokeWidth={1.5} />
              <line x1={x + bw / 2 - 5} y1={y(ci.hi)} x2={x + bw / 2 + 5} y2={y(ci.hi)} stroke="#e6e9ef" strokeWidth={1.5} />
              <text x={x + bw / 2} y={top - 6} textAnchor="middle" fontSize="11" fontWeight={700} fill="#e6e9ef">{asPct ? pct(v) : f2(v)}</text>
              <text x={x + bw / 2} y={H - padB + 14} textAnchor="middle" fontSize="9" fill="#e6e9ef">{s.name.replace(" (no tools)", "")}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function ci(s: Sys, k: string, asPct = true): string {
  const c = s.ci[k];
  if (!c) return asPct ? pct((s.metrics as any)[k]) : f2((s.metrics as any)[k]);
  const f = asPct ? pct : f2;
  return `${f(c.mean)} [${f(c.lo)}, ${f(c.hi)}]`;
}

export default function LiveBenchmark({ interactions }: { interactions: Interaction[] }) {
  const [data, setData] = useState<Data | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true); setErr(null);
    try {
      const res = await fetch("/api/benchmark", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ interactions }),
      });
      const j = await res.json();
      if (!res.ok || j.error) throw new Error(j.error || res.statusText);
      setData(j);
    } catch (e: any) {
      setErr(String(e?.message || e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel pad" style={{ marginTop: 16 }}>
      <h3 className="h3" style={{ marginTop: 0 }}>Live benchmark from your conversation</h3>
      <p className="note" style={{ marginTop: 0 }}>
        Built from the {interactions.length} message{interactions.length === 1 ? "" : "s"} you just sent.
        For each one, a plain model (Opus, no tools) answers, AXLE on its own contributes its raw
        result from your chat, and an evaluator agent decides the truth and grades everyone. The
        results are then bootstrapped to 500 resamples for confidence intervals.
      </p>

      {!data && (
        <button className="btn" onClick={run} disabled={busy}>
          {busy ? "Running models and evaluator..." : "Build the benchmark"}
        </button>
      )}
      {err && (
        <p className="note" style={{ color: "var(--red)" }}>
          Could not run: {err}. This needs <code>ANTHROPIC_API_KEY</code> on the server (set on the deployed site).
        </p>
      )}

      {data && (
        <>
          <p className="note">
            {data.n_scored} of {data.n_messages} messages were checkable claims and got scored. AXLE
            on its own broke {data.axle_decided} of them outright (from your chat). Graded by{" "}
            {data.model}; the plain baseline is {data.model} with no tools; bootstrapped to{" "}
            {data.bootstrap_samples} resamples.
          </p>

          <div className="chart-grid">
            <MetricBars title="Accuracy" sub="claims answered correctly (95% CI)" systems={data.systems} metric="accuracy" />
            <MetricBars title="F1, catching false claims" sub="precision and recall combined (95% CI)" systems={data.systems} metric="f1" />
            <MetricBars title="MCC" sub="balanced score, -1 to 1 (95% CI)" systems={data.systems} metric="mcc" asPct={false} min={-1} max={1} />
            <MetricBars title="Counterexample yield" sub="false claims given a valid witness (95% CI)" systems={data.systems} metric="counterexample_yield" />
          </div>

          <div className="panel" style={{ marginTop: 8 }}>
            <table>
              <thead>
                <tr><th>system</th><th>accuracy</th><th>F1</th><th>MCC</th><th>counterex. yield</th><th>avg quality</th></tr>
              </thead>
              <tbody>
                {data.systems.map((s) => (
                  <tr key={s.name}>
                    <td>{s.name}</td>
                    <td className="mono">{ci(s, "accuracy")}</td>
                    <td className="mono">{ci(s, "f1")}</td>
                    <td className="mono">{ci(s, "mcc", false)}</td>
                    <td className="mono">{ci(s, "counterexample_yield")}</td>
                    <td className="mono">{s.metrics.avg_quality.toFixed(1)}/5</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="note" style={{ margin: "10px 0 6px" }}>Per claim:</p>
          <div className="panel">
            <table>
              <thead>
                <tr><th>your message</th><th>truth</th>{data.systems.map((s) => <th key={s.name}>{s.name.replace(" (no tools)", "")}</th>)}</tr>
              </thead>
              <tbody>
                {data.items.map((it, i) => (
                  <tr key={i}>
                    <td style={{ maxWidth: 280 }}>{it.question}</td>
                    <td><span className={`badge ${it.truth === "TRUE" ? "faithful" : it.truth === "FALSE" ? "warn" : "bad"}`}>{it.truth}</span></td>
                    {data.systems.map((s) => {
                      const g = it.grades[s.name];
                      return <td key={s.name}>{g ? <span className={`badge ${g.correct ? "faithful" : "bad"}`}>{g.verdict}</span> : "-"}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button className="btn ghost" style={{ marginTop: 12 }} onClick={run} disabled={busy}>
            {busy ? "Running..." : "Run again"}
          </button>
        </>
      )}
    </div>
  );
}

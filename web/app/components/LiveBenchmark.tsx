"use client";

import { useEffect, useState } from "react";

const GREEN = "#3fb950";
const BLUE = "#7aa2ff";
const CACHE_KEY = "popper_live_benchmark_v1";

type Sys = {
  accuracy: number; precision: number; recall: number; f1: number; mcc: number;
  counterexample_yield: number; avg_quality: number;
};
type Data = {
  model: string; ran_at: string; axle_live: boolean; n_items: number;
  metrics: { popper: Sys; plain: Sys };
  items: any[];
  cached?: boolean;
};

const pct = (x: number) => `${Math.round(x * 100)}%`;
const f2 = (x: number) => x.toFixed(2);

// grouped two-bar comparison, inline SVG
function Compare({ title, sub, plain, popper, max = 1, asPct = true }: {
  title: string; sub: string; plain: number; popper: number; max?: number; asPct?: boolean;
}) {
  const W = 300, H = 150, padB = 26, padT = 22, padL = 8, innerH = H - padB - padT;
  const bars = [{ label: "Plain model", v: plain, c: BLUE }, { label: "Popper agent", v: popper, c: GREEN }];
  const slot = (W - padL) / bars.length;
  return (
    <div className="chart">
      <div className="chart-title">{title}</div>
      <div className="chart-sub">{sub}</div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={title}>
        <line x1={padL} y1={padT + innerH} x2={W} y2={padT + innerH} stroke="#232a39" />
        {bars.map((b, i) => {
          const h = Math.max(0, (b.v / max) * innerH);
          const bw = 70, x = padL + slot * i + (slot - bw) / 2, y = padT + innerH - h;
          return (
            <g key={i}>
              <rect x={x} y={y} width={bw} height={h} rx={3} fill={b.c} />
              <text x={x + bw / 2} y={y - 5} textAnchor="middle" fontSize="12" fontWeight={700} fill="#e6e9ef">
                {asPct ? pct(b.v) : f2(b.v)}
              </text>
              <text x={x + bw / 2} y={H - 8} textAnchor="middle" fontSize="10" fill="#9aa4b2">{b.label}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function ok(v: boolean) {
  return <span className={`badge ${v ? "faithful" : "bad"}`}>{v ? "correct" : "wrong"}</span>;
}

export default function LiveBenchmark() {
  const [data, setData] = useState<Data | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(force = false) {
    setBusy(true); setErr(null);
    try {
      if (!force) {
        const cached = sessionStorage.getItem(CACHE_KEY);
        if (cached) { setData(JSON.parse(cached)); setBusy(false); return; }
      }
      const res = await fetch("/api/benchmark", { method: "POST" });
      const j = await res.json();
      if (!res.ok || j.error) throw new Error(j.error || res.statusText);
      setData(j);
      sessionStorage.setItem(CACHE_KEY, JSON.stringify(j));
    } catch (e: any) {
      setErr(String(e?.message || e));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { run(false); /* eslint-disable-next-line */ }, []);

  return (
    <div style={{ marginBottom: 28 }}>
      <p className="note" style={{ marginBottom: 12 }}>
        This runs live when the page loads. For each claim, the <b>Popper agent</b> (Claude with live
        AXLE) and a <b>plain model</b> (Claude, no tools) each answer, then a separate{" "}
        <b>evaluator agent</b> grades both against the known answer. The numbers below are those
        grades, so they are a real range, not a fixed score.
      </p>

      {busy && !data && (
        <div className="panel pad note">
          Running the agents and the evaluator over the claim set. This makes several Claude and AXLE
          calls, so it can take up to a minute the first time...
        </div>
      )}

      {err && !data && (
        <div className="panel pad">
          <p className="note" style={{ margin: 0 }}>
            Live run unavailable: {err}. This needs <code>ANTHROPIC_API_KEY</code> and{" "}
            <code>AXLE_API_KEY</code> set on the server (they are configured on the deployed site).
          </p>
          <button className="btn ghost" style={{ marginTop: 10 }} onClick={() => run(true)}>Retry</button>
        </div>
      )}

      {data && (
        <>
          <div className="chart-grid">
            <Compare title="Accuracy" sub="claims answered correctly" plain={data.metrics.plain.accuracy} popper={data.metrics.popper.accuracy} />
            <Compare title="F1 (catching false claims)" sub="harmonic mean of precision and recall" plain={data.metrics.plain.f1} popper={data.metrics.popper.f1} />
            <Compare title="MCC" sub="balanced score in -1..1; higher is better" plain={data.metrics.plain.mcc} popper={data.metrics.popper.mcc} max={1} asPct={false} />
            <Compare title="Counterexample yield" sub="false claims given a valid witness" plain={data.metrics.plain.counterexample_yield} popper={data.metrics.popper.counterexample_yield} />
          </div>

          <div className="panel" style={{ marginTop: 8 }}>
            <table>
              <thead>
                <tr><th>system</th><th>accuracy</th><th>precision</th><th>recall</th><th>F1</th><th>MCC</th><th>counterex. yield</th><th>avg quality</th></tr>
              </thead>
              <tbody>
                {([["Plain model", data.metrics.plain], ["Popper agent", data.metrics.popper]] as [string, Sys][]).map(([name, m]) => (
                  <tr key={name}>
                    <td>{name}</td>
                    <td className="mono">{pct(m.accuracy)}</td>
                    <td className="mono">{pct(m.precision)}</td>
                    <td className="mono">{pct(m.recall)}</td>
                    <td className="mono">{f2(m.f1)}</td>
                    <td className="mono">{f2(m.mcc)}</td>
                    <td className="mono">{pct(m.counterexample_yield)}</td>
                    <td className="mono">{m.avg_quality.toFixed(1)}/5</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="note" style={{ margin: "10px 0 6px" }}>
            Per claim ({data.n_items} total, graded by {data.model}{data.axle_live ? ", AXLE live" : ", AXLE not available"}
            {data.cached ? ", cached" : ""}):
          </p>
          <div className="panel">
            <table>
              <thead>
                <tr><th>claim</th><th>truth</th><th>plain model</th><th>Popper agent</th><th>Popper counterexample</th></tr>
              </thead>
              <tbody>
                {data.items.map((it) => (
                  <tr key={it.id}>
                    <td style={{ maxWidth: 320 }}>{it.question}</td>
                    <td><span className={`badge ${it.truth === "TRUE" ? "faithful" : "warn"}`}>{it.truth}</span></td>
                    <td>{ok(it.plain.conclusion_correct)}</td>
                    <td>
                      {ok(it.popper.conclusion_correct)}
                      {it.popper.axle_found_counterexample ? <span className="note" style={{ marginLeft: 6 }}>AXLE</span> : null}
                    </td>
                    <td className="mono" style={{ color: "var(--muted)", maxWidth: 280 }}>{it.popper.counterexample || ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button className="btn ghost" style={{ marginTop: 12 }} onClick={() => run(true)} disabled={busy}>
            {busy ? "Running..." : "Run again"}
          </button>
        </>
      )}
    </div>
  );
}

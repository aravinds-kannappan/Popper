"use client";

import bench from "../data/benchmark.json";

const GREEN = "#3fb950";
const RED = "#f85149";
const BLUE = "#7aa2ff";
const MUTED = "#9aa4b2";

type Bar = { label: string; value: number; color: string; note?: string };

// A simple vertical bar chart, drawn as inline SVG so there is no chart
// dependency to install or break.
function VBars({ title, sub, bars, max = 100, unit = "%" }: { title: string; sub?: string; bars: Bar[]; max?: number; unit?: string }) {
  const W = 460;
  const H = 220;
  const padL = 36;
  const padB = 56;
  const padT = 12;
  const innerW = W - padL - 12;
  const innerH = H - padB - padT;
  const slot = innerW / bars.length;
  const bw = Math.min(80, slot * 0.5);

  return (
    <div className="chart">
      <div className="chart-title">{title}</div>
      {sub && <div className="chart-sub">{sub}</div>}
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={title}>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const y = padT + innerH * (1 - t);
          return (
            <g key={t}>
              <line x1={padL} y1={y} x2={W - 12} y2={y} stroke="#232a39" strokeWidth={1} />
              <text x={padL - 6} y={y + 3} textAnchor="end" fontSize="9" fill={MUTED}>
                {Math.round(max * t)}
              </text>
            </g>
          );
        })}
        {bars.map((b, i) => {
          const h = (b.value / max) * innerH;
          const x = padL + slot * i + (slot - bw) / 2;
          const y = padT + innerH - h;
          return (
            <g key={i}>
              <rect x={x} y={y} width={bw} height={h} rx={3} fill={b.color} />
              <text x={x + bw / 2} y={y - 5} textAnchor="middle" fontSize="11" fontWeight={700} fill="#e6e9ef">
                {b.value}
                {unit}
              </text>
              <text x={x + bw / 2} y={H - padB + 16} textAnchor="middle" fontSize="10" fill="#e6e9ef">
                {b.label}
              </text>
              {b.note && (
                <text x={x + bw / 2} y={H - padB + 30} textAnchor="middle" fontSize="9" fill={MUTED}>
                  {b.note}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// A horizontal bar chart for the per-family breakdown.
function HBars({ title, sub, rows }: { title: string; sub?: string; rows: { label: string; total: number; caught: number }[] }) {
  const maxTotal = Math.max(...rows.map((r) => r.total), 1);
  const W = 460;
  const rowH = 26;
  const padL = 132;
  const padR = 28;
  const H = rows.length * rowH + 12;
  const innerW = W - padL - padR;

  return (
    <div className="chart wide">
      <div className="chart-title">{title}</div>
      {sub && <div className="chart-sub">{sub}</div>}
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={title}>
        {rows.map((r, i) => {
          const y = i * rowH + 6;
          const full = (r.total / maxTotal) * innerW;
          const caught = (r.caught / maxTotal) * innerW;
          return (
            <g key={i}>
              <text x={padL - 8} y={y + 13} textAnchor="end" fontSize="10" fill="#e6e9ef">
                {r.label}
              </text>
              <rect x={padL} y={y} width={full} height={16} rx={3} fill="#232a39" />
              <rect x={padL} y={y} width={caught} height={16} rx={3} fill={GREEN} />
              <text x={padL + full + 6} y={y + 13} fontSize="10" fontWeight={700} fill="#e6e9ef">
                {r.caught}/{r.total}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// A line chart with a log x-axis, for the budget sweep.
function LineChart({ title, sub, points }: { title: string; sub?: string; points: { x: number; recall: number; rare: number }[] }) {
  const W = 460;
  const H = 230;
  const padL = 38;
  const padB = 46;
  const padT = 12;
  const innerW = W - padL - 14;
  const innerH = H - padB - padT;
  const xs = points.map((p) => Math.log10(p.x));
  const xmin = Math.min(...xs);
  const xmax = Math.max(...xs);
  const px = (x: number) => padL + ((Math.log10(x) - xmin) / (xmax - xmin)) * innerW;
  const py = (v: number) => padT + innerH * (1 - v / 100);

  const line = (key: "recall" | "rare") =>
    points.map((p, i) => `${i === 0 ? "M" : "L"} ${px(p.x).toFixed(1)} ${py(p[key]).toFixed(1)}`).join(" ");

  return (
    <div className="chart wide">
      <div className="chart-title">{title}</div>
      {sub && <div className="chart-sub">{sub}</div>}
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={title}>
        {[0, 25, 50, 75, 100].map((t) => {
          const y = py(t);
          return (
            <g key={t}>
              <line x1={padL} y1={y} x2={W - 14} y2={y} stroke="#232a39" strokeWidth={1} />
              <text x={padL - 6} y={y + 3} textAnchor="end" fontSize="9" fill={MUTED}>
                {t}
              </text>
            </g>
          );
        })}
        {points.map((p, i) => (
          <text key={i} x={px(p.x)} y={H - padB + 16} textAnchor="middle" fontSize="9" fill={MUTED}>
            {p.x >= 1000 ? `${p.x / 1000}k` : p.x}
          </text>
        ))}
        <text x={padL + innerW / 2} y={H - 6} textAnchor="middle" fontSize="10" fill={MUTED}>
          random draws per statement (log scale)
        </text>
        <path d={line("recall")} fill="none" stroke={BLUE} strokeWidth={2} />
        <path d={line("rare")} fill="none" stroke={GREEN} strokeWidth={2} />
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={px(p.x)} cy={py(p.recall)} r={3} fill={BLUE} />
            <circle cx={px(p.x)} cy={py(p.rare)} r={3} fill={GREEN} />
          </g>
        ))}
        <g>
          <rect x={padL + 8} y={padT + 4} width={10} height={3} fill={GREEN} />
          <text x={padL + 22} y={padT + 9} fontSize="9" fill="#e6e9ef">subtle bugs only</text>
          <rect x={padL + 130} y={padT + 4} width={10} height={3} fill={BLUE} />
          <text x={padL + 144} y={padT + 9} fontSize="9" fill="#e6e9ef">all math bugs</text>
        </g>
      </svg>
    </div>
  );
}

export default function Charts() {
  const data: any = bench;
  const s = data.scores;
  const popperRecall = Math.round(s.popper.recall_unfaithful * 100);
  const checkerRecall = Math.round(s.proof_checker.recall_unfaithful * 100);

  const recallBars: Bar[] = [
    { label: "Popper", value: popperRecall, color: GREEN },
    { label: "LLM judge", value: 52, color: BLUE, note: "Verina paper" },
    { label: "Proof checker", value: checkerRecall, color: RED },
  ];

  const yieldBars: Bar[] = [
    { label: "Popper", value: Math.round(s.popper.counterexample_yield * 100), color: GREEN },
    { label: "LLM judge", value: 0, color: BLUE, note: "no witness" },
    { label: "Proof checker", value: 0, color: RED },
  ];

  const famRows = (data.by_family || []).map((f: any) => ({
    label: f.family,
    total: f.total,
    caught: f.popper || 0,
  }));

  const sweep = (data.sweep || []).map((r: any) => ({
    x: r.budget,
    recall: Math.round(r.recall * 100),
    rare: Math.round(r.rare_recall * 100),
  }));

  return (
    <div>
      <div className="chart-grid">
        <VBars
          title="Unfaithful specs caught"
          sub="percent of the wrong specs each judge flagged (higher is better)"
          bars={recallBars}
        />
        <VBars
          title="Detections that came with a counterexample"
          sub="a concrete input that breaks the spec, not just a yes or no"
          bars={yieldBars}
        />
      </div>
      <div className="chart-grid">
        <HBars
          title="Bugs caught by kind, Popper"
          sub="green is caught, grey track is the total. The proof checker caught zero in every row."
          rows={famRows}
        />
        {sweep.length > 0 && (
          <LineChart
            title="Detection improves with the search budget"
            sub="this is why the score is not a flat 100%: subtle bugs that fire on a tiny fraction of inputs need more draws to find"
            points={sweep}
          />
        )}
      </div>
    </div>
  );
}

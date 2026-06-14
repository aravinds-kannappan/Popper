"use client";

import { useState } from "react";

type Tab = "verina" | "math" | "code" | "repair";
const TABS: [Tab, string][] = [
  ["verina", "Live Verina (AXLE)"],
  ["math", "Numerical (math)"],
  ["code", "Code-spec (offline)"],
  ["repair", "M2 repair"],
];

function badgeClass(verdict: string): string {
  const v = (verdict || "").toUpperCase();
  if (v === "FAITHFUL") return "badge faithful";
  if (v === "INCONCLUSIVE") return "badge warn";
  return "badge bad";
}

function Badge({ verdict }: { verdict: string }) {
  return <span className={badgeClass(verdict)}>{verdict}</span>;
}

export default function Dashboard({ data }: { data: any }) {
  const [tab, setTab] = useState<Tab>("verina");
  const set = data[tab];
  const rows: any[] = set?.results ?? [];
  const isRepair = tab === "repair";

  // summary counts
  const counts: Record<string, number> = set?.summary ?? {};
  const cards: [string, number][] = isRepair
    ? [
        ["tasks", rows.length],
        ["repaired → faithful", rows.filter((r) => r.repaired).length],
      ]
    : Object.entries(counts);

  return (
    <div>
      <div className="tabs">
        {TABS.map(([key, label]) => (
          <button key={key} className={`tab ${tab === key ? "active" : ""}`} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {cards.length > 0 && (
        <div className="cards" style={{ marginBottom: 12 }}>
          <div className="card">
            <div className="k">{rows.length}</div>
            <div className="l">claims</div>
          </div>
          {cards.map(([k, v]) => (
            <div className="card" key={k}>
              <div className="k">{v}</div>
              <div className="l">{k}</div>
            </div>
          ))}
        </div>
      )}

      <div className="panel">
        {isRepair ? (
          <table>
            <thead>
              <tr>
                <th>Task</th>
                <th>Verdict path</th>
                <th>Final</th>
                <th>Repaired?</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="mono">{r.task}</td>
                  <td className="mono" style={{ color: "var(--muted)" }}>{r.verdict_path}</td>
                  <td><Badge verdict={r.final} /></td>
                  <td>{r.repaired ? "✅" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table>
            <thead>
              <tr>
                <th style={{ width: "130px" }}>Verdict</th>
                <th style={{ width: "230px" }}>Claim</th>
                <th>Reason / counterexample</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td><Badge verdict={r.verdict} /></td>
                  <td className="mono">{r.name}</td>
                  <td style={{ color: "var(--muted)" }}>
                    {r.reason}
                    {r.counterexample ? (
                      <div className="mono" style={{ color: "var(--text)", marginTop: 4 }}>⟵ {r.counterexample}</div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

const RUNGS: [string, string, string][] = [
  [
    "1 · LLM writes a proof",
    "A fluent, plausible artifact",
    "No ground truth. Unjustified steps, hidden cases, off-by-one — invisible without an expert reader.",
  ],
  [
    "2 · LLM + Lean / AXLE",
    "A deterministic proof that matches the statement",
    "Spec blindness. A vacuous spec proves instantly; 'sorted' written as 'same length' is satisfied by the identity function.",
  ],
  [
    "3 · + Popper",
    "Proof matches statement AND an oracle tried & failed to break the statement",
    "The honest residual: falsify ≠ certify. But dropped hypotheses, vacuity, wrong direction, too-strong/weak specs are exactly what it catches — with a counterexample.",
  ],
];

export default function Ladder() {
  return (
    <div className="panel ladder">
      <table>
        <thead>
          <tr>
            <th style={{ width: "210px" }}>Rung</th>
            <th style={{ width: "260px" }}>What you get</th>
            <th>What still fails silently</th>
          </tr>
        </thead>
        <tbody>
          {RUNGS.map(([rung, get, fail]) => (
            <tr key={rung}>
              <td className="rung">{rung}</td>
              <td>{get}</td>
              <td style={{ color: "var(--muted)" }}>{fail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

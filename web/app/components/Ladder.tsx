const RUNGS: [string, string, string][] = [
  [
    "1 . A model writes a proof",
    "Something that reads well",
    "No guarantee. A skipped case or an off-by-one error is invisible unless an expert reads it.",
  ],
  [
    "2 . A model plus Lean or AXLE",
    "A real proof that matches the statement",
    "You are still trusting the statement. A statement that says nothing proves instantly. 'Sorted' written as 'same length' is satisfied by code that does nothing.",
  ],
  [
    "3 . Plus Popper",
    "The proof matches the statement, and a separate checker tried to break the statement",
    "If it could not, that is evidence the spec is fine. If it could, you get the input that breaks it. Loose specs, tight specs, dropped assumptions, and flipped directions are what it catches.",
  ],
];

export default function Ladder() {
  return (
    <div className="panel ladder">
      <table>
        <thead>
          <tr>
            <th style={{ width: "230px" }}>Level</th>
            <th style={{ width: "260px" }}>What you get</th>
            <th>What still slips through</th>
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

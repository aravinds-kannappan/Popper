"use client";

import { useRef, useState } from "react";

type Role = "user" | "assistant" | "error";
type ToolCall = { name: string; input: any; output: any };
type Msg = { role: Role; content: string; toolCalls?: ToolCall[] };

const EXAMPLES = [
  "Is ∀ n : Nat, n < 5 true? Check it.",
  "Falsify: ∀ a b : Nat, a - b + b = a",
  "Why can a fully-verified spec still be wrong?",
  "Show me the live Verina audit results.",
];

export default function Chat() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  function scroll() {
    requestAnimationFrame(() => {
      if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
    });
  }

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    const history = [...msgs, { role: "user" as Role, content: q }];
    setMsgs(history);
    setInput("");
    setBusy(true);
    scroll();
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: history
            .filter((m) => m.role === "user" || m.role === "assistant")
            .map((m) => ({ role: m.role, content: m.content })),
        }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setMsgs((m) => [...m, { role: "error", content: `Error: ${data.error || res.statusText}` }]);
      } else {
        setMsgs((m) => [...m, { role: "assistant", content: data.reply, toolCalls: data.toolCalls }]);
      }
    } catch (e: any) {
      setMsgs((m) => [...m, { role: "error", content: `Network error: ${String(e?.message || e)}` }]);
    } finally {
      setBusy(false);
      scroll();
    }
  }

  return (
    <div className="panel chat">
      <div className="log" ref={logRef}>
        {msgs.length === 0 && (
          <div className="note">
            The agent is Claude (Opus 4.8) with live AXLE tools. Ask anything — for checkable
            claims it runs <code>disprove</code>/<code>check</code> on the Axiom Lean Engine and
            reports the real result.
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.content}
            {m.toolCalls && m.toolCalls.length > 0 && (
              <div className="toolchip">
                {m.toolCalls.map((t, j) => (
                  <div key={j}>
                    <b>🔧 {t.name}</b>(<span>{JSON.stringify(t.input)}</span>)
                    <pre>{typeof t.output === "string" ? t.output : JSON.stringify(t.output, null, 2)}</pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="msg assistant">…thinking & running AXLE</div>}
      </div>

      <div className="examples">
        {EXAMPLES.map((e) => (
          <button key={e} onClick={() => send(e)} disabled={busy}>
            {e}
          </button>
        ))}
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a math or coding question, or give a Lean statement to falsify…"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}

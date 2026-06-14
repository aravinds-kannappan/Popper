// Minimal TypeScript client for the Axiom Lean Engine (AXLE) REST API.
// POST {base}/api/v1/{method} with `Authorization: Bearer <key>`.

const BASE = process.env.AXLE_BASE_URL || "https://axle.axiommath.ai";
const ENV = process.env.AXLE_ENVIRONMENT || "lean-4.28.0";

type Messages = { errors?: string[]; warnings?: string[]; infos?: string[] };

async function axlePost(method: string, body: Record<string, unknown>): Promise<any> {
  const key = process.env.AXLE_API_KEY;
  if (!key) throw new Error("AXLE_API_KEY is not set on the server.");
  const res = await fetch(`${BASE}/api/v1/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${key}` },
    body: JSON.stringify(body),
    // AXLE + Lean can be slow; the route's maxDuration bounds the overall request.
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`AXLE ${method} ${res.status}: ${txt.slice(0, 300)}`);
  }
  return res.json();
}

// Heuristic: only force the Mathlib import context when the snippet asks for it.
function ignoreImports(content: string): boolean {
  return !content.includes("import Mathlib");
}

export async function axleDisprove(content: string): Promise<{
  disproved: string[];
  results: Record<string, string>;
  messages: Messages;
}> {
  const r = await axlePost("disprove", {
    content,
    environment: ENV,
    ignore_imports: ignoreImports(content),
  });
  return {
    disproved: r.disproved_theorems ?? [],
    results: r.results ?? {},
    messages: r.lean_messages ?? {},
  };
}

export async function axleCheck(content: string): Promise<{
  okay: boolean;
  failed: string[];
  messages: Messages;
}> {
  const r = await axlePost("check", {
    content,
    environment: ENV,
    ignore_imports: ignoreImports(content),
  });
  return {
    okay: !!r.okay,
    failed: r.failed_declarations ?? [],
    messages: r.lean_messages ?? {},
  };
}

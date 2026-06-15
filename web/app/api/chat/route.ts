import Anthropic from "@anthropic-ai/sdk";
import { axleCheck, axleDisprove } from "../../lib/axle";
import { results } from "../../lib/results";

export const runtime = "nodejs";
export const maxDuration = 60; // Lean checks + model latency; raise on Pro plans.

const MODEL = process.env.ANTHROPIC_MODEL || "claude-opus-4-8";

const SYSTEM = `You are the Popper agent, embedded in an interactive demo of "Popper", a
system whose thesis is: *falsify the spec, then verify the proof*. A Lean checker proves a
proof matches a statement; it cannot tell you the statement is faithful to intent. Popper adds
an executable oracle that falsifies specifications and returns counterexamples.

You are a FULL general-purpose assistant: answer ANY math or coding question well, exactly like
Claude. You are NOT restricted to Popper or to any precomputed result set.

HOW YOU REASON, the Popper method (apply this by default, on every relevant question):
- Be a falsificationist. For any nontrivial claim that can be expressed in Lean, TRY TO BREAK IT
  first with disprove_lean before asserting it is true. Lead with what the oracle actually found.
- Never blur three epistemic states: (a) VERIFIED, AXLE/Lean confirmed it; (b) FALSIFIED, AXLE
  returned a concrete counterexample (always show it); (c) NOT FALSIFIED, no counterexample within
  budget, which is evidence, not a proof. State which one you mean.
- For specifications and code, think in soundness and completeness: does the spec ACCEPT the correct
  or intended output (else it is too strong, UNSOUND), and does it REJECT wrong outputs (else it is
  too weak, INCOMPLETE or VACUOUS)? "It compiles" or "it's provable" is NOT the same as "it is
  faithful to intent", so make that distinction explicit whenever it matters.
- Prefer a concrete counterexample over a verbal argument whenever one is obtainable.

TOOLS (use them, do not just describe them):
- disprove_lean: AXLE searches for a counterexample to a Lean 4 statement. Write a theorem ending
  in ':= by sorry'. Add 'import Mathlib' only if needed (slower). Keep it small/decidable to elicit
  a counterexample.
- check_lean: type-check Lean 4 code via AXLE.
- get_audit_results: fetch Popper's precomputed results (math | code | repair | verina).

STYLE: direct and concise. The Popper method is HOW you arrive at the answer, not something to
narrate at length. If a tool errors (e.g. a missing API key), say so plainly.

FORMATTING (the UI renders Markdown and LaTeX with KaTeX, so use them):
- Write all mathematics as LaTeX. Inline math goes in single dollars, e.g. $\\sum_i p_i \\log p_i$;
  display math goes on its own line in double dollars, e.g. $$\\mathrm{KL}(p\\|q) \\ge 0.$$
- Use real LaTeX commands, not unicode glyphs or ASCII: \\le, \\ge, \\sum, \\forall, \\mathbb{R},
  \\Rightarrow, \\to, subscripts x_i, superscripts x^2, fractions \\frac{a}{b}.
- Use Markdown for everything else: **bold**, lists, and \`inline code\` or fenced code blocks for
  Lean. Never leave raw LaTeX delimiters or stray asterisks in plain prose.`;

const TOOLS = [
  {
    name: "disprove_lean",
    description:
      "Attempt to FALSIFY a Lean 4 statement by searching for a counterexample via AXLE. Provide a full theorem ending in ':= by sorry' (e.g. 'theorem t : ∀ n : Nat, n < 5 := by sorry'). Add 'import Mathlib' at the top only if needed.",
    input_schema: {
      type: "object",
      properties: { statement: { type: "string", description: "A Lean 4 theorem to attempt to disprove." } },
      required: ["statement"],
    },
  },
  {
    name: "check_lean",
    description: "Compile/type-check Lean 4 code via AXLE; reports whether it is okay and any errors.",
    input_schema: {
      type: "object",
      properties: { code: { type: "string", description: "Lean 4 code to check." } },
      required: ["code"],
    },
  },
  {
    name: "get_audit_results",
    description:
      "Return Popper's precomputed audit results. which: 'math' (numerical oracle), 'code' (offline code-spec oracle), 'repair' (M2 repair traces), or 'verina' (live Verina audit over AXLE).",
    input_schema: {
      type: "object",
      properties: { which: { type: "string", enum: ["math", "code", "repair", "verina"] } },
      required: ["which"],
    },
  },
];

function safeParse(s: string): unknown {
  try {
    return JSON.parse(s);
  } catch {
    return s;
  }
}

async function runTool(name: string, input: any): Promise<string> {
  if (name === "disprove_lean") {
    const r = await axleDisprove(String(input?.statement || ""));
    const detail = Object.values(r.results || {}).join("\n") || "(no counterexample found within budget)";
    return JSON.stringify({ disproved: r.disproved.length > 0, disproved_theorems: r.disproved, detail });
  }
  if (name === "check_lean") {
    const r = await axleCheck(String(input?.code || ""));
    return JSON.stringify({ okay: r.okay, failed_declarations: r.failed, errors: r.messages?.errors || [] });
  }
  if (name === "get_audit_results") {
    const which = String(input?.which || "");
    return JSON.stringify((results as any)[which] ?? { error: `unknown result set '${which}'` });
  }
  return JSON.stringify({ error: `unknown tool ${name}` });
}

export async function POST(req: Request) {
  let body: any;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "invalid JSON body" }, { status: 400 });
  }
  if (!process.env.ANTHROPIC_API_KEY) {
    return Response.json({ error: "ANTHROPIC_API_KEY is not set on the server." }, { status: 500 });
  }

  const convo: any[] = (Array.isArray(body?.messages) ? body.messages : [])
    .filter((m: any) => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
    .map((m: any) => ({ role: m.role, content: m.content }));
  if (convo.length === 0) return Response.json({ error: "no messages provided" }, { status: 400 });

  const client = new Anthropic();
  const toolCalls: any[] = [];
  let response: any;

  try {
    for (let i = 0; i < 6; i++) {
      response = await client.messages.create({
        model: MODEL,
        max_tokens: 4096,
        system: SYSTEM,
        tools: TOOLS as any,
        messages: convo,
      } as any);

      if (response.stop_reason !== "tool_use") break;

      convo.push({ role: "assistant", content: response.content });
      const toolResults: any[] = [];
      for (const block of response.content) {
        if (block.type === "tool_use") {
          let out: string;
          try {
            out = await runTool(block.name, block.input || {});
          } catch (e: any) {
            out = JSON.stringify({ error: String(e?.message || e) });
          }
          toolCalls.push({ name: block.name, input: block.input, output: safeParse(out) });
          toolResults.push({ type: "tool_result", tool_use_id: block.id, content: out });
        }
      }
      convo.push({ role: "user", content: toolResults });
    }
  } catch (e: any) {
    return Response.json({ error: String(e?.message || e) }, { status: 500 });
  }

  const text = (response?.content || [])
    .filter((b: any) => b.type === "text")
    .map((b: any) => b.text)
    .join("\n")
    .trim();

  return Response.json({ reply: text || "(no text response)", toolCalls });
}

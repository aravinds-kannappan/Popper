// The three roles used by the live benchmark, all backed by Claude:
//
//   * runPopperAgent  -- Claude with live AXLE tools. It reasons the Popper way:
//                        for a checkable claim it tries to break it with AXLE first
//                        and reports the real counterexample.
//   * runPlainLLM     -- Claude with no tools, answering from its own knowledge.
//                        This is the "model on its own" baseline.
//   * runEvaluator    -- a separate Claude that grades both answers against the
//                        known ground truth. This is the layer that turns the
//                        agent's behaviour into the numbers the benchmark compares.
//
// Each system ends its answer with a VERDICT line, and FALSE answers add a
// COUNTEREXAMPLE line, which keeps parsing simple and robust.

import Anthropic from "@anthropic-ai/sdk";
import { axleCheck, axleDisprove } from "./axle";

export const AGENT_MODEL = process.env.ANTHROPIC_MODEL || "claude-opus-4-8";

export type Answer = {
  verdict: "TRUE" | "FALSE" | "UNSURE";
  counterexample: string;
  text: string;
  usedAxle: boolean;
  axleFoundCounterexample: boolean;
};

const VERDICT_RE = /VERDICT:\s*(TRUE|FALSE|UNSURE)/i;
const CE_RE = /COUNTEREXAMPLE:\s*(.+)/i;

function parseAnswer(text: string, usedAxle: boolean, axleHit: boolean): Answer {
  const v = (text.match(VERDICT_RE)?.[1] || "UNSURE").toUpperCase() as Answer["verdict"];
  const ce = (text.match(CE_RE)?.[1] || "").trim();
  return { verdict: v, counterexample: ce, text: text.trim(), usedAxle, axleFoundCounterexample: axleHit };
}

const FORMAT = `End your reply with exactly one line:
VERDICT: TRUE   (the claim holds)   or   VERDICT: FALSE   or   VERDICT: UNSURE
If the verdict is FALSE, add one more line:
COUNTEREXAMPLE: <one concrete input that breaks the claim>`;

const POPPER_SYSTEM = `You are the Popper agent. Your job is to decide whether a mathematical claim is
true, and you are a falsificationist: for any claim you can express in Lean, TRY TO BREAK IT with
disprove_lean before asserting it is true, and lead with what AXLE actually found. Prefer a concrete
counterexample over a verbal argument. Keep Lean snippets small and decidable (over Nat or Int) so a
counterexample can be found. Be concise.

${FORMAT}`;

const PLAIN_SYSTEM = `You are a careful mathematical assistant. Decide whether the claim is true using
your own reasoning. You have no tools. Be concise.

${FORMAT}`;

const TOOLS = [
  {
    name: "disprove_lean",
    description:
      "Attempt to FALSIFY a Lean 4 statement by searching for a counterexample via AXLE. Provide a full theorem ending in ':= by sorry'. Add 'import Mathlib' only if needed.",
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
];

async function runTool(name: string, input: any): Promise<{ out: string; axleHit: boolean }> {
  if (name === "disprove_lean") {
    const r = await axleDisprove(String(input?.statement || ""));
    const hit = r.disproved.length > 0;
    const detail = Object.values(r.results || {}).join("\n") || "(no counterexample found within budget)";
    return { out: JSON.stringify({ disproved: hit, disproved_theorems: r.disproved, detail }), axleHit: hit };
  }
  if (name === "check_lean") {
    const r = await axleCheck(String(input?.code || ""));
    return { out: JSON.stringify({ okay: r.okay, failed: r.failed, errors: r.messages?.errors || [] }), axleHit: false };
  }
  return { out: JSON.stringify({ error: `unknown tool ${name}` }), axleHit: false };
}

export async function runPopperAgent(question: string, client: Anthropic, model = AGENT_MODEL): Promise<Answer> {
  const convo: any[] = [{ role: "user", content: question }];
  let usedAxle = false;
  let axleHit = false;
  let response: any;

  for (let i = 0; i < 3; i++) {
    response = await client.messages.create({
      model,
      max_tokens: 1024,
      system: POPPER_SYSTEM,
      tools: TOOLS as any,
      messages: convo,
    } as any);
    if (response.stop_reason !== "tool_use") break;
    convo.push({ role: "assistant", content: response.content });
    const toolResults: any[] = [];
    for (const block of response.content) {
      if (block.type === "tool_use") {
        usedAxle = true;
        let res: { out: string; axleHit: boolean };
        try {
          res = await runTool(block.name, block.input || {});
        } catch (e: any) {
          res = { out: JSON.stringify({ error: String(e?.message || e) }), axleHit: false };
        }
        axleHit = axleHit || res.axleHit;
        toolResults.push({ type: "tool_result", tool_use_id: block.id, content: res.out });
      }
    }
    convo.push({ role: "user", content: toolResults });
  }

  const text = (response?.content || [])
    .filter((b: any) => b.type === "text")
    .map((b: any) => b.text)
    .join("\n");
  return parseAnswer(text, usedAxle, axleHit);
}

export async function runPlainLLM(question: string, client: Anthropic, model = AGENT_MODEL): Promise<Answer> {
  const response: any = await client.messages.create({
    model,
    max_tokens: 700,
    system: PLAIN_SYSTEM,
    messages: [{ role: "user", content: question }],
  } as any);
  const text = (response?.content || [])
    .filter((b: any) => b.type === "text")
    .map((b: any) => b.text)
    .join("\n");
  return parseAnswer(text, false, false);
}

export type Grade = {
  conclusion_correct: boolean;
  counterexample_valid: boolean | null; // null when no counterexample was needed/given
  quality: number; // 1..5
  note: string;
};

const EVAL_SYSTEM = `You grade two answers to a math claim, given the ground truth. You are strict and
fair. For each answer report, as JSON only:
{
  "popper": {"conclusion_correct": bool, "counterexample_valid": bool|null, "quality": 1-5, "note": "short"},
  "plain":  {"conclusion_correct": bool, "counterexample_valid": bool|null, "quality": 1-5, "note": "short"}
}
- conclusion_correct: did the answer reach the right TRUE/FALSE conclusion? An UNSURE answer is not correct.
- counterexample_valid: if the claim is FALSE, did the answer give a concrete, correct counterexample?
  Use true/false. Use null if the claim is TRUE (no counterexample is needed).
- quality: 1 (wrong or empty) to 5 (correct conclusion with a valid, concrete justification).
Output JSON only, no prose.`;

export async function runEvaluator(
  item: { question: string; truth: string; counterexample?: string },
  popper: Answer,
  plain: Answer,
  client: Anthropic,
  model = AGENT_MODEL
): Promise<{ popper: Grade; plain: Grade }> {
  const prompt = `CLAIM: ${item.question}
GROUND TRUTH: the claim is ${item.truth}${item.counterexample ? ` (a valid counterexample: ${item.counterexample})` : ""}

POPPER AGENT ANSWER:
${popper.text || "(empty)"}

PLAIN MODEL ANSWER:
${plain.text || "(empty)"}

Grade both as specified.`;

  const response: any = await client.messages.create({
    model,
    max_tokens: 700,
    system: EVAL_SYSTEM,
    messages: [{ role: "user", content: prompt }],
  } as any);
  const text = (response?.content || [])
    .filter((b: any) => b.type === "text")
    .map((b: any) => b.text)
    .join("\n");
  return parseGrades(text, item.truth, popper, plain);
}

function fallbackGrade(truth: string, a: Answer): Grade {
  const correct = a.verdict === truth;
  const ceValid = truth === "FALSE" ? a.counterexample.length > 0 : null;
  return { conclusion_correct: correct, counterexample_valid: ceValid, quality: correct ? 3 : 1, note: "parsed without evaluator" };
}

function parseGrades(text: string, truth: string, popper: Answer, plain: Answer): { popper: Grade; plain: Grade } {
  try {
    const obj = JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
    const norm = (g: any): Grade => ({
      conclusion_correct: !!g.conclusion_correct,
      counterexample_valid: g.counterexample_valid === null ? null : !!g.counterexample_valid,
      quality: Math.max(1, Math.min(5, Number(g.quality) || 1)),
      note: String(g.note || ""),
    });
    return { popper: norm(obj.popper), plain: norm(obj.plain) };
  } catch {
    return { popper: fallbackGrade(truth, popper), plain: fallbackGrade(truth, plain) };
  }
}

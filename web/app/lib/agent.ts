// The models used by the live benchmark.
//
//   * runPlainModel -- Claude with NO tools, answering from its own knowledge.
//                      Used for the comparison baselines (a large and a small model).
//   * runEvaluator  -- a separate Claude that, for each question, decides the true
//                      answer (treating AXLE's finding from the chat as authoritative
//                      when present) and grades every system's answer. This is the
//                      layer that turns the chat into the numbers the benchmark uses.
//
// The Popper agent's own answers are not produced here; they come straight from the
// chat the user already had, so the benchmark is built from real interactions.

import Anthropic from "@anthropic-ai/sdk";

export const BIG_MODEL = process.env.ANTHROPIC_MODEL || "claude-opus-4-8";

const PLAIN_SYSTEM = `You are a careful mathematical assistant with no tools. Decide whether the
user's claim is true or false using your own reasoning. Be concise. End with exactly one line:
VERDICT: TRUE | FALSE | UNSURE
If FALSE, add: COUNTEREXAMPLE: <one concrete witness>`;

export type PlainAnswer = { text: string; model: string };

export async function runPlainModel(question: string, client: Anthropic, model: string): Promise<PlainAnswer> {
  const r: any = await client.messages.create({
    model,
    max_tokens: 600,
    system: PLAIN_SYSTEM,
    messages: [{ role: "user", content: question }],
  } as any);
  const text = (r?.content || []).filter((b: any) => b.type === "text").map((b: any) => b.text).join("\n");
  return { text: text.trim(), model };
}

export type Grade = {
  verdict: "TRUE" | "FALSE" | "UNSURE";
  counterexample_valid: boolean | null;
  quality: number; // 1..5
};

export type Evaluation = {
  truth: "TRUE" | "FALSE" | "NA"; // NA = not a checkable true/false claim
  reference_counterexample: string;
  grades: Record<string, Grade>;  // keyed by system name
};

const EVAL_SYSTEM = `You are a strict evaluator. You are given a math/logic claim, what an AXLE Lean
prover found about it (this is AUTHORITATIVE: if AXLE returned a counterexample the claim is FALSE
with that witness; if AXLE checked it and found none on a decidable statement, lean TRUE), and one or
more system answers. Decide the truth and grade each answer. Output JSON ONLY:
{
  "truth": "TRUE" | "FALSE" | "NA",
  "reference_counterexample": "string (empty if none)",
  "grades": {
    "<system name>": {"verdict": "TRUE"|"FALSE"|"UNSURE", "counterexample_valid": true|false|null, "quality": 1-5}
  }
}
- truth = NA if the claim is not a checkable true/false statement (e.g. an opinion or open question).
- For each system: read its effective verdict from its text; counterexample_valid is whether any
  counterexample it gave is concrete and correct (null if truth is TRUE or none was needed);
  quality is 1 (wrong/empty) to 5 (right conclusion with a valid, concrete justification).
Output JSON only.`;

export async function runEvaluator(
  question: string,
  axleHint: string,
  answers: { name: string; text: string }[],
  client: Anthropic,
  model: string = BIG_MODEL
): Promise<Evaluation> {
  const body =
    `CLAIM: ${question}\n\nAXLE FINDING: ${axleHint || "(AXLE was not used for this one)"}\n\n` +
    answers.map((a) => `SYSTEM "${a.name}" ANSWER:\n${a.text || "(empty)"}`).join("\n\n") +
    `\n\nGrade every system named above.`;
  const r: any = await client.messages.create({
    model,
    max_tokens: 800,
    system: EVAL_SYSTEM,
    messages: [{ role: "user", content: body }],
  } as any);
  const text = (r?.content || []).filter((b: any) => b.type === "text").map((b: any) => b.text).join("\n");
  return parseEval(text, answers.map((a) => a.name));
}

function parseEval(text: string, names: string[]): Evaluation {
  try {
    const obj = JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
    const grades: Record<string, Grade> = {};
    for (const n of names) {
      const g = (obj.grades || {})[n] || {};
      const v = String(g.verdict || "UNSURE").toUpperCase();
      grades[n] = {
        verdict: (["TRUE", "FALSE", "UNSURE"].includes(v) ? v : "UNSURE") as Grade["verdict"],
        counterexample_valid: g.counterexample_valid === null || g.counterexample_valid === undefined ? null : !!g.counterexample_valid,
        quality: Math.max(1, Math.min(5, Number(g.quality) || 1)),
      };
    }
    const truth = String(obj.truth || "NA").toUpperCase();
    return {
      truth: (["TRUE", "FALSE", "NA"].includes(truth) ? truth : "NA") as Evaluation["truth"],
      reference_counterexample: String(obj.reference_counterexample || ""),
      grades,
    };
  } catch {
    const grades: Record<string, Grade> = {};
    for (const n of names) grades[n] = { verdict: "UNSURE", counterexample_valid: null, quality: 1 };
    return { truth: "NA", reference_counterexample: "", grades };
  }
}

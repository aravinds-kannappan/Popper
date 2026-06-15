// Live benchmark built from the user's real chat.
//
// The client sends the interactions the user already had with the Popper agent:
// each one carries the question, the Popper agent's answer, and what AXLE found
// (read from the chat's tool calls). For each question this route runs two more
// systems with no tools (a large and a small model), then an evaluator agent
// decides the truth (treating AXLE's finding as authoritative) and grades every
// system. The grades become the metrics, which are bootstrapped to 500 resamples
// for confidence intervals.
//
// Needs ANTHROPIC_API_KEY; AXLE_API_KEY powers the agent's tools in the chat.

import Anthropic from "@anthropic-ai/sdk";
import { BIG_MODEL, SMALL_MODEL, runEvaluator, runPlainModel } from "../../lib/agent";
import { bootstrap, computeMetrics, ItemResult } from "../../lib/benchMetrics";

export const runtime = "nodejs";
export const maxDuration = 300;

const POPPER = "Popper agent";
const OPUS = "Opus (no tools)";
const HAIKU = "Haiku (no tools)";

type Interaction = {
  question: string;
  popperText: string;
  axleUsed?: boolean;
  axleDisproved?: boolean;
  axleDetail?: string;
};

function axleHint(it: Interaction): string {
  if (!it.axleUsed) return "";
  if (it.axleDisproved) return `AXLE found a counterexample: ${it.axleDetail || "(witness returned)"}`;
  return "AXLE ran and found no counterexample within its budget.";
}

export async function POST(req: Request) {
  if (!process.env.ANTHROPIC_API_KEY) {
    return Response.json({ error: "ANTHROPIC_API_KEY is not set on the server." }, { status: 503 });
  }
  let body: any;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "invalid JSON body" }, { status: 400 });
  }
  const interactions: Interaction[] = (Array.isArray(body?.interactions) ? body.interactions : [])
    .filter((x: any) => x && typeof x.question === "string" && x.question.trim())
    .slice(0, 12);
  if (interactions.length === 0) {
    return Response.json({ error: "no interactions provided" }, { status: 400 });
  }

  const client = new Anthropic();
  const names = [POPPER, OPUS, HAIKU];

  try {
    const perItem = await Promise.all(
      interactions.map(async (it) => {
        const [opus, haiku] = await Promise.all([
          runPlainModel(it.question, client, BIG_MODEL).catch(() => ({ text: "(failed)", model: BIG_MODEL })),
          runPlainModel(it.question, client, SMALL_MODEL).catch(() => ({ text: "(failed)", model: SMALL_MODEL })),
        ]);
        const ev = await runEvaluator(
          it.question,
          axleHint(it),
          [
            { name: POPPER, text: it.popperText || "" },
            { name: OPUS, text: opus.text },
            { name: HAIKU, text: haiku.text },
          ],
          client
        ).catch(() => ({ truth: "NA" as const, reference_counterexample: "", grades: {} as any }));
        return { it, ev };
      })
    );

    // Only items the evaluator judged as a checkable TRUE/FALSE claim are scored.
    const scored = perItem.filter((r) => r.ev.truth === "TRUE" || r.ev.truth === "FALSE");

    const rowsFor = (name: string): ItemResult[] =>
      scored.map((r) => {
        const g = r.ev.grades[name] || { verdict: "UNSURE", counterexample_valid: null, quality: 1 };
        return {
          truth: r.ev.truth as "TRUE" | "FALSE",
          verdict: g.verdict,
          counterexample_valid: g.counterexample_valid,
          quality: g.quality,
        };
      });

    const systems = names.map((name) => {
      const rows = rowsFor(name);
      return { name, metrics: computeMetrics(rows), ci: bootstrap(rows, 500) };
    });

    const payload = {
      model: BIG_MODEL,
      small_model: SMALL_MODEL,
      ran_at: new Date().toISOString(),
      n_messages: interactions.length,
      n_scored: scored.length,
      bootstrap_samples: 500,
      axle_decided: interactions.filter((it) => it.axleUsed && it.axleDisproved).length,
      axle_used: interactions.filter((it) => it.axleUsed).length,
      systems,
      items: perItem.map((r) => ({
        question: r.it.question,
        truth: r.ev.truth,
        reference_counterexample: r.ev.reference_counterexample,
        axle_used: !!r.it.axleUsed,
        axle_disproved: !!r.it.axleDisproved,
        grades: names.reduce((acc: any, name) => {
          const g = r.ev.grades[name];
          if (g) acc[name] = { ...g, correct: r.ev.truth !== "NA" && g.verdict === r.ev.truth };
          return acc;
        }, {}),
      })),
    };
    return Response.json(payload);
  } catch (e: any) {
    return Response.json({ error: String(e?.message || e) }, { status: 500 });
  }
}

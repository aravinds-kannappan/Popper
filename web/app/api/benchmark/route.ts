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
import { BIG_MODEL, runEvaluator, runPlainModel } from "../../lib/agent";
import { bootstrap, computeMetrics, ItemResult } from "../../lib/benchMetrics";

export const runtime = "nodejs";
export const maxDuration = 300;

const POPPER = "Popper agent";
const OPUS = "Opus (no tools)";
const AXLE = "AXLE alone";

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
  const names = [POPPER, OPUS, AXLE];

  try {
    const perItem = await Promise.all(
      interactions.map(async (it) => {
        const opus = await runPlainModel(it.question, client, BIG_MODEL).catch(() => ({ text: "(failed)", model: BIG_MODEL }));
        // The evaluator decides the truth and grades the two text systems. AXLE on
        // its own is graded deterministically from its raw result below, because it
        // has no reasoning to read: it either returned a counterexample or it did not.
        const ev = await runEvaluator(
          it.question,
          axleHint(it),
          [
            { name: POPPER, text: it.popperText || "" },
            { name: OPUS, text: opus.text },
          ],
          client
        ).catch(() => ({ truth: "NA" as const, reference_counterexample: "", grades: {} as any }));
        return { it, ev, axle: axleAlone(it, ev.truth) };
      })
    );

    // Only items the evaluator judged as a checkable TRUE/FALSE claim are scored.
    const scored = perItem.filter((r) => r.ev.truth === "TRUE" || r.ev.truth === "FALSE");

    const gradeOf = (r: any, name: string) =>
      name === AXLE ? r.axle : (r.ev.grades[name] || { verdict: "UNSURE", counterexample_valid: null, quality: 1 });

    const rowsFor = (name: string): ItemResult[] =>
      scored.map((r) => {
        const g = gradeOf(r, name);
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
          const g = gradeOf(r, name);
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

// AXLE used by itself, with no Popper agent around it. All it can do is run its
// counterexample search: it either returned a witness (so the claim is FALSE) or it
// did not, in which case on its own it cannot conclude anything (UNSURE). It can
// never confirm a true statement, which is exactly the gap the Popper agent fills.
function axleAlone(it: Interaction, truth: string) {
  const disproved = !!it.axleDisproved;
  const verdict = disproved ? "FALSE" : "UNSURE";
  const counterexample_valid = disproved ? true : truth === "FALSE" ? false : null;
  let quality = 1;
  if (truth === "FALSE") quality = disproved ? 5 : 1;
  else if (truth === "TRUE") quality = 2; // did not err, but cannot confirm
  return {
    verdict,
    counterexample_valid,
    quality,
    counterexample: disproved ? it.axleDetail || "witness returned by AXLE" : "",
  };
}

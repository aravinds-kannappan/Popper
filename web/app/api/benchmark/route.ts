// Live benchmark. Runs when the Benchmark tab loads.
//
// For each claim in the eval set it runs two systems live: the Popper agent
// (Claude + live AXLE), and a plain model (Claude, no tools). A third Claude, the
// evaluator agent, grades both answers against the known ground truth. The grades
// become the metrics the page compares. This needs ANTHROPIC_API_KEY and, for the
// Popper agent's AXLE tools, AXLE_API_KEY, both set as server env vars on Vercel.

import Anthropic from "@anthropic-ai/sdk";
import { AGENT_MODEL, runEvaluator, runPlainLLM, runPopperAgent } from "../../lib/agent";
import { computeMetrics, ItemResult } from "../../lib/benchMetrics";
import { EVAL_SET } from "../../lib/evalset";

export const runtime = "nodejs";
export const maxDuration = 300; // many model calls + Lean; needs a Pro plan for the full set.

// Cache within a warm serverless instance so repeat loads are instant.
let CACHE: { ranAt: number; payload: any } | null = null;
const TTL_MS = 1000 * 60 * 30;

export async function POST() {
  if (!process.env.ANTHROPIC_API_KEY) {
    return Response.json({ error: "ANTHROPIC_API_KEY is not set on the server." }, { status: 503 });
  }
  if (CACHE && Date.now() - CACHE.ranAt < TTL_MS) {
    return Response.json({ ...CACHE.payload, cached: true });
  }

  const client = new Anthropic();
  const haveAxle = !!process.env.AXLE_API_KEY;

  try {
    // Run every item in parallel; each item: agent + plain, then the evaluator.
    const perItem = await Promise.all(
      EVAL_SET.map(async (item) => {
        const [popper, plain] = await Promise.all([
          runPopperAgent(item.question, client).catch((e) => emptyAnswer(e)),
          runPlainLLM(item.question, client).catch((e) => emptyAnswer(e)),
        ]);
        const grades = await runEvaluator(item, popper, plain, client).catch(() => ({
          popper: fallback(item.truth, popper.verdict, popper.counterexample),
          plain: fallback(item.truth, plain.verdict, plain.counterexample),
        }));
        return { item, popper, plain, grades };
      })
    );

    const popperRows: ItemResult[] = perItem.map((r) => row(r.item.truth, r.popper, r.grades.popper));
    const plainRows: ItemResult[] = perItem.map((r) => row(r.item.truth, r.plain, r.grades.plain));

    const payload = {
      model: AGENT_MODEL,
      ran_at: new Date().toISOString(),
      axle_live: haveAxle,
      n_items: EVAL_SET.length,
      metrics: {
        popper: computeMetrics(popperRows),
        plain: computeMetrics(plainRows),
      },
      items: perItem.map((r) => ({
        id: r.item.id,
        question: r.item.question,
        truth: r.item.truth,
        note: r.item.note || "",
        reference_counterexample: r.item.counterexample || "",
        popper: {
          verdict: r.popper.verdict,
          counterexample: r.popper.counterexample,
          used_axle: r.popper.usedAxle,
          axle_found_counterexample: r.popper.axleFoundCounterexample,
          ...r.grades.popper,
        },
        plain: {
          verdict: r.plain.verdict,
          counterexample: r.plain.counterexample,
          ...r.grades.plain,
        },
      })),
    };

    CACHE = { ranAt: Date.now(), payload };
    return Response.json(payload);
  } catch (e: any) {
    return Response.json({ error: String(e?.message || e) }, { status: 500 });
  }
}

function emptyAnswer(_e: any) {
  return { verdict: "UNSURE" as const, counterexample: "", text: "(failed)", usedAxle: false, axleFoundCounterexample: false };
}

function fallback(truth: string, verdict: string, ce: string) {
  const correct = verdict === truth;
  return {
    conclusion_correct: correct,
    counterexample_valid: truth === "FALSE" ? ce.length > 0 : null,
    quality: correct ? 3 : 1,
    note: "graded without evaluator",
  };
}

function row(truth: "TRUE" | "FALSE", ans: { verdict: any }, grade: any): ItemResult {
  return {
    truth,
    verdict: ans.verdict,
    conclusion_correct: grade.conclusion_correct,
    counterexample_valid: grade.counterexample_valid,
    quality: grade.quality,
  };
}

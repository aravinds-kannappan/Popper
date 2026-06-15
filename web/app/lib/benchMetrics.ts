// Turn per-item grades into comparison metrics. The task is binary: decide whether
// a claim is FALSE (the "positive" class, the thing worth flagging). We report the
// usual recall/precision/F1, accuracy, and the Matthews correlation coefficient
// (MCC), a single balanced number in [-1, 1] that is only high when a system does
// well on both true and false claims.
//
// The user's 10 real messages are a small sample, so we also bootstrap: resample
// the graded items with replacement many times (default 500) and report the mean
// of each metric plus a 95% interval. That is what "scaling 10 to 500" means here:
// it tightens the estimate honestly rather than inventing new data.

export type ItemResult = {
  truth: "TRUE" | "FALSE";
  verdict: "TRUE" | "FALSE" | "UNSURE";
  counterexample_valid: boolean | null;
  quality: number;
};

export type Metrics = {
  n: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  mcc: number;
  counterexample_yield: number;
  avg_quality: number;
};

export function computeMetrics(rows: ItemResult[]): Metrics {
  let tp = 0, fp = 0, fn = 0, tn = 0, correct = 0, qual = 0, falseItems = 0, validCe = 0;
  for (const r of rows) {
    const flagged = r.verdict === "FALSE";
    if (r.truth === "FALSE") {
      falseItems++;
      if (r.counterexample_valid) validCe++;
      if (flagged) tp++; else fn++;
    } else {
      if (flagged) fp++; else tn++;
    }
    if (r.verdict === r.truth) correct++;
    qual += r.quality;
  }
  const n = rows.length || 1;
  const precision = tp + fp ? tp / (tp + fp) : 0;
  const recall = tp + fn ? tp / (tp + fn) : 0;
  const f1 = precision + recall ? (2 * precision * recall) / (precision + recall) : 0;
  const den = Math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn));
  const mcc = den ? (tp * tn - fp * fn) / den : 0;
  return {
    n: rows.length,
    accuracy: correct / n,
    precision,
    recall,
    f1,
    mcc,
    counterexample_yield: falseItems ? validCe / falseItems : 0,
    avg_quality: qual / n,
  };
}

export type CI = { mean: number; lo: number; hi: number };

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  const i = Math.min(sorted.length - 1, Math.max(0, Math.round(p * (sorted.length - 1))));
  return sorted[i];
}

export function bootstrap(rows: ItemResult[], samples = 500, seed = 1): Record<string, CI> {
  const keys = ["accuracy", "f1", "mcc", "counterexample_yield"] as const;
  const draws: Record<string, number[]> = { accuracy: [], f1: [], mcc: [], counterexample_yield: [] };
  if (rows.length === 0) {
    return Object.fromEntries(keys.map((k) => [k, { mean: 0, lo: 0, hi: 0 }]));
  }
  // small deterministic PRNG so results are stable for a given set of grades
  let s = seed >>> 0;
  const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  for (let b = 0; b < samples; b++) {
    const resample: ItemResult[] = [];
    for (let i = 0; i < rows.length; i++) resample.push(rows[Math.floor(rnd() * rows.length)]);
    const m = computeMetrics(resample);
    for (const k of keys) draws[k].push(m[k]);
  }
  const out: Record<string, CI> = {};
  for (const k of keys) {
    const arr = draws[k].slice().sort((a, b) => a - b);
    const mean = arr.reduce((x, y) => x + y, 0) / arr.length;
    out[k] = { mean, lo: percentile(arr, 0.025), hi: percentile(arr, 0.975) };
  }
  return out;
}

// Turn per-item results into the comparison metrics. The task is binary: decide
// whether a claim is FALSE (the "positive" class, i.e. the thing worth flagging).
// We report the usual recall/precision/F1, plus accuracy and the Matthews
// correlation coefficient (MCC). MCC is a single balanced number in [-1, 1] that
// is only high when the system does well on both true and false claims, so it is
// the honest summary when the classes are mixed, and it lands in a real range
// rather than pinning at 1.

export type ItemResult = {
  truth: "TRUE" | "FALSE";
  verdict: "TRUE" | "FALSE" | "UNSURE";
  conclusion_correct: boolean;
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
  tp: number;
  fp: number;
  fn: number;
  tn: number;
};

export function computeMetrics(rows: ItemResult[]): Metrics {
  let tp = 0, fp = 0, fn = 0, tn = 0, correct = 0, qual = 0;
  let falseItems = 0, validCe = 0;
  for (const r of rows) {
    const flagged = r.verdict === "FALSE";
    if (r.truth === "FALSE") {
      falseItems++;
      if (r.counterexample_valid) validCe++;
      if (flagged) tp++; else fn++;
    } else {
      if (flagged) fp++; else tn++;
    }
    if (r.conclusion_correct) correct++;
    qual += r.quality;
  }
  const n = rows.length || 1;
  const precision = tp + fp ? tp / (tp + fp) : 0;
  const recall = tp + fn ? tp / (tp + fn) : 0;
  const f1 = precision + recall ? (2 * precision * recall) / (precision + recall) : 0;
  const denom = Math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn));
  const mcc = denom ? (tp * tn - fp * fn) / denom : 0;
  return {
    n: rows.length,
    accuracy: correct / n,
    precision,
    recall,
    f1,
    mcc,
    counterexample_yield: falseItems ? validCe / falseItems : 0,
    avg_quality: qual / n,
    tp, fp, fn, tn,
  };
}

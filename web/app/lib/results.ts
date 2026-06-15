// Precomputed Popper audit results, copied from the repo's `results/` directory.
// These power the dashboard and the agent's `get_audit_results` tool. They are a
// reference the agent can consult, not the limit of what it can answer.

import math from "../data/math_audit.json";
import code from "../data/codespec_offline.json";
import repair from "../data/repair.json";
import verina from "../data/verina_live.json";

export const results = { math, code, repair, verina } as const;
export type ResultsKey = keyof typeof results;

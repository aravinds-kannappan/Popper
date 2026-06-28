#!/usr/bin/env python3
"""Scaling Popper with AI-safety / RLHF principles (falsify.scale).

Six research ideas, each ported to spec faithfulness and run for real, offline,
no API key:

  1. Sleeper Agents      -> adaptive (CEM) search finds rare-trigger spec bugs
                            with far fewer draws than uniform Monte-Carlo.
  2. Reward Hacking      -> active search for an implementation that games a spec.
  3. Safe RLHF           -> reward/cost decoupling -> a constrained faithfulness score.
  4. Scalable Debate     -> a cheap verifier recovers a statement's missing premise.
  5. Bridge (LLM judge)  -> calibrate a guessing judge against the executable oracle.
  6. Model Eval / gating -> a risk card that decides PROVE / REPAIR / REJECT.

    python examples/scale_demo.py
    python examples/scale_demo.py --markdown > reports/scaling_demo.md
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falsify import (  # noqa: E402
    CodeSpecOracle, MockAxleClient, verina_like_tasks,
    UniformFalsifier, AdaptiveFalsifier, sleeper_claims,
    probe_reward_hacks, score_task, build_eval_card,
    calibrate_judge, ensemble_verdict,
)
from falsify.scale.debate import gibbs_debate, run_debate  # noqa: E402
from falsify.scale.calibration import synthetic_judge  # noqa: E402
from falsify.montecarlo.numerical import NumericalOracle  # noqa: E402
from falsify.bench.corpus import math_items  # noqa: E402
from falsify.bench.judges import popper_judge  # noqa: E402


def sleeper_table(budget=20000):
    rows = []
    for claim in sleeper_claims():
        u = UniformFalsifier(budget=budget).search(claim)
        a = AdaptiveFalsifier(budget=budget).search(claim)
        speedup = (u.draws_used / a.draws_used) if (a.found and u.found) else float("inf")
        rows.append((claim.name, claim.expected.value, u.found, u.draws_used,
                     a.found, a.draws_used, speedup))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--budget", type=int, default=20000)
    args = ap.parse_args()
    md = args.markdown
    client = MockAxleClient()
    tasks = verina_like_tasks()

    out = []
    p = out.append

    # -- 1. Sleeper Agents: adaptive vs uniform on rare-trigger bugs --------- #
    rows = sleeper_table(args.budget)
    if md:
        p("# Scaling Popper with AI-safety principles\n")
        p("## 1. Sleeper Agents -> adaptive search for rare-trigger bugs\n")
        p("Uniform Monte-Carlo needs ~1/p draws to hit a trigger of probability p. "
          "Cross-Entropy-Method search steers draws to the low-margin boundary.\n")
        p("| claim | gold | uniform found | uniform draws | adaptive found | adaptive draws | speedup |")
        p("|---|---|---|---|---|---|---|")
        for n, g, uf, ud, af, ad, sp in rows:
            sp_s = "inf" if sp == float("inf") else f"{sp:.0f}x"
            p(f"| `{n}` | {g} | {uf} | {ud} | {af} | {ad} | {sp_s} |")
        p("")
    else:
        p("\n=== 1. Sleeper Agents -> adaptive search (draws to find a rare bug) ===")
        p(f"{'claim':<22}{'gold':<11}{'uniform':>16}{'adaptive':>14}{'speedup':>10}")
        for n, g, uf, ud, af, ad, sp in rows:
            us = f"{ud}" if uf else f"miss({ud})"
            as_ = f"{ad}" if af else f"miss({ad})"
            sp_s = "inf" if sp == float("inf") else f"{sp:.0f}x"
            p(f"{n:<22}{g:<11}{us:>16}{as_:>14}{sp_s:>10}")

    # -- 2. Reward Hacking: search for an impl that games the spec ----------- #
    if md:
        p("## 2. Reward Hacking -> active search for a spec-gaming implementation\n")
        p("| task | hacked | hacker | acceptance | agreement | margin | verdict |")
        p("|---|---|---|---|---|---|---|")
    else:
        p("\n=== 2. Reward Hacking -> active spec-gaming search ===")
    for t in tasks:
        r = probe_reward_hacks(t, client)
        if md:
            p(f"| `{t.name}` | {r.hacked} | `{r.hacker or '-'}` | {r.acceptance:.2f} | "
              f"{r.agreement:.2f} | {r.hacking_margin:.2f} | {r.verdict.value} |")
        else:
            p(f"  {t.name:<24} hacked={str(r.hacked):<5} hacker={str(r.hacker):<16} "
              f"margin={r.hacking_margin:.2f} -> {r.verdict.value}")

    # -- 3. Safe RLHF: reward/cost decoupling ------------------------------- #
    if md:
        p("\n## 3. Safe RLHF -> constrained faithfulness score (reward - lambda*cost)\n")
        p("| task | reward | cost | objective | constraint | verdict |")
        p("|---|---|---|---|---|---|")
    else:
        p("\n=== 3. Safe RLHF -> reward (accept correct) vs cost (accept wrong) ===")
    for t in tasks:
        s = score_task(t, client)
        if md:
            ok = "ok" if s.constraint_satisfied else "VIOLATED"
            p(f"| `{t.name}` | {s.reward:.2f} | {s.cost:.2f} | {s.objective:+.2f} | {ok} | {s.verdict.value} |")
        else:
            p("  " + s.one_line())

    # -- 4. Debate: recover the missing premise ----------------------------- #
    claim, rescues = gibbs_debate()
    t_ = run_debate(claim, rescues, budget=4000)
    if md:
        p("\n## 4. Scalable Debate -> a cheap verifier recovers the missing premise\n")
        p("```")
        p(t_.render())
        p("```")
    else:
        p("\n=== 4. Scalable Debate -> recover the dropped hypothesis ===")
        p(t_.render())

    # -- 5. Bridge: calibrate the LLM judge against the oracle --------------- #
    items = [it for it in math_items() if it.family in ("faithful", "dropped-hypothesis",
                                                         "direction-error", "over-claim")][:120]
    pairs = []
    for it in items:
        o = popper_judge(it, n_trials=2000)
        j = synthetic_judge(o)            # SYNTHETIC judge, declared bias, no API key
        pairs.append((o, j))
    cal = calibrate_judge(pairs, judge_name="synthetic-llm")
    recovered = sum(1 for o, j in pairs
                    if ensemble_verdict(o, j, cal).verdict.is_falsified and o.verdict.is_falsified)
    oracle_caught = sum(1 for o, _ in pairs if o.verdict.is_falsified)
    if md:
        p("\n## 5. Bridge -> calibrate a guessing judge against the executable oracle\n")
        p(f"On {cal.n} math items (synthetic judge, declared bias, no witness):\n")
        p(f"- judge accuracy vs oracle: **{cal.accuracy:.2f}**, kappa **{cal.kappa:.2f}**, "
          f"flag-bias **{cal.flag_bias:+.2f}**")
        p(f"- ensemble (oracle witness wins, judge discounted by bias) keeps "
          f"**{recovered}/{oracle_caught}** of the oracle's true catches\n")
    else:
        p("\n=== 5. Bridge -> LLM-judge calibration (synthetic judge) ===")
        p("  " + cal.one_line())
        p(f"  ensemble keeps {recovered}/{oracle_caught} of the oracle's true catches")

    # -- 6. Model Eval -> the gate decision --------------------------------- #
    if md:
        p("\n## 6. Model Eval -> risk card and PROVE / REPAIR / REJECT gate\n")
        p("| task | capability | propensity | risk | gate | verdict |")
        p("|---|---|---|---|---|---|")
    else:
        p("\n=== 6. Model Eval -> gate the expensive prover on a risk threshold ===")
    for t in tasks:
        card = build_eval_card(t, client)
        if md:
            p(f"| `{t.name}` | {card.capability:.2f} | {card.propensity:.2f} | "
              f"{card.risk:.2f} | **{card.gate.value}** | {card.verdict.value} |")
        else:
            p("  " + card.one_line())

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

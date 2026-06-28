#!/usr/bin/env python3
"""M4: exact falsification, statistical certificates, type-directed generation,
and a trained adversary. Ideas 1-3 from the scaling roadmap, all offline.

  1a. SMT engine     -> decide statements exactly: exact counterexample, or a
                        real certificate (enum over an integer box; Fourier-
                        Motzkin over the rationals; optional Z3 for nonlinear).
  1b. PAC certificate -> turn "survived N draws" into "bug rate <= eps at 1-delta".
  2.  Type-directed   -> derive generators from a signature; no hand-written fixtures.
  3.  Trained adversary -> a UCB bandit + transfer memory finds reward hacks in
                        fewer tries over a stream; trigger search learns the
                        conjunctive sleeper predicate, not just a point.

    python examples/exact_demo.py
    python examples/exact_demo.py --markdown > reports/exact.md
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falsify import (  # noqa: E402
    SMTOracle, symbolic_library, MockAxleClient,
    NumericalOracle, AdaptiveOracle, sleeper_claims,
    bug_rate_upper_bound, certify_result,
    parse_signature, gen_inputs_for, small_inputs_for,
    AdaptiveHackPolicy, WitnessMemory, probe_reward_hacks_learned, naive_evaluations,
    conjunctive_trigger_search, Task, CodeSpecOracle, verina_like_tasks,
)
from falsify.bench.corpus import math_items  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()
    md = args.markdown
    out, p = [], None
    out = []
    p = out.append

    # -- 1a. exact SMT decisions ------------------------------------------- #
    smt = SMTOracle()
    if md:
        p("# M4: exact falsification, certificates, type-directed generation, trained adversary\n")
        p("## 1a. Exact SMT engine -> exact counterexample or a real certificate\n")
        p("| claim | verdict | backend | certificate | counterexample |")
        p("|---|---|---|---|---|")
    else:
        p("\n=== 1a. Exact SMT engine (decide, do not sample) ===")
    for c in symbolic_library():
        r = smt.audit(c)
        cert = r.details.get("certificate")
        if md:
            p(f"| `{c.name}` | {r.verdict.value} | {r.details.get('backend','-')} | "
              f"{cert} | {r.counterexample or '-'} |")
        else:
            tail = f" ce: {r.counterexample}" if r.counterexample else (
                "  [CERTIFIED]" if cert else "")
            p(f"  {c.name:<26} {r.verdict.value:<12} via {r.details.get('backend','-'):<16}{tail}")

    # -- 1b. PAC certificate over a sampling survivor ---------------------- #
    item = next(it for it in math_items() if it.family == "faithful")
    res = NumericalOracle(n_trials=3000).audit(item.math)
    bound = certify_result(res)
    bounds = [(n, bug_rate_upper_bound(n).eps) for n in (100, 1000, 3000, 10000, 50000)]
    if md:
        p("\n## 1b. PAC certificate -> survived draws become a bug-rate bound\n")
        p(f"A faithful statement that survives sampling: {bound.one_line() if bound else 'n/a'}.\n")
        p("| clean draws | bug-rate upper bound (95%) |")
        p("|---|---|")
        for n, e in bounds:
            p(f"| {n:,} | {e:.2g} |")
    else:
        p("\n=== 1b. PAC certificate (Clopper-Pearson, 95% confidence) ===")
        p(f"  {bound.one_line() if bound else 'n/a'}")
        for n, e in bounds:
            p(f"  {n:>6,} clean draws  ->  bug rate <= {e:.2g}")

    # -- 2. type-directed generation --------------------------------------- #
    sig = "max2 : Int -> Int -> Int"
    arg_types, _ = parse_signature(sig)
    gen_input = gen_inputs_for(arg_types)
    small = small_inputs_for(arg_types, scope=1)
    # build the SAME too-weak max spec as the fixtures, but with generated inputs
    gen_task = Task(
        name="max_generated", description="max of two ints, inputs from the signature",
        signature=sig, reference="builtin_max", spec="post_lower_bound",
        impls_py={"builtin_max": lambda a, b: max(a, b),
                  "max_plus_one": lambda a, b: max(a, b) + 1,
                  "neg_inf": lambda a, b: -(10 ** 9)},
        spec_py={"post_lower_bound": lambda args, o: o >= args[0] and o >= args[1]},
        wrong_impls=["max_plus_one"], arbitrary="neg_inf",
        test_inputs=small, gen_input=gen_input)
    verdict = CodeSpecOracle(MockAxleClient()).audit(gen_task)
    if md:
        p("\n## 2. Type-directed generation -> audit a signature with no hand-written fixture\n")
        p(f"- signature `{sig}` parses to argument types `{[type(t).__name__ for t in arg_types]}`")
        p(f"- small-scope enumeration (scope 1) gives {len(small)} inputs, e.g. {small[:5]}")
        p(f"- the oracle, fed only generated inputs, returns **{verdict.verdict.value}**: "
          f"{verdict.counterexample}\n")
    else:
        p("\n=== 2. Type-directed generation (no hand-written gen_input) ===")
        p(f"  signature -> arg types {[type(t).__name__ for t in arg_types]}; "
          f"{len(small)} small inputs e.g. {small[:4]}")
        p(f"  audit of generated task -> {verdict.verdict.value}: {verdict.counterexample}")

    # -- 3. trained adversary: bandit + transfer over a stream ------------- #
    client = MockAxleClient()
    base = verina_like_tasks()
    stream = (base * 6)  # a stream of recurring spec shapes
    naive_total = sum(naive_evaluations(t, client) for t in stream)
    policy, memory = AdaptiveHackPolicy(), WitnessMemory()
    learned_total = 0
    for t in stream:
        r = probe_reward_hacks_learned(t, client, policy=policy, memory=memory)
        learned_total += r.candidates_tried
    if md:
        p("## 3. Trained adversary -> learn which hacks pay off, transfer across tasks\n")
        p(f"Over a stream of {len(stream)} tasks, candidate evaluations before a catch:\n")
        p(f"- fixed-order baseline: **{naive_total}**")
        p(f"- UCB bandit + transfer memory: **{learned_total}** "
          f"({100*(naive_total-learned_total)/naive_total:.0f}% fewer)\n")
        p("Learned family values (1.0 = always caught a bug):\n")
        p("| family | value | pulls |")
        p("|---|---|---|")
        for f in sorted(policy.value, key=policy.value.get, reverse=True):
            p(f"| {f} | {policy.value[f]:.2f} | {policy.counts[f]} |")
    else:
        p("\n=== 3. Trained adversary (UCB bandit + transfer memory) ===")
        p(f"  stream of {len(stream)} tasks: fixed-order {naive_total} evals  ->  "
          f"learned {learned_total} evals "
          f"({100*(naive_total-learned_total)/naive_total:.0f}% fewer)")
        top = sorted(policy.value, key=policy.value.get, reverse=True)[:3]
        p(f"  top families: " + ", ".join(f"{f}={policy.value[f]:.2f}" for f in top))

    # trigger-structure search on the conjunctive sleeper
    needle = next(c for c in sleeper_claims() if c.name == "needle_dim5")
    trig = conjunctive_trigger_search(needle)
    if md:
        p("\nTrigger-structure search on a 5-D conjunctive sleeper:\n")
        p(f"- {trig.one_line()}\n")
    else:
        p("\n  trigger search: " + trig.one_line())

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

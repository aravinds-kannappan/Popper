"""M4: exact falsification, PAC certificates, type-directed generation, trained adversary.

Pins the property that makes each an actual scaling gain over sampling alone:
  * Fourier-Motzkin decides linear systems exactly (witness or real UNSAT);
  * the SMT oracle finds measure-zero bugs and issues certificates a sampler can't;
  * the Clopper-Pearson bound is sound and tightens like 1/N;
  * a signature alone yields generators that catch a real spec bug;
  * the bandit + memory finds reward hacks in no more tries than fixed order, and
    trigger search recovers the conjunctive sleeper structure, not just a point.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falsify import (  # noqa: E402
    SMTOracle, symbolic_library, Verdict, con, fm_solve,
    bug_rate_upper_bound, certify_result, NumericalOracle,
    parse_signature, gen, enumerate_small, small_inputs_for, gen_inputs_for,
    TInt, TList, TBool, Task, CodeSpecOracle, MockAxleClient,
    AdaptiveHackPolicy, WitnessMemory, probe_reward_hacks_learned,
    naive_evaluations, conjunctive_trigger_search, sleeper_claims, verina_like_tasks,
)
from falsify.bench.corpus import math_items  # noqa: E402

try:
    import z3  # noqa: F401
    HAVE_Z3 = True
except Exception:
    HAVE_Z3 = False


class TestFourierMotzkin(unittest.TestCase):
    def test_infeasible_system_is_certified_unsat(self):
        # x0>=0, x1>=0, x0+x1<0  ->  unsat
        cons = [con({"x0": -1}, 0), con({"x1": -1}, 0), con({"x0": 1, "x1": 1}, 0, strict=True)]
        sol = fm_solve(cons, ["x0", "x1"])
        self.assertFalse(sol.sat)
        self.assertTrue(sol.certificate)

    def test_feasible_system_returns_a_valid_witness(self):
        cons = [con({"x0": 1, "x1": 1}, 0, strict=True)]   # x0 + x1 < 0
        sol = fm_solve(cons, ["x0", "x1"])
        self.assertTrue(sol.sat)
        w = sol.witness
        self.assertLess(float(w["x0"]) + float(w["x1"]), 0.0)


class TestSMTOracle(unittest.TestCase):
    def setUp(self):
        self.results = {c.name: (c, SMTOracle().audit(c)) for c in symbolic_library()}

    def test_unsound_abs_is_falsified_at_zero(self):
        c, r = self.results["abs_strictly_positive"]
        self.assertEqual(r.verdict, Verdict.FALSIFIED)
        self.assertEqual(r.details["backend"], "enum")
        self.assertIn("x=0", r.counterexample)

    def test_faithful_abs_gets_a_certificate(self):
        c, r = self.results["abs_value_faithful"]
        self.assertEqual(r.verdict, Verdict.FAITHFUL)
        self.assertTrue(r.details["certificate"])

    def test_measure_zero_needle_found_exactly(self):
        c, r = self.results["rare_int_needle"]
        self.assertEqual(r.verdict, Verdict.FALSIFIED)
        self.assertIn("n=7", r.counterexample)

    def test_linear_overclaim_falsified_and_true_statement_certified(self):
        self.assertEqual(self.results["mean_nonneg_overclaim"][1].verdict, Verdict.FALSIFIED)
        cert = self.results["nonneg_sum_certificate"][1]
        self.assertEqual(cert.verdict, Verdict.FAITHFUL)
        self.assertTrue(cert.details["certificate"])
        self.assertEqual(cert.details["backend"], "fourier-motzkin")

    def test_nonlinear_needs_z3_else_inconclusive(self):
        c, r = self.results["amgm_flipped_nonlinear"]
        if HAVE_Z3:
            self.assertEqual(r.verdict, Verdict.FALSIFIED)
        else:
            self.assertEqual(r.verdict, Verdict.INCONCLUSIVE)


class TestCertify(unittest.TestCase):
    def test_rule_of_three_for_zero_failures(self):
        b = bug_rate_upper_bound(3000, failures=0, delta=0.05)
        self.assertAlmostEqual(b.eps, 1 - 0.05 ** (1 / 3000), places=9)
        self.assertLess(b.eps, 0.002)

    def test_bound_tightens_with_more_draws(self):
        e100 = bug_rate_upper_bound(100).eps
        e10000 = bug_rate_upper_bound(10000).eps
        self.assertLess(e10000, e100)
        self.assertLess(e10000, 0.001)

    def test_bound_with_failures_is_above_empirical_rate(self):
        b = bug_rate_upper_bound(1000, failures=10, delta=0.05)
        self.assertGreater(b.eps, 0.01)      # above the 1% empirical rate
        self.assertLess(b.eps, 0.05)

    def test_certify_attaches_only_to_sampling_faithful(self):
        item = next(it for it in math_items() if it.family == "faithful")
        faithful = NumericalOracle(n_trials=2000).audit(item.math)
        self.assertIsNotNone(certify_result(faithful))
        bad = next(it for it in math_items() if it.family == "dropped-hypothesis")
        falsified = NumericalOracle(n_trials=2000).audit(bad.math)
        self.assertIsNone(certify_result(falsified))


class TestTypegen(unittest.TestCase):
    def test_parse_signature(self):
        args, ret = parse_signature("max2 : Int -> Int -> Int")
        self.assertEqual(len(args), 2)
        self.assertIsInstance(args[0], TInt)
        args2, _ = parse_signature("sort : List Int -> List Int")
        self.assertIsInstance(args2[0], TList)

    def test_enumerate_small_is_systematic(self):
        self.assertEqual(list(enumerate_small(TBool())), [False, True])
        self.assertEqual(set(enumerate_small(TInt(), scope=2)), set(range(-2, 3)))
        lists = list(enumerate_small(TList(TInt()), scope=1))
        self.assertIn([], lists)          # the empty-list edge case is covered

    def test_generated_inputs_audit_a_real_bug(self):
        import random
        sig = "max2 : Int -> Int -> Int"
        arg_types, _ = parse_signature(sig)
        task = Task(
            name="max_gen", description="max", signature=sig,
            reference="m", spec="weak",
            impls_py={"m": lambda a, b: max(a, b), "bad": lambda a, b: max(a, b) + 1},
            spec_py={"weak": lambda args, o: o >= args[0] and o >= args[1]},
            wrong_impls=["bad"], test_inputs=small_inputs_for(arg_types, scope=1),
            gen_input=gen_inputs_for(arg_types))
        r = CodeSpecOracle(MockAxleClient()).audit(task)
        self.assertEqual(r.verdict, Verdict.INCOMPLETE)


class TestAdversary(unittest.TestCase):
    def setUp(self):
        self.client = MockAxleClient()
        self.tasks = {t.name: t for t in verina_like_tasks()}

    def test_memory_transfers_a_winning_family(self):
        mem = WitnessMemory()
        sort = self.tasks["sort_by_length"]
        mem.record(sort, "declared")
        self.assertIn("declared", mem.suggest(sort))

    def test_bandit_learns_and_does_not_do_worse_than_fixed_order(self):
        client = self.client
        stream = list(verina_like_tasks()) * 6
        naive = sum(naive_evaluations(t, client) for t in stream)
        policy, mem = AdaptiveHackPolicy(), WitnessMemory()
        learned = 0
        for t in stream:
            r = probe_reward_hacks_learned(t, client, policy=policy, memory=mem)
            learned += r.candidates_tried
            # the hackable tasks must still be caught under the learned order
            if t.name in ("sort_by_length", "max_lower_bound_only"):
                self.assertTrue(r.hacked)
        self.assertLessEqual(learned, naive)

    def test_trigger_search_recovers_the_conjunction(self):
        needle = next(c for c in sleeper_claims() if c.name == "needle_dim5")
        trig = conjunctive_trigger_search(needle)
        self.assertTrue(trig.found)
        self.assertGreaterEqual(len(trig.trigger_coords), 4)  # most/all 5 coords constrained


if __name__ == "__main__":
    unittest.main()

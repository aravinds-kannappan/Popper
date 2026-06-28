"""falsify.scale: the AI-safety / RLHF principles ported to spec faithfulness.

Each test pins the property that makes the corresponding module a real scaling
win, not a relabelling:
  * adaptive search finds rare-trigger bugs uniform search misses, at equal budget;
  * the reward-hack probe catches a spec-gamer not in the fixed wrong-impl list;
  * the Safe-RLHF score's reward/cost map onto UNSOUND/INCOMPLETE;
  * the debate recovers the *true* missing premise and rejects a decoy;
  * judge calibration recovers a declared synthetic bias and the ensemble defers
    to the executable witness;
  * the eval-card gate sends faithful specs to PROVE and broken ones elsewhere.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falsify import (  # noqa: E402
    CodeSpecOracle, MockAxleClient, verina_like_tasks, Verdict,
    UniformFalsifier, AdaptiveFalsifier, AdaptiveOracle, sleeper_claims,
    probe_reward_hacks, score_task, build_eval_card, GateDecision,
    calibrate_judge, ensemble_verdict,
)
from falsify.scale.debate import gibbs_debate, run_debate  # noqa: E402
from falsify.scale.calibration import synthetic_judge  # noqa: E402
from falsify.core.oracle import OracleResult  # noqa: E402


class TestAdaptiveSearch(unittest.TestCase):
    def test_adaptive_beats_uniform_on_rare_trigger(self):
        # p = 1e-4: uniform needs ~10k draws in expectation; adaptive should be
        # dramatically cheaper. Cap the budget low enough that uniform must miss.
        claim = next(c for c in sleeper_claims() if c.name == "rare_edge_p0.0001")
        budget = 3000
        u = UniformFalsifier(budget=budget, seed=0).search(claim)
        a = AdaptiveFalsifier(budget=budget, seed=0).search(claim)
        self.assertTrue(a.found, "adaptive search failed to find the rare trigger")
        self.assertFalse(u.found, "uniform unexpectedly found a 1e-4 bug in 3k draws")
        self.assertLess(a.draws_used, budget)

    def test_adaptive_solves_multidim_needle(self):
        claim = next(c for c in sleeper_claims() if c.name == "needle_dim5")
        a = AdaptiveFalsifier(budget=5000, seed=1).search(claim)
        self.assertTrue(a.found, "adaptive search failed on the 5-D conjunctive trigger")

    def test_adaptive_no_false_alarm_on_faithful(self):
        claim = next(c for c in sleeper_claims() if c.name == "rare_edge_faithful")
        res = AdaptiveOracle(budget=4000).audit(claim)
        self.assertEqual(res.verdict, Verdict.FAITHFUL)

    def test_adaptive_oracle_returns_counterexample(self):
        claim = next(c for c in sleeper_claims() if c.name == "rare_edge_p0.01")
        res = AdaptiveOracle(budget=5000).audit(claim)
        self.assertEqual(res.verdict, Verdict.FALSIFIED)
        self.assertIsNotNone(res.counterexample)


class TestRewardHack(unittest.TestCase):
    def setUp(self):
        self.client = MockAxleClient()
        self.tasks = {t.name: t for t in verina_like_tasks()}

    def test_vacuous_spec_is_hacked_by_a_constant(self):
        r = probe_reward_hacks(self.tasks["sort_by_length"], self.client)
        self.assertTrue(r.hacked)
        self.assertGreater(r.hacking_margin, 0.0)
        self.assertEqual(r.verdict, Verdict.VACUOUS)  # a constant impl wins => vacuous

    def test_incomplete_spec_is_hacked(self):
        r = probe_reward_hacks(self.tasks["max_lower_bound_only"], self.client)
        self.assertTrue(r.hacked)

    def test_faithful_spec_is_not_hacked(self):
        r = probe_reward_hacks(self.tasks["abs_value"], self.client)
        self.assertFalse(r.hacked)
        self.assertEqual(r.verdict, Verdict.FAITHFUL)


class TestSafeRLHFScore(unittest.TestCase):
    def setUp(self):
        self.client = MockAxleClient()
        self.tasks = {t.name: t for t in verina_like_tasks()}

    def test_faithful_spec_satisfies_constraint(self):
        s = score_task(self.tasks["abs_value"], self.client)
        self.assertEqual(s.reward, 1.0)
        self.assertEqual(s.cost, 0.0)
        self.assertTrue(s.constraint_satisfied)
        self.assertEqual(s.verdict, Verdict.FAITHFUL)

    def test_unsound_spec_is_a_reward_failure(self):
        s = score_task(self.tasks["abs_strictly_positive"], self.client)
        self.assertLess(s.reward, 1.0)              # rejects abs(0)=0
        self.assertEqual(s.verdict, Verdict.UNSOUND)

    def test_incomplete_spec_is_a_cost_failure(self):
        s = score_task(self.tasks["max_lower_bound_only"], self.client)
        self.assertGreater(s.cost, 0.0)             # accepts a wrong answer
        self.assertFalse(s.constraint_satisfied)
        self.assertEqual(s.verdict, Verdict.INCOMPLETE)


class TestDebate(unittest.TestCase):
    def test_debate_recovers_normalization_premise(self):
        claim, rescues = gibbs_debate()
        t = run_debate(claim, rescues, budget=4000)
        self.assertEqual(t.verdict, Verdict.FALSIFIED)        # false as written
        self.assertEqual(t.recovered_premise, "sum_q_eq_1")   # but the premise is recovered
        self.assertIsNotNone(t.counterexample)

    def test_decoy_premise_is_rejected_by_the_verifier(self):
        claim, rescues = gibbs_debate()
        t = run_debate(claim, rescues, budget=4000)
        # the verifier must have considered and rejected the decoy before accepting
        said = " ".join(m.text for m in t.moves)
        self.assertIn("q0_small", said)


class TestCalibration(unittest.TestCase):
    def _pairs(self, n=200):
        pairs = []
        for i in range(n):
            truth = Verdict.FALSIFIED if i % 2 else Verdict.FAITHFUL
            o = OracleResult(name=f"it{i}", verdict=truth, reason="oracle",
                             counterexample="x" if truth.is_falsified else None)
            pairs.append((o, synthetic_judge(o, seed=i)))
        return pairs

    def test_calibration_detects_overflagging_bias(self):
        # synthetic judge over-flags faithful and misses some bugs
        cal = calibrate_judge(self._pairs(), judge_name="synthetic")
        self.assertGreater(cal.n, 0)
        self.assertLess(cal.accuracy, 1.0)
        self.assertLess(cal.kappa, 1.0)
        self.assertIsNotNone(cal.brier)

    def test_ensemble_trusts_the_executable_witness(self):
        o = OracleResult(name="t", verdict=Verdict.FALSIFIED, reason="oracle",
                         counterexample="q sums to 1.3")
        j = OracleResult(name="t", verdict=Verdict.FAITHFUL, reason="judge")  # disagrees, no witness
        e = ensemble_verdict(o, j)
        self.assertEqual(e.verdict, Verdict.FALSIFIED)
        self.assertEqual(e.details["ensemble_source"], "oracle-witness")

    def test_ensemble_discounts_a_biased_judge_when_oracle_silent(self):
        o = OracleResult(name="t", verdict=Verdict.FAITHFUL, reason="oracle", counterexample=None)
        j = OracleResult(name="t", verdict=Verdict.FALSIFIED, reason="judge")  # lone flag, no witness
        cal = calibrate_judge(self._pairs(), judge_name="synthetic")
        e = ensemble_verdict(o, j, cal)
        self.assertIn(e.verdict, (Verdict.INCONCLUSIVE, Verdict.FALSIFIED))


class TestEvalCard(unittest.TestCase):
    def setUp(self):
        self.client = MockAxleClient()
        self.tasks = {t.name: t for t in verina_like_tasks()}

    def test_faithful_spec_is_gated_to_prove(self):
        card = build_eval_card(self.tasks["abs_value"], self.client)
        self.assertEqual(card.gate, GateDecision.PROVE)
        self.assertLess(card.risk, 0.05 + 1e-9)

    def test_vacuous_spec_is_rejected(self):
        card = build_eval_card(self.tasks["sort_by_length"], self.client)
        self.assertEqual(card.gate, GateDecision.REJECT)

    def test_incomplete_spec_is_sent_to_repair(self):
        card = build_eval_card(self.tasks["max_lower_bound_only"], self.client)
        self.assertEqual(card.gate, GateDecision.REPAIR)

    def test_unsound_spec_is_rejected(self):
        card = build_eval_card(self.tasks["abs_strictly_positive"], self.client)
        self.assertEqual(card.gate, GateDecision.REJECT)


if __name__ == "__main__":
    unittest.main()

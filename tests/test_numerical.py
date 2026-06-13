"""The numerical oracle must pass faithful statements and falsify unfaithful ones."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falsify import NumericalOracle, information_theory_library, Verdict


class TestNumericalOracle(unittest.TestCase):
    def setUp(self):
        self.oracle = NumericalOracle(n_trials=2000, seed=0)
        self.lib = {s.name: s for s in information_theory_library()}

    def test_every_statement_matches_its_ground_truth_label(self):
        for stmt in self.lib.values():
            with self.subTest(stmt=stmt.name):
                result = self.oracle.audit(stmt)
                self.assertEqual(
                    result.verdict, stmt.expected,
                    f"{stmt.name}: expected {stmt.expected}, got {result.verdict} "
                    f"({result.reason})",
                )

    def test_dropped_hypotheses_yield_counterexamples(self):
        for name in ("kl_nonneg_DROPPED_normalization",
                     "data_processing_DROPPED_markov",
                     "entropy_concave_WRONG_direction"):
            with self.subTest(stmt=name):
                result = self.oracle.audit(self.lib[name])
                self.assertEqual(result.verdict, Verdict.FALSIFIED)
                self.assertIsNotNone(result.counterexample)

    def test_faithful_statements_survive(self):
        for name in ("kl_nonneg", "data_processing", "entropy_concave"):
            with self.subTest(stmt=name):
                self.assertTrue(self.oracle.audit(self.lib[name]).ok)

    def test_vacuity_is_flagged(self):
        result = self.oracle.audit(self.lib["entropy_uniform_vacuous_guard"])
        self.assertEqual(result.verdict, Verdict.INCONCLUSIVE)

    def test_determinism(self):
        a = self.oracle.audit(self.lib["kl_nonneg_DROPPED_normalization"])
        b = NumericalOracle(n_trials=2000, seed=0).audit(
            self.lib["kl_nonneg_DROPPED_normalization"])
        self.assertEqual(a.counterexample, b.counterexample)


if __name__ == "__main__":
    unittest.main()

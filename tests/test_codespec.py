"""The code-spec oracle must return the right verdict for each fixture."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falsify import CodeSpecOracle, MockAxleClient, verina_like_tasks, Verdict

EXPECTED = {
    "sort_by_length": Verdict.VACUOUS,
    "max_lower_bound_only": Verdict.INCOMPLETE,
    "abs_value": Verdict.FAITHFUL,
    "abs_strictly_positive": Verdict.UNSOUND,
}


class TestCodeSpecOracle(unittest.TestCase):
    def setUp(self):
        self.oracle = CodeSpecOracle(MockAxleClient())
        self.tasks = {t.name: t for t in verina_like_tasks()}

    def test_verdicts(self):
        for name, expected in EXPECTED.items():
            with self.subTest(task=name):
                result = self.oracle.audit(self.tasks[name])
                self.assertEqual(
                    result.verdict, expected,
                    f"{name}: expected {expected}, got {result.verdict} ({result.reason})",
                )

    def test_unfaithful_results_carry_a_counterexample(self):
        for name in ("sort_by_length", "max_lower_bound_only", "abs_strictly_positive"):
            with self.subTest(task=name):
                self.assertIsNotNone(self.oracle.audit(self.tasks[name]).counterexample)

    def test_faithful_has_no_counterexample(self):
        self.assertIsNone(self.oracle.audit(self.tasks["abs_value"]).counterexample)


if __name__ == "__main__":
    unittest.main()

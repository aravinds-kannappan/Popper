"""M2: the repair loop must drive every unfaithful fixture to FAITHFUL."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falsify import (CodeSpecOracle, FunctionalSpecRepairer, MockAxleClient,
                    default_repairer, repair_loop, verina_like_tasks, Verdict)

UNFAITHFUL = {"sort_by_length", "max_lower_bound_only", "abs_strictly_positive"}


class TestRepair(unittest.TestCase):
    def setUp(self):
        self.oracle = CodeSpecOracle(MockAxleClient())
        self.tasks = {t.name: t for t in verina_like_tasks()}

    def test_template_repair_reaches_faithful(self):
        for name, task in self.tasks.items():
            with self.subTest(task=name):
                trace = repair_loop(task, self.oracle, default_repairer())
                self.assertTrue(trace.success, f"{name} did not reach FAITHFUL: "
                                               f"{[r.verdict.value for r in trace.rounds]}")
                self.assertEqual(trace.final, Verdict.FAITHFUL)

    def test_unfaithful_tasks_take_at_least_one_repair(self):
        for name in UNFAITHFUL:
            with self.subTest(task=name):
                trace = repair_loop(self.tasks[name], self.oracle, default_repairer())
                self.assertGreater(len(trace.rounds), 1)
                self.assertTrue(trace.rounds[0].verdict.is_falsified)

    def test_already_faithful_needs_no_repair(self):
        trace = repair_loop(self.tasks["abs_value"], self.oracle, default_repairer())
        self.assertEqual(len(trace.rounds), 1)

    def test_generic_functional_repairer_alone_converges(self):
        for name in UNFAITHFUL:
            with self.subTest(task=name):
                trace = repair_loop(self.tasks[name], self.oracle, FunctionalSpecRepairer())
                self.assertTrue(trace.success)


if __name__ == "__main__":
    unittest.main()

"""The benchmark must reproduce: Popper catches the unfaithful specs the proof
checker cannot, with no false positives, and detection of subtle bugs improves
as the search budget grows."""

import unittest

from falsify.bench.corpus import benchmark_corpus
from falsify.bench.judges import popper_judge, proof_checker_judge
from falsify.bench.metrics import score_judge
from falsify.bench.run import budget_sweep
from falsify.core.oracle import Verdict


class BenchmarkTest(unittest.TestCase):
    def setUp(self):
        self.items = benchmark_corpus()

    def test_corpus_is_labelled_and_large(self):
        self.assertGreaterEqual(len(self.items), 300)
        for it in self.items:
            self.assertIn(it.surface, ("math", "code", "verina"))
            self.assertIsInstance(it.gold, Verdict)

    def test_math_statements_match_their_gold_label(self):
        # The oracle must agree with each math item's ground truth. Subtle
        # "rare-edge" bugs only fail on a tiny fraction of inputs, so they need a
        # large budget to be caught reliably.
        for it in self.items:
            if it.surface != "math":
                continue
            n = 300_000 if it.family == "rare-edge" else 1500
            res = popper_judge(it, n_trials=n, seed=0)
            self.assertEqual(res.verdict, it.gold, msg=f"{it.name}: {res.verdict} != {it.gold}")

    def test_popper_beats_proof_checker(self):
        popper = score_judge("popper", [(it, popper_judge(it, n_trials=2000)) for it in self.items])
        checker = score_judge("proof_checker", [(it, proof_checker_judge(it)) for it in self.items])

        # No false positives, and every detection carries a counterexample.
        self.assertEqual(popper.false_positive_rate, 0.0)
        self.assertEqual(popper.counterexample_yield, 1.0)
        # At a modest budget Popper catches nearly everything; the few it misses
        # are the rarest subtle bugs (see the budget sweep).
        self.assertGreaterEqual(popper.recall, 0.95)

        # The proof checker, by construction, catches none of them.
        self.assertEqual(checker.recall, 0.0)
        self.assertEqual(checker.tp, 0)

    def test_budget_sweep_improves_recall(self):
        rows = budget_sweep(budgets=(100, 50000))
        low, high = rows[0], rows[-1]
        # Spending more draws never hurts and catches strictly more subtle bugs.
        self.assertGreater(high["rare_recall"], low["rare_recall"])
        self.assertEqual(high["rare_recall"], 1.0)


if __name__ == "__main__":
    unittest.main()

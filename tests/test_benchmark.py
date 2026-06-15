"""The benchmark must reproduce: Popper catches the unfaithful specs the proof
checker cannot, and never flags a faithful one."""

import unittest

from falsify.bench.corpus import benchmark_corpus
from falsify.bench.judges import popper_judge, proof_checker_judge
from falsify.bench.metrics import score_judge
from falsify.core.oracle import Verdict


class BenchmarkTest(unittest.TestCase):
    def setUp(self):
        self.items = benchmark_corpus()

    def test_corpus_is_labelled_and_nonempty(self):
        self.assertGreaterEqual(len(self.items), 30)
        for it in self.items:
            self.assertIn(it.surface, ("math", "code", "verina"))
            self.assertIsInstance(it.gold, Verdict)

    def test_math_statements_match_their_gold_label(self):
        # The Monte-Carlo oracle must agree with each math item's ground truth.
        for it in self.items:
            if it.surface != "math":
                continue
            res = popper_judge(it, n_trials=2000, seed=0)
            self.assertEqual(res.verdict, it.gold, msg=f"{it.name}: {res.verdict} != {it.gold}")

    def test_popper_beats_proof_checker(self):
        popper = score_judge("popper", [(it, popper_judge(it)) for it in self.items])
        checker = score_judge("proof_checker", [(it, proof_checker_judge(it)) for it in self.items])

        # Popper catches every unfaithful spec, with a counterexample, no false positives.
        self.assertEqual(popper.recall, 1.0)
        self.assertEqual(popper.false_positive_rate, 0.0)
        self.assertEqual(popper.counterexample_yield, 1.0)

        # The proof checker, by construction, catches none of them.
        self.assertEqual(checker.recall, 0.0)
        self.assertEqual(checker.tp, 0)


if __name__ == "__main__":
    unittest.main()

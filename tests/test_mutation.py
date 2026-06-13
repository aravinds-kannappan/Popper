"""The mutation engine must actually produce changed source and fuzz inputs."""

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falsify.speccheck.mutation import available_ops, fuzz_int, fuzz_list_int, mutate


class TestMutation(unittest.TestCase):
    def test_mutants_change_source(self):
        src = "def f (a b : Int) : Int := a + b"
        mutants = mutate(src)
        self.assertTrue(mutants)
        for m in mutants:
            self.assertNotEqual(m.source, src)
            self.assertIn(m.op, available_ops())

    def test_specific_operator_fires(self):
        mutants = {m.op: m.source for m in mutate("a + b", ["arith_plus_to_minus"])}
        self.assertEqual(mutants["arith_plus_to_minus"], "a - b")

    def test_fuzzers_respect_bounds_and_hit_edges(self):
        rng = random.Random(0)
        seen = {fuzz_int(rng, -10, 10) for _ in range(500)}
        self.assertTrue(all(-10 <= x <= 10 for x in seen))
        self.assertIn(0, seen)  # edge-case bias
        for _ in range(50):
            xs = fuzz_list_int(rng, max_len=6)
            self.assertLessEqual(len(xs), 6)


if __name__ == "__main__":
    unittest.main()

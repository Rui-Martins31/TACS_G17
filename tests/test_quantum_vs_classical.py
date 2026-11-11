import unittest
from dataclasses import replace
from math import sqrt

from models.gas_defaults import DEFAULT_CONFIG
from models.instances.medium_conference import build
from transformations.ilp_to_gas import search
from transformations.problem_to_ilp import transform
from validation.quantum_vs_classical import (
    amplification, best_iterations, gas_statistics, ideal_probability,
)


class TestGroverFormula(unittest.TestCase):
    def test_ideal_probability_limits(self):
        self.assertEqual(ideal_probability(0, 16, 3), 0.0)
        self.assertAlmostEqual(ideal_probability(3, 16, 0), 3 / 16)   # k=0: uniform sampling
        self.assertAlmostEqual(ideal_probability(16, 16, 0), 1.0)
        # M/N = 1/4: one iteration reaches the marked set exactly (Boyer et al. 1998).
        self.assertAlmostEqual(ideal_probability(1, 4, 1), 1.0)

    def test_best_iterations(self):
        self.assertEqual(best_iterations(1, 512), 17)
        self.assertEqual(best_iterations(1, 16), 3)
        self.assertEqual(best_iterations(0, 16), 0)


class TestSearchHistory(unittest.TestCase):
    def test_history_counts_rounds_and_oracle_calls(self):
        ilp, mapping = transform(build())
        config = replace(DEFAULT_CONFIG, round_policy="fixed", fixed_iterations=2,
                         shots=3, max_rounds=4, seed=1)
        samples = [(1, 0, 1, 0)] * 3   # the optimum, found in round 1
        result = search(ilp, mapping, config, lambda *args: samples)
        self.assertEqual(len(result.history), result.rounds)
        self.assertEqual(result.oracle_calls, 4 * 2 * 3)
        self.assertEqual([r.improved for r in result.history], [True, False, False, False])
        self.assertEqual([r.threshold for r in result.history], [None, -7, -7, -7])


class TestAmplificationOnGeneratedCircuits(unittest.TestCase):
    """Measured marked-state frequencies on Aer agree with sin^2((2k+1)theta)."""

    def assert_close(self, rows):
        for r in rows:
            with self.subTest(marked=r.marked_set, k=r.iterations):
                sigma = sqrt(max(r.ideal * (1 - r.ideal), 1e-4) / r.shots)
                self.assertLess(abs(r.measured - r.ideal), 5 * sigma + 1e-9)

    def test_medium_valid_and_optimal(self):
        self.assert_close(amplification("medium", shots=1024))

    def test_multi_optima(self):
        self.assert_close(amplification("multi_optima", shots=1024))

    def test_infeasible_never_measures_a_valid_selection(self):
        rows = amplification("infeasible", iterations=[0, 1, 2], shots=256)
        self.assertEqual([r.measured for r in rows], [0.0, 0.0, 0.0])


class TestGasStatistics(unittest.TestCase):
    def test_tiny_and_infeasible(self):
        tiny = gas_statistics("tiny", runs=3)
        self.assertEqual((tiny.successes, tiny.qubits, tiny.brute_force_evaluations), (3, 8, 8))
        self.assertTrue(all(b <= t for b, t in zip(tiny.oracle_calls_to_best, tiny.oracle_calls)))
        infeasible = gas_statistics("infeasible", runs=2)
        self.assertEqual(infeasible.successes, 2)


if __name__ == "__main__":
    unittest.main()

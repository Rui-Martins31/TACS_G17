import unittest
from dataclasses import replace

from models.gas_defaults import DEFAULT_CONFIG
from models.instances.tiny_conference import build
from transformations.ilp_to_gas import search
from transformations.problem_to_ilp import transform


class TestSolverConfig(unittest.TestCase):
    def test_invalid_config(self):
        for kwargs in ({"shots": 0}, {"round_policy": "unknown"},
                       {"growth_factor": float("nan")}, {"initial_window": 99},
                       {"max_rounds": 0}, {"backend": ""}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                replace(DEFAULT_CONFIG, **kwargs)

    def test_fixed_policy_threshold_and_stopping(self):
        ilp, mapping = transform(build())
        config = replace(DEFAULT_CONFIG, round_policy="fixed", fixed_iterations=3,
                         max_rounds=10, max_rounds_without_improvement=2, shots=4)
        calls = []

        def sampler(oracle, layout, iterations, received):
            calls.append((set(layout.atom_qubits), iterations, received))
            return [(1, 0, 1, 0)]  # A + C, objective -7

        result = search(ilp, mapping, config, sampler)
        self.assertEqual((result.bits, result.objective, result.rounds), ((1, 0, 1, 0), -7, 3))
        self.assertEqual(result.stop_reason, "max_rounds_without_improvement")
        self.assertNotIn("objective_threshold", calls[0][0])
        self.assertIn("objective_threshold", calls[1][0])
        self.assertTrue(all(iterations == 3 and received is config for _, iterations, received in calls))

    def test_no_sample_is_not_reported_as_infeasible(self):
        ilp, mapping = transform(build())
        config = replace(DEFAULT_CONFIG, max_rounds=2, max_rounds_without_improvement=5)
        result = search(ilp, mapping, config, lambda *args: [])
        self.assertIsNone(result.bits)
        self.assertEqual(result.stop_reason, "max_rounds")

    def test_adaptive_policy_is_seeded_and_bounded(self):
        ilp, mapping = transform(build())
        config = replace(DEFAULT_CONFIG, initial_window=3, max_window=5, growth_factor=2,
                         max_rounds=8, max_rounds_without_improvement=8)
        def run():
            calls = []
            def sampler(oracle, layout, iterations, received):
                calls.append(iterations)
                return []
            search(ilp, mapping, config, sampler)
            return calls
        first = run()
        self.assertEqual(first, run())
        self.assertTrue(all(0 <= iteration < 5 for iteration in first))
        self.assertLess(first[0], 3)


if __name__ == "__main__":
    unittest.main()

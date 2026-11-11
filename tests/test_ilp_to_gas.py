"""Deterministic controller and execution-boundary tests; no simulator sampling."""

import unittest
from dataclasses import replace
from itertools import product
from unittest.mock import patch

from besser.BUML.metamodel.quantum import quantum as bq

from models.gas_defaults import DEFAULT_CONFIG
from models.instances.infeasible_retreat import build as infeasible
from models.instances.medium_conference import build
from transformations.ilp_to_gas import quantum_sampler, search
from transformations.ilp_to_oracle import build_oracle
from transformations.problem_to_ilp import transform
from validation.classical_baseline import solve


class TestGASController(unittest.TestCase):
    def test_only_feasible_improvements_update_threshold_and_best(self):
        source = build()
        ilp, mapping = transform(source)
        batches = iter([
            [(1, 1, 1, 1)],  # infeasible, despite the attractive objective
            [(0, 1, 0, 0)],  # first feasible: -2
            [(1, 1, 1, 1), (0, 1, 0, 0), (0, 0, 0, 0), (1, 0, 1, 0)],
            [(1, 0, 1, 0), (0, 0, 0, 0)],  # equal and worse
            [(1, 1, 1, 1)],
        ])
        config = replace(DEFAULT_CONFIG, max_rounds=20, max_rounds_without_improvement=2)
        with patch("transformations.ilp_to_gas.build_oracle", wraps=build_oracle) as oracle:
            result = search(ilp, mapping, config, lambda *args: next(batches))
        constants = [call.args[2][0].constant if call.args[2] else None
                     for call in oracle.call_args_list]
        self.assertEqual(constants, [None, None, 3, 8, 8])
        self.assertEqual((result.bits, result.objective), ((1, 0, 1, 0), -7))
        self.assertEqual((result.rounds, result.stop_reason),
                         (5, "max_rounds_without_improvement"))
        baseline = solve(source)
        self.assertIn(frozenset(result.selected_activities(mapping)), baseline.optimal_selections)
        self.assertEqual(-result.objective, baseline.optimum_value)

    def test_adaptive_window_and_failure_counter_reset_on_improvement(self):
        ilp, mapping = transform(build())
        config = replace(DEFAULT_CONFIG, initial_window=2, max_window=8, growth_factor=2,
                         max_rounds=6, max_rounds_without_improvement=4)
        batches = iter([[], [], [(1, 0, 0, 0)], [], [], []])
        with patch("transformations.ilp_to_gas.Random") as random:
            random.return_value.randrange.side_effect = lambda upper: upper - 1
            result = search(ilp, mapping, config, lambda *args: next(batches))
        self.assertEqual([c.args[0] for c in random.return_value.randrange.call_args_list],
                         [2, 4, 8, 2, 4, 8])
        self.assertEqual((result.rounds, result.stop_reason), (6, "max_rounds"))
        self.assertEqual((result.bits, result.objective), ((1, 0, 0, 0), -3))

    def test_no_samples_and_infeasible_instance_are_not_proofs(self):
        for source, samples in ((build(), []), (infeasible(), list(product((0, 1), repeat=4)))):
            ilp, mapping = transform(source)
            config = replace(DEFAULT_CONFIG, max_rounds=2, max_rounds_without_improvement=3)
            result = search(ilp, mapping, config, lambda *args: samples)
            self.assertIsNone(result.bits)
            self.assertIsNone(result.objective)
            self.assertIsNone(result.selected_activities(mapping))
            self.assertEqual(result.stop_reason, "max_rounds")
        self.assertEqual(solve(infeasible()).feasible_count, 0)

    def test_malformed_candidates_are_rejected(self):
        ilp, mapping = transform(build())
        for candidate in ((1,), (1, 0, 2, 0), (True, 0, 1, 0)):
            with self.subTest(candidate=candidate), self.assertRaisesRegex(ValueError, "bit tuples"):
                search(ilp, mapping, DEFAULT_CONFIG, lambda *args: [candidate])


class TestQuantumSamplerContract(unittest.TestCase):
    def test_configuration_measurements_decoding_and_advancing_seed(self):
        ilp, mapping = transform(build())
        oracle, layout = build_oracle(ilp, mapping)
        config = replace(DEFAULT_CONFIG, shots=3, backend="executor_selected_backend")

        def run():
            calls = []
            def execute(circuit, **options):
                calls.append(options)
                self.assertEqual(circuit.num_clbits, 4)
                measurements = [o for o in circuit.operations if isinstance(o, bq.Measurement)]
                self.assertEqual([(o.target_qubits[0], o.output_bit) for o in measurements],
                                 list(enumerate(layout.variable_qubits)))
                return {"0101": 2, "0010": 1}
            sampler = quantum_sampler(execute)
            for _ in range(2):
                self.assertEqual(sampler(oracle, layout, 0, config),
                                 [(1, 0, 1, 0), (1, 0, 1, 0), (0, 1, 0, 0)])
            self.assertTrue(all(c["backend"] == config.backend and c["shots"] == 3 for c in calls))
            return [c["seed"] for c in calls]
        seeds = run()
        self.assertEqual(seeds, run())
        self.assertNotEqual(*seeds)

    def test_executor_counts_are_validated(self):
        ilp, mapping = transform(build())
        oracle, layout = build_oracle(ilp, mapping)
        for counts in ({"010": 1}, {"xxxx": 1}, {"0101": -1}, {"0101": True}, {"0101": 2}):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                quantum_sampler(lambda *args, **kwargs: counts)(oracle, layout, 0, DEFAULT_CONFIG)


if __name__ == "__main__":
    unittest.main()

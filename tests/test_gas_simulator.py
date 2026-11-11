"""Quantum checks via the test converter, not a production #8 generator."""

import unittest
from dataclasses import replace
from itertools import product

import numpy as np
from qiskit import transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

from besser.BUML.metamodel.quantum import quantum as bq

from models.gas_defaults import DEFAULT_CONFIG
from models.instances._plan import PlanBuilder
from models.instances.infeasible_retreat import build as infeasible
from tests.test_ilp_to_oracle import basis_index, run_basis, to_qiskit
from transformations.ilp_to_gas import build_round, objective_atom, quantum_sampler, search
from transformations.ilp_to_oracle import Atom, build_oracle
from transformations.problem_to_ilp import transform
from validation.classical_baseline import solve


def unique_feasible_plan():
    plan = PlanBuilder("UniqueFeasible")
    plan.activity("B", 1, 0, 1)
    plan.activity("A", 2, 0, 1, mandatory=True)
    plan.conflict("A", "B", "test")
    return plan.build("unique_feasible")


def execute_for_test(circuit, *, backend, shots, seed):
    """Issue #8 stand-in: translate with the oracle TEST helper and run real Aer."""
    if backend != "aer_simulator":
        raise ValueError("test executor supports aer_simulator only")
    simulator = AerSimulator(max_parallel_threads=1)
    qc = transpile(to_qiskit(circuit), simulator, seed_transpiler=seed)
    return simulator.run(qc, shots=shots, seed_simulator=seed).result().get_counts()


class TestGroverRound(unittest.TestCase):
    def test_zero_and_repeated_iterations_amplify_and_clean_scratch(self):
        ilp, mapping = transform(unique_feasible_plan())
        oracle, layout = build_oracle(ilp, mapping)
        original = list(oracle.operations)
        # One marked assignment out of four: P(marked) = sin^2((2k+1)*pi/6).
        for iterations, expected_probability in ((0, 0.25), (1, 1.0), (2, 0.25)):
            with self.subTest(iterations=iterations):
                circuit = build_round(oracle, layout, iterations)
                state = Statevector.from_instruction(to_qiskit(circuit))
                index = basis_index((1, 0), layout.variable_qubits)
                self.assertAlmostEqual(abs(state.data[index]) ** 2, expected_probability, places=6)
                clean_probability = sum(abs(state.data[basis_index(bits, layout.variable_qubits)]) ** 2
                                        for bits in product((0, 1), repeat=2))
                self.assertAlmostEqual(clean_probability, 1.0, places=6)
                if iterations == 0:
                    self.assertTrue(np.allclose(state.probabilities(layout.variable_qubits), 0.25))
        self.assertEqual(oracle.operations, original)

    def test_diffuser_uses_only_decision_qubits(self):
        ilp, mapping = transform(unique_feasible_plan())
        oracle, layout = build_oracle(ilp, mapping)
        circuit = build_round(oracle, layout, 1)
        n = len(mapping)
        diffuser = circuit.operations[n + len(oracle.operations):]
        for op in diffuser:
            self.assertLessEqual(set(op.control_qubits + op.target_qubits), set(layout.variable_qubits))
        for invalid in (-1, True, 1.5):
            with self.subTest(iterations=invalid), self.assertRaises(ValueError):
                build_round(oracle, layout, invalid)

    def test_one_decision_qubit(self):
        plan = PlanBuilder("One")
        plan.activity("A", 1, 0, 1, mandatory=True)
        ilp, mapping = transform(plan.build("one"))
        oracle, layout = build_oracle(ilp, mapping)
        state = Statevector.from_instruction(to_qiskit(build_round(oracle, layout, 1)))
        self.assertAlmostEqual(sum(abs(state.data[i]) ** 2 for i in (0, 1)), 1.0)

    def test_strict_threshold_marks_only_better_assignments_and_resizes_layout(self):
        plan = PlanBuilder("Threshold")
        plan.activity("A", 1, 0, 1)
        plan.activity("B", 2, 0, 1)
        ilp, mapping = transform(plan.build("threshold"))
        objective = objective_atom(ilp, mapping)
        widths = []
        for best in (0, -1, -3):
            threshold = Atom(objective.name, "LE", objective.constant - best + 1,
                             objective.coefficients)
            oracle, layout = build_oracle(ilp, mapping, (threshold,))
            widths.append(layout.num_qubits)
            self.assertEqual(build_round(oracle, layout, 1).num_qubits, layout.num_qubits)
            for bits in product((0, 1), repeat=2):
                value = -bits[0] - 2 * bits[1]
                index = basis_index(bits, layout.variable_qubits)
                state = run_basis(oracle, index)
                expected = Statevector.from_int(index, 2 ** layout.num_qubits)
                if value < best:
                    expected = -expected
                self.assertTrue(np.allclose(state.data, expected.data, atol=1e-6), (best, bits))
        self.assertGreater(len(set(widths)), 1)


class TestAerSearch(unittest.TestCase):
    def test_round_measurement_order_and_classical_baseline(self):
        source = unique_feasible_plan()
        ilp, mapping = transform(source)
        config = replace(DEFAULT_CONFIG, round_policy="fixed", fixed_iterations=1, shots=8,
                         max_rounds=3, max_rounds_without_improvement=1)
        oracle, layout = build_oracle(ilp, mapping)
        samples = quantum_sampler(execute_for_test)(oracle, layout, 1, config)
        self.assertEqual(samples, [(1, 0)] * config.shots)
        result = search(ilp, mapping, config, quantum_sampler(execute_for_test))
        self.assertEqual(result.selected_activities(mapping), ("A",))
        baseline = solve(source)
        self.assertIn(frozenset(result.selected_activities(mapping)), baseline.optimal_selections)
        self.assertEqual(-result.objective, baseline.optimum_value)
        self.assertEqual((result.rounds, result.stop_reason),
                         (2, "max_rounds_without_improvement"))

    def test_supplied_infeasible_instance_has_no_feasible_sample(self):
        source = infeasible()
        ilp, mapping = transform(source)
        config = replace(DEFAULT_CONFIG, round_policy="fixed", fixed_iterations=1, shots=4,
                         max_rounds=2, max_rounds_without_improvement=3)
        result = search(ilp, mapping, config, quantum_sampler(execute_for_test))
        self.assertIsNone(result.bits)
        self.assertIsNone(result.objective)
        self.assertEqual(result.stop_reason, "max_rounds")
        self.assertEqual(solve(source).feasible_count, 0)


if __name__ == "__main__":
    unittest.main()

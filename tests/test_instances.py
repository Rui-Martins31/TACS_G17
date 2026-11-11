import unittest

from metamodels.problem_checks import check_model
from metamodels.problem_dsl import BOCL_UNSUPPORTED, problem_dsl
from models.instances import BY_NAME, INSTANCES
from validation.classical_baseline import solve
from validation.qubit_count import QUBIT_BUDGET, count_qubits


class TestInstances(unittest.TestCase):
    def test_instances_are_valid_models(self):
        for inst in INSTANCES:
            with self.subTest(instance=inst.name):
                results = check_model(problem_dsl, inst.build(), BOCL_UNSUPPORTED)
                failing = [(r.constraint, r.holds, r.detail) for r in results if r.holds is not True]
                self.assertEqual(failing, [])

    def test_expected_optimum_matches_brute_force(self):
        for inst in INSTANCES:
            with self.subTest(instance=inst.name):
                result = solve(inst.build())
                self.assertEqual(result.optimum_value, inst.expected_value)
                self.assertEqual(set(result.optimal_selections), set(inst.expected_optima))

    def test_annex_a_coverage(self):
        """Annex A asks for: a unique-optimum case, several optima, and an infeasible one."""
        results = {i.name: solve(i.build()) for i in INSTANCES}
        self.assertTrue(any(len(r.optimal_selections) == 1 for r in results.values()))
        self.assertTrue(any(len(r.optimal_selections) > 1 for r in results.values()))
        self.assertTrue(any(r.optimum_value is None for r in results.values()))
        self.assertEqual(len({i.name for i in INSTANCES}), len(INSTANCES))

    def test_documented_benchmark_sizes(self):
        expected = {
            "tiny": (3, 1, 6),
            "multi_optima": (5, 2, 18),
            "medium": (4, 3, 8),
            "large": (9, 2, 96),
            "infeasible": (4, 1, 0),
        }
        results = {i.name: solve(i.build()) for i in INSTANCES}
        self.assertEqual(set(results), set(expected))
        for name, (n, m, feasible) in expected.items():
            with self.subTest(instance=name):
                result = results[name]
                self.assertEqual((result.n, result.m, result.feasible_count), (n, m, feasible))
        self.assertEqual(results["tiny"].n, min(r.n for r in results.values()))

    def test_qubit_counts(self):
        """Peak GAS circuit sizes; Annex A asks for instances up to and near ~20 qubits."""
        expected = {"tiny": 8, "infeasible": 10, "multi_optima": 14, "medium": 15, "large": 20}
        peaks = {i.name: count_qubits(i.build()).peak for i in INSTANCES}
        self.assertEqual(peaks, expected)
        self.assertLessEqual(max(peaks.values()), QUBIT_BUDGET)

    def test_qubit_count_matches_built_circuit(self):
        """The reported peak is the size of a real oracle with the widest threshold."""
        from transformations.ilp_to_gas import objective_atom
        from transformations.ilp_to_oracle import Atom, build_oracle
        from transformations.problem_to_ilp import transform

        ilp, mapping = transform(BY_NAME["medium"].build())
        objective = objective_atom(ilp, mapping)
        # Best value 1 ({D} alone) gives the widest threshold range, [-9, 1] -> 5 bits.
        threshold = Atom(objective.name, "LE", objective.constant + 1 + 1, objective.coefficients)
        _, layout = build_oracle(ilp, mapping, (threshold,))
        self.assertEqual(layout.num_qubits, count_qubits(BY_NAME["medium"].build()).peak)


if __name__ == "__main__":
    unittest.main()

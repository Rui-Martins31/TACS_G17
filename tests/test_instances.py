import unittest

from metamodels.problem_checks import check_model
from metamodels.problem_dsl import BOCL_UNSUPPORTED, problem_dsl
from models.instances import INSTANCES
from validation.classical_baseline import solve


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
            "tiny": (4, 3, 8),
            "multi_optima": (5, 2, 18),
            "medium": (7, 6, 15),
            "large": (9, 5, 60),
            "infeasible": (4, 1, 0),
        }
        results = {i.name: solve(i.build()) for i in INSTANCES}
        for name, (n, m, feasible) in expected.items():
            with self.subTest(instance=name):
                result = results[name]
                self.assertEqual((result.n, result.m, result.feasible_count), (n, m, feasible))
        self.assertEqual(results["tiny"].n, min(r.n for r in results.values()))


if __name__ == "__main__":
    unittest.main()

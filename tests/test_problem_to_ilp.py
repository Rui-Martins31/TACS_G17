"""Check T1's actual generated objects and their binary assignment semantics."""

import unittest
from itertools import product
from unittest.mock import patch

from besser.BUML.metamodel.object import ObjectModel
from besser.BUML.metamodel.object.builder import ObjectBuilder

from metamodels.problem_checks import CheckResult, linked, objects_of
from metamodels.problem_dsl import Activity, ActivityPlan
from metamodels.solution_checks import check_solution_model
from models.examples.tiny_conference import build
from tests.test_problem_dsl import add_conflict, add_second_plan, find
from tests.test_solution_dsl import evaluate_constraint, evaluate_expression, slot_value
from transformations.problem_to_ilp import transform


def independent_plan(names=("B", "A"), mandatory=()):
    """Overlapping activities with no resources or explicit conflicts."""
    activities = [ObjectBuilder(Activity).name(f"activity_{i}").attributes(
        name=name, value=i + 1, start=0, end=1, mandatory=name in mandatory).build()
        for i, name in enumerate(names)]
    plan = ObjectBuilder(ActivityPlan).name("plan").attributes(name="Independent").build()
    plan.activities = set(activities)
    return ObjectModel(name="independent", objects={plan, *activities})


def feasible_assignments(model, mapping):
    problem, = objects_of(model, "ILPProblem")
    objective, = linked(problem, "objective")
    roots = linked(problem, "root")
    return [(evaluate_expression(objective, assignment), bits)
            for bits in product((0, 1), repeat=len(mapping))
            for assignment in [dict(zip(mapping.values(), bits))]
            if not roots or evaluate_constraint(roots[0], assignment)]


def atom_signatures(model, mapping):
    indices = {variable: i for i, variable in enumerate(mapping.values())}
    return sorted((slot_value(atom, "comparison"),
                   slot_value(linked(atom, "linearExpression")[0], "constant"),
                   tuple(sorted((indices[linked(term, "variable")[0]],
                                 slot_value(term, "coefficient"))
                                for term in linked(linked(atom, "linearExpression")[0], "terms"))))
                  for atom in objects_of(model, "LinearConstraint"))


class TestProblemToILP(unittest.TestCase):
    def test_tiny_formulation_and_all_assignments(self):
        source = build()
        original_objects = set(source.objects)
        model, mapping = transform(source)
        self.assertEqual(set(source.objects), original_objects)
        self.assertTrue(set(model.objects).isdisjoint(source.objects))
        self.assertEqual(list(mapping), sorted(objects_of(source, "Activity"), key=lambda a: a.name))
        self.assertEqual([v.name for v in mapping.values()], [f"y_{i}" for i in range(4)])
        self.assertEqual([v.bitWidth for v in mapping.values()], [1] * 4)
        self.assertTrue(all(r.holds is True for r in check_solution_model(model)))
        self.assertEqual(atom_signatures(model, mapping), [
            ("LE", -1, ((0, 1), (1, 1))),
            ("LE", -1, ((1, 1), (2, 1))),
            ("LE", -1, ((2, 1), (3, 1))),
        ])
        expected = [(-sum(w * b for w, b in zip((3, 2, 4, 1), bits)), bits)
                    for bits in product((0, 1), repeat=4)
                    if all(bits[i] + bits[j] <= 1 for i, j in ((0, 1), (1, 2), (2, 3)))]
        actual = feasible_assignments(model, mapping)
        self.assertEqual(actual, expected)
        self.assertEqual(min(actual), (-7, (1, 0, 1, 0)))
        self.assertEqual(sum(value == -7 for value, _ in actual), 1)

    def test_case_sensitive_order_ignores_construction_order(self):
        for names in (("z", "a", "B", "A"), ("A", "B", "a", "z")):
            model, mapping = transform(independent_plan(names))
            self.assertEqual([(a.name, v.name) for a, v in mapping.items()],
                             [("A", "y_0"), ("B", "y_1"), ("a", "y_2"), ("z", "y_3")])
            problem, = objects_of(model, "ILPProblem")
            objective, = linked(problem, "objective")
            for activity, variable in mapping.items():
                self.assertEqual(evaluate_expression(objective, {v: int(v is variable)
                                                                 for v in mapping.values()}),
                                 -activity.value)

    def test_explicit_and_multiple_resource_conflicts_are_deduplicated(self):
        source = build()
        add_conflict(source, "explicit_b_a", "b", "a")
        for name in ("a", "b"):
            activity = find(source, name)
            activity.uses = set(linked(activity, "uses")) | {find(source, "ana")}
        model, mapping = transform(source)
        self.assertEqual(len(atom_signatures(model, mapping)), 3)
        self.assertEqual(sum(signature == ("LE", -1, ((0, 1), (1, 1)))
                             for signature in atom_signatures(model, mapping)), 1)

    def test_no_constraints_and_overlap_without_shared_resources(self):
        model, mapping = transform(independent_plan())
        problem, = objects_of(model, "ILPProblem")
        self.assertEqual(linked(problem, "root"), [])
        self.assertEqual(len(feasible_assignments(model, mapping)), 4)

    def test_single_mandatory_atom_is_root(self):
        model, mapping = transform(independent_plan(names=("A",), mandatory=("A",)))
        problem, = objects_of(model, "ILPProblem")
        root, = linked(problem, "root")
        self.assertEqual(root.classifier.name, "LinearConstraint")
        self.assertEqual(atom_signatures(model, mapping), [("EQ", 1, ((0, -1),))])
        self.assertEqual(feasible_assignments(model, mapping), [(-1, (1,))])

    def test_multiple_mandatory_atoms_are_conjoined(self):
        model, mapping = transform(independent_plan(mandatory=("A", "B")))
        problem, = objects_of(model, "ILPProblem")
        root, = linked(problem, "root")
        self.assertEqual(root.classifier.name, "LogicalConstraint")
        self.assertEqual(slot_value(root, "operator"), "AND")
        self.assertEqual(feasible_assignments(model, mapping), [(-3, (1, 1))])

    def test_conflicting_mandatory_activities_produce_valid_infeasible_ilp(self):
        source = build()
        find(source, "a").mandatory = True
        find(source, "b").mandatory = True
        model, mapping = transform(source)
        self.assertEqual(feasible_assignments(model, mapping), [])

    def test_invalid_input_reports_invariant(self):
        source = build()
        find(source, "a").value = 0
        with self.assertRaisesRegex(ValueError, "positiveValue"):
            transform(source)

    def test_malformed_input_reports_structure(self):
        source = independent_plan()
        orphan = ObjectBuilder(Activity).name("orphan").attributes(
            name="Orphan", value=1, start=0, end=1, mandatory=False).build()
        source.add_object(orphan)
        with self.assertRaisesRegex(ValueError, "structure"):
            transform(source)

    def test_requires_exactly_one_plan(self):
        source = build()
        add_second_plan(source)
        for model, count in ((source, 2), (ObjectModel(name="empty", objects=set()), 0)):
            with self.subTest(plans=count), self.assertRaisesRegex(
                    ValueError, f"exactly one ActivityPlan; found {count}"):
                transform(model)

    def test_unevaluated_input_check_is_rejected(self):
        with patch("transformations.problem_to_ilp.check_model", return_value=[
                CheckResult("validInterval", None, "B-OCL", "evaluation failed")]):
            with self.assertRaisesRegex(ValueError, "validInterval.*evaluation failed"):
                transform(build())

    def test_invalid_or_unevaluated_generated_model_is_internal_error(self):
        for holds in (False, None):
            with self.subTest(holds=holds), patch(
                    "transformations.problem_to_ilp.check_solution_model", return_value=[
                        CheckResult("expressionOwner", holds, "B-OCL", "test failure")]):
                with self.assertRaisesRegex(RuntimeError, "expressionOwner.*test failure"):
                    transform(build())


if __name__ == "__main__":
    unittest.main()

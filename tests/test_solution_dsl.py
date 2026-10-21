"""Solution DSL regression tests using the project's actual checker and B-UML objects.

Place in tests/test_solution_dsl.py, then run from the repository root:
    python -m unittest tests.test_solution_dsl -v

Uses the ILPProblem / bitWidth metamodel, not the earlier ILPModel draft.
No mocks or replacement OCL evaluators are used.
"""
import unittest
from itertools import product

from besser.BUML.metamodel.object import ObjectModel
from besser.BUML.metamodel.object.builder import ObjectBuilder

from metamodels.checks import linked
from metamodels.solution_checks import check_solution_model
from metamodels.solution_dsl import (
    ILPProblem, IntegerVariable, LinearExpression, LinearTerm,
    LinearConstraint, LogicalConstraint,
)


def build_solution_example():
    """Hand-built ILP for tiny_conference: weights 3,2,4,1; edges AB,BC,CD.

    Returns (object_model, named_objects). Sets multi-valued links once, because
    repeated assignments to a B-UML association end may replace previous links.
    """
    named = {}

    def make(cls, identifier, **attributes):
        obj = ObjectBuilder(cls).name(identifier).attributes(**attributes).build()
        named[identifier] = obj
        return obj

    problem = make(ILPProblem, 'problem', name='TinyWorkshopILP')
    variables = [make(IntegerVariable, 'y_' + letter, name='y_' + letter, bitWidth=1)
                 for letter in 'ABCD']
    problem.variables = set(variables)

    def expression(identifier, constant, coefficients):
        expr = make(LinearExpression, identifier, constant=constant)
        terms = set()
        for letter, variable, coefficient in zip('ABCD', variables, coefficients):
            if coefficient:
                term = make(LinearTerm, identifier + '_term_' + letter,
                            coefficient=coefficient)
                term.variable = variable
                terms.add(term)
        expr.terms = terms
        return expr

    problem.objective = expression('objective', 0, (-3, -2, -4, -1))
    atoms = set()
    for identifier, coefficients in (
        ('conflict_AB', (1, 1, 0, 0)),
        ('conflict_BC', (0, 1, 1, 0)),
        ('conflict_CD', (0, 0, 1, 1)),
    ):
        atom = make(LinearConstraint, identifier, comparison='LE')
        atom.linearExpression = expression(identifier + '_expr', -1, coefficients)
        atoms.add(atom)
    root = make(LogicalConstraint, 'all_conflicts', operator='AND')
    root.operands = atoms
    problem.root = root
    return ObjectModel(name='tiny_conference_solution', objects=set(named.values())), named


def slot_value(obj, attribute_name):
    """Read a DSL slot explicitly, avoiding confusion with object identifiers."""
    return next(s.value.value for s in obj.slots if s.attribute.name == attribute_name)


def evaluate_expression(expression, assignment):
    return slot_value(expression, 'constant') + sum(
        slot_value(term, 'coefficient') * assignment[linked(term, 'variable')[0]]
        for term in linked(expression, 'terms'))


def evaluate_constraint(constraint, assignment):
    if constraint.classifier.name == 'LinearConstraint':
        value = evaluate_expression(linked(constraint, 'linearExpression')[0], assignment)
        return value == 0 if slot_value(constraint, 'comparison') == 'EQ' else value <= 0
    operands = [evaluate_constraint(child, assignment)
                for child in linked(constraint, 'operands')]
    return all(operands) if slot_value(constraint, 'operator') == 'AND' else any(operands)


class TestSolutionDSL(unittest.TestCase):
    def setUp(self):
        self.om, self.objects = build_solution_example()

    def assert_structurally_valid(self):
        result = self.om.validate(raise_exception=False)
        self.assertTrue(result['success'], '\n'.join(result['errors']))

    def invariant_results(self):
        results = check_solution_model(self.om)
        # An evaluator failure (holds=None) must never count as detection of bad input.
        unevaluated = [f'{r.constraint}: {r.detail}' for r in results if r.holds is None]
        self.assertEqual(unevaluated, [], 'Could not evaluate invariants:\n' + '\n'.join(unevaluated))
        return {r.constraint: r.holds for r in results}

    def assert_failed_invariants(self, expected):
        results = self.invariant_results()
        self.assertEqual({name for name, holds in results.items() if holds is False}, set(expected))

    def test_valid_instance(self):
        self.assert_structurally_valid()
        self.assert_failed_invariants(set())

    def test_example_optimum_matches_problem(self):
        # Evaluate the actual model expressions, not a separately hard-coded ILP.
        self.assert_structurally_valid()
        self.assert_failed_invariants(set())
        variables = [self.objects['y_' + letter] for letter in 'ABCD']
        feasible = []
        for bits in product((0, 1), repeat=4):
            assignment = dict(zip(variables, bits))
            if evaluate_constraint(self.objects['all_conflicts'], assignment):
                feasible.append((evaluate_expression(self.objects['objective'], assignment), bits))
        self.assertEqual(min(feasible), (-7, (1, 0, 1, 0)))
        self.assertEqual(sum(value == -7 for value, _ in feasible), 1)

    def test_zero_bit_width(self):
        self.objects['y_A'].bitWidth = 0
        self.assert_structurally_valid()  # type/multiplicities pass; invariant must fail
        self.assert_failed_invariants({'positiveBitWidth'})

    def test_negative_bit_width(self):
        self.objects['y_A'].bitWidth = -1
        self.assert_failed_invariants({'positiveBitWidth'})

    def test_constraint_has_two_owners(self):
        # An atom is both a parent's operand and a problem's root.
        self.objects['problem'].root = self.objects['conflict_AB']
        self.assert_failed_invariants({'constraintOwner'})

    def test_expression_has_two_owners(self):
        # Use the objective as an atom expression too. Remove the displaced
        # expression and its terms so no unrelated orphan errors are introduced.
        old_expr = self.objects['conflict_AB_expr']
        old_terms = linked(old_expr, 'terms')
        self.objects['conflict_AB'].linearExpression = self.objects['objective']
        old_expr.terms = set()
        for term in old_terms:
            term.variable = set()
            self.om.objects.remove(term)
        self.om.objects.remove(old_expr)
        self.assert_failed_invariants({'expressionOwner'})

    def test_orphan_constraint(self):
        orphan = ObjectBuilder(LogicalConstraint).name('orphan').attributes(operator='AND').build()
        self.om.add_object(orphan)
        self.assert_failed_invariants({'constraintOwner'})

    def test_cycle(self):
        root = self.objects['all_conflicts']
        root.operands = set(linked(root, 'operands')) | {root}
        self.assert_failed_invariants({'acyclicConstraints', 'constraintOwner'})

    def test_foreign_variable(self):
        # Both problems are structurally valid: the error is cross-problem scope.
        foreign = ObjectBuilder(IntegerVariable).name('foreign_y').attributes(
            name='foreign_y', bitWidth=1).build()
        other = ObjectBuilder(ILPProblem).name('other_problem').attributes(name='Other').build()
        objective = ObjectBuilder(LinearExpression).name('other_objective').attributes(constant=0).build()
        other.variables = {foreign}
        other.objective = objective
        for obj in (foreign, other, objective):
            self.om.add_object(obj)
        self.objects['objective_term_A'].variable = foreign
        self.assert_structurally_valid()
        self.assert_failed_invariants({'variablesWithinProblem'})

    def test_duplicate_variable_names(self):
        self.objects['y_B'].name = 'y_A'
        self.assert_failed_invariants({'uniqueVariableNames'})

    def test_missing_required_objective_is_structural_error(self):
        self.objects['problem'].objective = set()
        result = self.om.validate(raise_exception=False)
        self.assertFalse(result['success'])
        # No call to assert_failed_invariants: missing links are structural errors.


if __name__ == '__main__':
    unittest.main()
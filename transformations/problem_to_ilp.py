"""T1: transform one activity plan into a validated, bounded ILP model."""

from itertools import combinations

from besser.BUML.metamodel.object import ObjectModel
from besser.BUML.metamodel.object.builder import ObjectBuilder

from metamodels.problem_checks import check_model, linked, objects_of
from metamodels.problem_dsl import BOCL_UNSUPPORTED, problem_dsl
from metamodels.solution_checks import check_solution_model
from metamodels.solution_dsl import (
    ILPProblem, IntegerVariable, LinearConstraint, LinearExpression, LinearTerm,
    LogicalConstraint,
)


def transform(problem_model):
    """Return (ILP ObjectModel, ordered dict[activity object, variable object]).

    Accept exactly one ActivityPlan. Activities are sorted by their DSL name
    (case-sensitive); mapping position i identifies y_i for downstream decoding.
    Association sets must never be used to infer variable order.
    """
    failures = [r for r in check_model(problem_dsl, problem_model, BOCL_UNSUPPORTED)
                if r.holds is not True]
    if failures:
        raise ValueError("Invalid Problem DSL model: " + "; ".join(
            f"{r.constraint} ({r.engine}, holds={r.holds}): {r.detail}" for r in failures))
    plans = objects_of(problem_model, "ActivityPlan")
    if len(plans) != 1:
        raise ValueError(f"T1 requires exactly one ActivityPlan; found {len(plans)}")
    plan = plans[0]
    activities = sorted(linked(plan, "activities"), key=lambda a: a.name)
    objects = set()

    def make(classifier, identifier, **attributes):
        obj = ObjectBuilder(classifier).name(identifier).attributes(**attributes).build()
        objects.add(obj)
        return obj

    problem = make(ILPProblem, "problem", name=plan.name + "_ILP")
    # Annex A, class C (pp. 12-13), D3 (p. 14): one unsigned bit per activity.
    mapping = {activity: make(IntegerVariable, f"y_{i}", name=f"y_{i}", bitWidth=1)
               for i, activity in enumerate(activities)}
    variables = list(mapping.values())
    problem.variables = set(variables)

    def expression(identifier, constant, coefficients):
        expr = make(LinearExpression, identifier, constant=constant)
        terms = set()
        for i, coefficient in coefficients:
            term = make(LinearTerm, f"{identifier}_term_{i}", coefficient=coefficient)
            term.variable = variables[i]
            terms.add(term)
        expr.terms = terms
        return expr

    # Annex A, class D/D3 (pp. 13-14): maximise value by minimising its negative.
    problem.objective = expression("objective", 0,
                                   [(i, -a.value) for i, a in enumerate(activities)])
    indices = {a: i for i, a in enumerate(activities)}
    pairs = {tuple(sorted((indices[linked(c, "left")[0]], indices[linked(c, "right")[0]])))
             for c in linked(plan, "conflicts")}
    resources = [set(linked(a, "uses")) for a in activities]
    # Event-domain rule (docs/part1/concepts.md): half-open overlap AND shared resource.
    for i, j in combinations(range(len(activities)), 2):
        a, b = activities[i], activities[j]
        if a.start < b.end and b.start < a.end and resources[i] & resources[j]:
            pairs.add((i, j))

    atoms = []

    def atom(identifier, comparison, constant, coefficients):
        constraint = make(LinearConstraint, identifier, comparison=comparison)
        constraint.linearExpression = expression(identifier + "_expr", constant, coefficients)
        atoms.append(constraint)

    # Annex A, D3 (p. 14): each unordered conflict yields y_i + y_j - 1 <= 0.
    for i, j in sorted(pairs):
        atom(f"conflict_{i}_{j}", "LE", -1, [(i, 1), (j, 1)])
    # Annex A, class C (pp. 12-13): mandatory selection is the atom 1 - y_i = 0.
    for i, activity in enumerate(activities):
        if activity.mandatory:
            atom(f"mandatory_{i}", "EQ", 1, [(i, -1)])
    # Annex A, class C (pp. 12-13): conjunction; the DSL needs no wrapper for one atom.
    if len(atoms) == 1:
        problem.root = atoms[0]
    elif len(atoms) > 1:
        root = make(LogicalConstraint, "all_constraints", operator="AND")
        root.operands = set(atoms)
        problem.root = root

    result = ObjectModel(name=problem_model.name + "_ILP", objects=objects)
    failures = [r for r in check_solution_model(result) if r.holds is not True]
    if failures:
        raise RuntimeError("Invalid generated ILP model: " + "; ".join(
            f"{r.constraint} ({r.engine}, holds={r.holds}): {r.detail}" for r in failures))
    return result, mapping

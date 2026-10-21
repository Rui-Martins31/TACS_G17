"""Python equivalents for the Solution DSL's collection/closure invariants."""
from metamodels.checks import check_model, linked, objects_of
from metamodels.solution_dsl import BOCL_UNSUPPORTED, solution_dsl


def constraints(om):
    return [o for o in om.objects if o.classifier.name in {
        "ConstraintExpression", "LinearConstraint", "LogicalConstraint"}]


def ancestors(constraint):
    """Follow parents safely even when validating a cyclic, malformed model."""
    seen = set()
    pending = linked(constraint, "parent")
    while pending:
        parent = pending.pop()
        if parent not in seen:
            seen.add(parent)
            pending.extend(linked(parent, "parent"))
    return seen


def unique_variable_names(om):
    for problem in objects_of(om, "ILPProblem"):
        names = [v.name for v in linked(problem, "variables")]
        if len(names) != len(set(names)):
            return False
    return True


def concrete_constraints(om):
    return not objects_of(om, "ConstraintExpression")


def constraint_owner(om):
    return all(len(linked(c, "rootProblem")) + len(linked(c, "parent")) == 1
               for c in constraints(om))


def acyclic_constraints(om):
    return all(c not in ancestors(c) for c in constraints(om))


def variables_within_problem(om):
    for expression in objects_of(om, "LinearExpression"):
        owners = set(linked(expression, "objectiveProblem"))
        for atom in linked(expression, "atom"):
            for constraint in {atom} | ancestors(atom):
                owners.update(linked(constraint, "rootProblem"))
        if len(owners) != 1:
            return False
        variables = set(linked(next(iter(owners)), "variables"))
        for term in linked(expression, "terms"):
            references = linked(term, "variable")
            if len(references) != 1 or references[0] not in variables:
                return False
    return True


PYTHON_EQUIVALENTS = {
    "uniqueVariableNames": unique_variable_names,
    "concreteConstraints": concrete_constraints,
    "constraintOwner": constraint_owner,
    "acyclicConstraints": acyclic_constraints,
    "variablesWithinProblem": variables_within_problem,
}


def check_solution_model(object_model):
    return check_model(solution_dsl, object_model, BOCL_UNSUPPORTED, PYTHON_EQUIVALENTS)

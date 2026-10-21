from dataclasses import dataclass

from bocl.OCLWrapper import OCLWrapper


@dataclass
class CheckResult:
    constraint: str
    holds: bool | None  # None when the check could not be evaluated
    engine: str         # "BESSER", "B-OCL" or "Python"
    detail: str = ""


def linked(obj, end_name):
    """Objects reachable from obj through the association end end_name."""
    return [le.object for le in obj.link_ends() if le.name == end_name]


def objects_of(object_model, class_name):
    return [o for o in object_model.objects if o.classifier.name == class_name]


def _all_unique(values):
    return len(values) == len(set(values))


# --- Python equivalents of the constraints B-OCL cannot evaluate -------------

def _unique_activity_names(om):
    return all(_all_unique([a.name for a in linked(p, "activities")])
               for p in objects_of(om, "ActivityPlan"))


def _unique_resource_names(om):
    return all(_all_unique([r.name for r in linked(p, "resources")])
               for p in objects_of(om, "ActivityPlan"))


def _no_duplicate_conflicts(om):
    for plan in objects_of(om, "ActivityPlan"):
        pairs = []
        for conflict in linked(plan, "conflicts"):
            left, right = linked(conflict, "left"), linked(conflict, "right")
            if len(left) != 1 or len(right) != 1:
                return False
            pairs.append(frozenset((id(left[0]), id(right[0]))))
        if not _all_unique(pairs):
            return False
    return True


def _conflict_within_plan(om):
    for conflict in objects_of(om, "Conflict"):
        plans = linked(conflict, "conflictPlan")
        left, right = linked(conflict, "left"), linked(conflict, "right")
        if len(plans) != 1 or len(left) != 1 or len(right) != 1:
            return False
        plan_activities = linked(plans[0], "activities")
        ends = left + right
        if not all(any(e is a for a in plan_activities) for e in ends):
            return False
    return True


def _resources_within_plan(om):
    for activity in objects_of(om, "Activity"):
        plans = linked(activity, "plan")
        if len(plans) != 1:
            return False
        plan_resources = linked(plans[0], "resources")
        if not all(any(r is pr for pr in plan_resources) for r in linked(activity, "uses")):
            return False
    return True


PYTHON_EQUIVALENTS = {
    "uniqueActivityNames": _unique_activity_names,
    "uniqueResourceNames": _unique_resource_names,
    "noDuplicateConflicts": _no_duplicate_conflicts,
    "conflictWithinPlan": _conflict_within_plan,
    "resourcesWithinPlan": _resources_within_plan,
}


def check_model(domain_model, object_model, bocl_unsupported, python_equivalents=None):
    """Validate structure first; evaluate domain constraints only for a valid structure."""
    validation = object_model.validate(raise_exception=False)
    if not validation["success"]:
        return [CheckResult("structure", False, "BESSER", error)
                for error in validation["errors"]]
    wrapper = OCLWrapper(domain_model, object_model)
    equivalents = PYTHON_EQUIVALENTS if python_equivalents is None else python_equivalents
    results = []
    for constraint in sorted(domain_model.constraints, key=lambda c: c.name):
        if constraint.name in bocl_unsupported:
            results.append(CheckResult(constraint.name,
                                       equivalents[constraint.name](object_model),
                                       "Python"))
            continue
        try:
            results.append(CheckResult(constraint.name, bool(wrapper.evaluate(constraint)), "B-OCL"))
        except Exception as error:  # B-OCL raises plain Exceptions for unsupported constructs
            results.append(CheckResult(constraint.name, None, "B-OCL", str(error)))
    return results

import sys

from besser.BUML.metamodel.object.builder import ObjectBuilder

from metamodels.problem_checks import PYTHON_EQUIVALENTS, check_model
from metamodels.problem_dsl import (
    BOCL_UNSUPPORTED, Activity, ActivityPlan, Conflict, Resource, problem_dsl,
)
from models.examples.tiny_conference import build


def find(object_model, object_name):
    return next(o for o in object_model.objects if o.name_ == object_name)


def add_conflict(om, name, left, right, plan_name="plan"):
    conflict = (ObjectBuilder(Conflict).name(name).attributes(reason="test")
                .link(find(om, left) if isinstance(left, str) else left, "left")
                .link(find(om, right) if isinstance(right, str) else right, "right")
                .link(find(om, plan_name), "conflictPlan").build())
    om.add_object(conflict)


def add_second_plan(om):
    """A second plan with its own activity X and resource Hall, to test cross-plan references."""
    hall = ObjectBuilder(Resource).name("hall").attributes(name="Hall", kind="ROOM").build()
    x = ObjectBuilder(Activity).name("x").attributes(
        name="X", value=5, start=0, end=30, mandatory=False).build()
    other = (ObjectBuilder(ActivityPlan).name("other").attributes(name="OtherPlan")
             .link(x, "activities").link(hall, "resources").build())
    for obj in (other, x, hall):
        om.add_object(obj)
    return x, hall


def zero_value(om):
    find(om, "a").value = 0


def end_before_start(om):
    find(om, "b").end = 20


def self_conflict(om):
    add_conflict(om, "c_c", "c", "c")


def duplicate_activity_name(om):
    find(om, "d").name = "A"


def duplicate_resource_name(om):
    find(om, "room2").name = "Room1"


def duplicate_conflict_reversed(om):
    add_conflict(om, "d_c", "d", "c")


def conflict_with_other_plan(om):
    x, _ = add_second_plan(om)
    add_conflict(om, "c_x", "c", x)


def resource_from_other_plan(om):
    _, hall = add_second_plan(om)
    find(om, "d").uses = hall


BROKEN_VARIANTS = [
    (zero_value, "positiveValue"),
    (end_before_start, "validInterval"),
    (self_conflict, "distinctEnds"),
    (duplicate_activity_name, "uniqueActivityNames"),
    (duplicate_resource_name, "uniqueResourceNames"),
    (duplicate_conflict_reversed, "noDuplicateConflicts"),
    (conflict_with_other_plan, "conflictWithinPlan"),
    (resource_from_other_plan, "resourcesWithinPlan"),
]


def malformed_model(end, count):
    """Build invalid links directly, avoiding stale reverse links from reassignment."""
    om = build()
    add_second_plan(om)
    if end == "plan":
        obj = ObjectBuilder(Activity).name("malformed").attributes(
            name="Malformed", value=1, start=0, end=1, mandatory=False).build()
        obj.plan = set() if count == 0 else {find(om, "plan"), find(om, "other")}
    else:
        obj = ObjectBuilder(Conflict).name("malformed").attributes(reason="test").build()
        targets = {
            "left": [find(om, "a"), find(om, "b")],
            "right": [find(om, "c"), find(om, "d")],
            "conflictPlan": [find(om, "plan"), find(om, "other")],
        }
        for role, objects in targets.items():
            setattr(obj, role, set(objects[:count if role == end else 1]))
    om.add_object(obj)
    return om


def run():
    failures = []

    results = check_model(problem_dsl, build(), BOCL_UNSUPPORTED)
    print("Valid model: tiny_conference")
    for r in results:
        print(f"  {'OK  ' if r.holds else 'FAIL'} {r.constraint:<22} [{r.engine}] {r.detail}")
        if r.holds is not True:
            failures.append(f"valid model violates {r.constraint}")

    print("\nBroken variants (each must fail exactly its target constraint)")
    for mutate, target in BROKEN_VARIANTS:
        om = build()
        mutate(om)
        results = check_model(problem_dsl, om, BOCL_UNSUPPORTED)
        failed = sorted(r.constraint for r in results if r.holds is not True)
        ok = failed == [target]
        print(f"  {'OK  ' if ok else 'FAIL'} {mutate.__name__:<28} -> failed: {', '.join(failed) or 'none'}")
        if not ok:
            failures.append(f"{mutate.__name__}: expected only {target} to fail, got {failed}")

    print("\nMalformed models (structural failure, no exception)")
    for end in ("left", "right", "conflictPlan", "plan"):
        for count in (0, 2):
            om = malformed_model(end, count)
            results = check_model(problem_dsl, om, BOCL_UNSUPPORTED)
            ok = bool(results) and all(
                r.constraint == "structure" and r.engine == "BESSER" and r.holds is False
                for r in results)
            ok = ok and any(f"association end '{end}'" in r.detail for r in results)
            # Check helpers directly too, since structural validation normally skips them.
            targets = ["resourcesWithinPlan"] if end == "plan" else ["conflictWithinPlan"]
            if end in {"left", "right"}:
                targets.append("noDuplicateConflicts")
            helper_results = [PYTHON_EQUIVALENTS[target](om) for target in targets]
            ok = ok and all(result is False for result in helper_results)
            print(f"  {'OK  ' if ok else 'FAIL'} {end} with {count} links")
            if not ok:
                failures.append(f"{end} with {count} links: {results}; helpers: {helper_results}")

    print()
    if failures:
        print("FAILURES:\n  " + "\n  ".join(failures))
        return 1
    print(f"All checks passed ({len(BROKEN_VARIANTS)} broken variants and 8 malformed models detected).")
    return 0


if __name__ == "__main__":
    sys.exit(run())

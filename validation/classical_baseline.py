from dataclasses import dataclass
from itertools import combinations, product

from metamodels.problem_checks import linked, objects_of


@dataclass(frozen=True)
class BaselineResult:
    activities: tuple[str, ...]          # activity names, sorted (fixed variable order)
    conflict_pairs: frozenset             # frozensets of two activity names
    feasible_count: int
    optimum_value: int | None             # None when no feasible selection exists
    optimal_selections: tuple[frozenset, ...]

    @property
    def n(self):
        return len(self.activities)

    @property
    def m(self):
        return len(self.conflict_pairs)


def overlaps(a, b):
    return a.start < b.end and b.start < a.end


def conflict_pairs(object_model):
    """Unordered activity-name pairs that cannot be selected together (explicit + derived)."""
    pairs = set()
    for conflict in objects_of(object_model, "Conflict"):
        (left,), (right,) = linked(conflict, "left"), linked(conflict, "right")
        pairs.add(frozenset((left.name, right.name)))
    for a, b in combinations(objects_of(object_model, "Activity"), 2):
        shared = {id(r) for r in linked(a, "uses")} & {id(r) for r in linked(b, "uses")}
        if shared and overlaps(a, b):
            pairs.add(frozenset((a.name, b.name)))
    return frozenset(pairs)


def solve(object_model):
    activities = sorted(objects_of(object_model, "Activity"), key=lambda a: a.name)
    names = tuple(a.name for a in activities)
    values = {a.name: a.value for a in activities}
    mandatory = {a.name for a in activities if a.mandatory}
    pairs = conflict_pairs(object_model)

    feasible, best, optima = 0, None, []
    for bits in product((0, 1), repeat=len(names)):
        chosen = frozenset(n for n, b in zip(names, bits) if b)
        if not mandatory <= chosen or any(p <= chosen for p in pairs):
            continue
        feasible += 1
        value = sum(values[n] for n in chosen)
        if best is None or value > best:
            best, optima = value, [chosen]
        elif value == best:
            optima.append(chosen)
    return BaselineResult(names, pairs, feasible, best,
                          tuple(sorted(optima, key=lambda s: sorted(s))))


def main():
    from models.instances import INSTANCES

    header = f"{'instance':<16}{'n':>3}{'m':>4}{'feasible':>10}{'optimum':>9}{'#opt':>6}  optimal selections"
    print(header)
    print("-" * len(header))
    for inst in INSTANCES:
        om = inst.build()
        r = solve(om)
        optima = " | ".join("{" + ", ".join(sorted(s)) + "}" for s in r.optimal_selections) or "none (infeasible)"
        opt = "-" if r.optimum_value is None else r.optimum_value
        print(f"{inst.name:<16}{r.n:>3}{r.m:>4}{r.feasible_count:>10}{opt:>9}"
              f"{len(r.optimal_selections):>6}  {optima}")


if __name__ == "__main__":
    main()

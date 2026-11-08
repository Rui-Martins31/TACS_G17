from dataclasses import dataclass
from typing import Callable

from models.instances import (
    infeasible_retreat, large_open_day, medium_festival, multi_optima_sports, tiny_conference,
)


@dataclass(frozen=True)
class Instance:
    name: str
    kind: str
    build: Callable
    expected_value: int | None                 # None = infeasible
    expected_optima: tuple[frozenset, ...]     # every optimal selection, by activity name


INSTANCES = (
    Instance("tiny", "path graph, hand-checkable", tiny_conference.build, 7,
             (frozenset({"A", "C"}),)),
    Instance("medium", "mixed resources, mandatory", medium_festival.build, 19,
             (frozenset({"Opening", "Folk", "Rock", "Headliner"}),)),
    Instance("large", "~20 qubits, 9 activities", large_open_day.build, 12,
             (frozenset({"Welcome", "QuantumTalk", "GameJam", "StudentFair", "Closing"}),)),
    Instance("multi_optima", "4 optimal selections", multi_optima_sports.build, 6,
             tuple(frozenset({t, c, "Stretching"})
                   for t in ("Tennis1", "Tennis2") for c in ("Padel", "Basketball"))),
    Instance("infeasible", "conflicting mandatory", infeasible_retreat.build, None, ()),
)

BY_NAME = {i.name: i for i in INSTANCES}

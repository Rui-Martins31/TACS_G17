"""Tiny instance: the smallest end-to-end case, checkable by hand.

A short workshop in one room (times in minutes from 9:00).
Qubits at the GAS peak: 8 (python -m validation.qubit_count).

    act  value  time       uses
    A    2      [0, 60)    Room
    B    1      [30, 90)   Room
    C    1      [90, 120)  Room

Conflicts (1):
    A-B  derived: Room, overlap [30, 60)
    (B and C share the Room but are back-to-back: no conflict.)

Feasible selections: 6 of 8. Optimum: {A, C}, total value 3 (unique).
"""

from models.instances._plan import PlanBuilder


def build():
    p = PlanBuilder("TinyWorkshop")
    p.resource("Room", "ROOM")
    p.activity("A", 2, 0, 60, ["Room"])
    p.activity("B", 1, 30, 90, ["Room"])
    p.activity("C", 1, 90, 120, ["Room"])
    return p.build("tiny_workshop")

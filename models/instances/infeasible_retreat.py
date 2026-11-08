"""Infeasible instance: a company retreat where two mandatory sessions need the CEO at once.

Times in minutes from 9:00. The model is valid (all OCL constraints hold): the Problem DSL
deliberately allows conflicting mandatory activities so that "no solution" can be expressed.

    act        value  time        uses
    Keynote    5      [0, 60)     Auditorium, CEO   (mandatory)
    Board      4      [30, 90)    MeetingRoom, CEO  (mandatory)
    Workshop   3      [60, 120)   Auditorium
    Lunch      2      [120, 180)  (none)

Conflicts: Keynote-Board, derived (CEO, overlap [30, 60)). Keynote-Workshop share the
Auditorium but are back-to-back.

Every selection must contain both Keynote and Board, which conflict: no feasible selection.
GAS should find no state satisfying the constraints and the demo must report that.
"""

from models.instances._plan import PlanBuilder


def build():
    p = PlanBuilder("CompanyRetreat")
    p.resource("Auditorium", "ROOM")
    p.resource("MeetingRoom", "ROOM")
    p.resource("CEO", "PERSON")

    p.activity("Keynote", 5, 0, 60, ["Auditorium", "CEO"], mandatory=True)
    p.activity("Board", 4, 30, 90, ["MeetingRoom", "CEO"], mandatory=True)
    p.activity("Workshop", 3, 60, 120, ["Auditorium"])
    p.activity("Lunch", 2, 120, 180)
    return p.build("infeasible_retreat")

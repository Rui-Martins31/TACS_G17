"""Instance with several optimal solutions: a sports club Saturday morning.

Times in minutes from 9:00. Kind: symmetric values, conflict graph = two disjoint edges plus
an isolated activity, no explicit conflicts.

    act          value  time        uses
    Tennis1      3      [0, 60)     Court1
    Tennis2      3      [0, 60)     Court1
    Padel        2      [60, 120)   Court1, Coach
    Basketball   2      [60, 120)   Court2, Coach
    Stretching   1      [120, 150)  Court2

Conflicts (2, both derived):
    Tennis1-Tennis2     Court1, same slot
    Padel-Basketball    Coach, same slot

Pick one of each pair, plus Stretching: value 3 + 2 + 1 = 6, with 2 x 2 = 4 optimal
selections. Tests that GAS returns *an* optimum and validation accepts any of the four.
"""

from models.instances._plan import PlanBuilder


def build():
    p = PlanBuilder("SportsSaturday")
    p.resource("Court1", "ROOM")
    p.resource("Court2", "ROOM")
    p.resource("Coach", "PERSON")

    p.activity("Tennis1", 3, 0, 60, ["Court1"])
    p.activity("Tennis2", 3, 0, 60, ["Court1"])
    p.activity("Padel", 2, 60, 120, ["Court1", "Coach"])
    p.activity("Basketball", 2, 60, 120, ["Court2", "Coach"])
    p.activity("Stretching", 1, 120, 150, ["Court2"])
    return p.build("multi_optima_sports")

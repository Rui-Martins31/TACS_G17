"""Tiny example problem model, checkable by hand.

A one-morning workshop with four talks (times in minutes from 9:00):

    talk  value  time       uses
    A     3      [0, 60)    Room1
    B     2      [30, 90)   Room1
    C     4      [60, 120)  Room1, Ana
    D     1      [100, 130) Room2

Conflicts:
    A-B  derived: overlap in [30, 60) and both use Room1
    B-C  derived: overlap in [60, 90) and both use Room1
    C-D  explicit: same target audience
    (A and C share Room1 but do not overlap: A ends when C starts.)

Conflict graph is the path A-B-C-D. Optimum: {A, C}, total value 7 (unique).
"""

from besser.BUML.metamodel.object import ObjectModel
from besser.BUML.metamodel.object.builder import ObjectBuilder

from metamodels.problem_dsl import Activity, ActivityPlan, Conflict, Resource


def build():
    room1 = ObjectBuilder(Resource).name("room1").attributes(name="Room1", kind="ROOM").build()
    room2 = ObjectBuilder(Resource).name("room2").attributes(name="Room2", kind="ROOM").build()
    ana   = ObjectBuilder(Resource).name("ana").attributes(name="Ana", kind="PERSON").build()

    def talk(name, value, start, end, uses):
        activity = ObjectBuilder(Activity).name(name.lower()).attributes(
            name=name, value=value, start=start, end=end, mandatory=False).build()
        activity.uses = uses
        return activity

    a = talk("A", 3, 0, 60, {room1})
    b = talk("B", 2, 30, 90, {room1})
    c = talk("C", 4, 60, 120, {room1, ana})
    d = talk("D", 1, 100, 130, {room2})

    c_d  = (ObjectBuilder(Conflict)
                .name("c_d")
                .attributes(reason="same target audience")
                .link(c, "left")
                .link(d, "right")
                .build())

    plan = ObjectBuilder(ActivityPlan).name("plan").attributes(name="TinyWorkshop").build()
    plan.activities = {a, b, c, d}
    plan.resources  = {room1, room2, ana}
    plan.conflicts  = {c_d}

    return ObjectModel(name="tiny_conference",
                       objects={plan, a, b, c, d, room1, room2, ana, c_d})


tiny_conference = build()

"""Medium instance: a festival afternoon with stages, a shared sound engineer and one drum kit.

Times in minutes from 14:00. Kind: mixed resource kinds (ROOM, PERSON, EQUIPMENT), one
mandatory activity, one explicit conflict between activities that do not overlap.

    act        value  time        uses
    Opening    2      [0, 45)     MainStage
    Jazz       5      [30, 90)    MainStage, DrumKit
    Folk       3      [0, 60)     SideStage, Rita
    Rock       6      [60, 120)   SideStage, DrumKit, Rita
    Poetry     2      [90, 120)   MainStage
    DJ         4      [100, 160)  MainStage, Rita
    Headliner  8      [120, 180)  SideStage, DrumKit, Rita   (mandatory)

Conflicts (6):
    Opening-Jazz     derived: MainStage, overlap [30, 45)
    Jazz-Rock        derived: DrumKit, overlap [60, 90)
    Poetry-DJ        derived: MainStage, overlap [100, 120)
    Rock-DJ          derived: Rita, overlap [100, 120)
    DJ-Headliner     derived: Rita, overlap [120, 160)
    Folk-Poetry      explicit: same target audience (they do not overlap)
    Folk-Rock and Rock-Headliner share resources but are back-to-back: no conflict.

Headliner is mandatory, so DJ is excluded. Remaining choice: Jazz (5) or Opening + Rock (8);
Folk (3) beats Poetry (2). Optimum: {Opening, Folk, Rock, Headliner}, value 19 (unique).
"""

from models.instances._plan import PlanBuilder


def build():
    p = PlanBuilder("SummerFestival")
    p.resource("MainStage", "ROOM")
    p.resource("SideStage", "ROOM")
    p.resource("Rita", "PERSON")
    p.resource("DrumKit", "EQUIPMENT")

    p.activity("Opening", 2, 0, 45, ["MainStage"])
    p.activity("Jazz", 5, 30, 90, ["MainStage", "DrumKit"])
    p.activity("Folk", 3, 0, 60, ["SideStage", "Rita"])
    p.activity("Rock", 6, 60, 120, ["SideStage", "DrumKit", "Rita"])
    p.activity("Poetry", 2, 90, 120, ["MainStage"])
    p.activity("DJ", 4, 100, 160, ["MainStage", "Rita"])
    p.activity("Headliner", 8, 120, 180, ["SideStage", "DrumKit", "Rita"], mandatory=True)

    p.conflict("Folk", "Poetry", "same target audience")
    return p.build("medium_festival")

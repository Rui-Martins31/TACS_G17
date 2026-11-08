"""Large instance: a university open day (9 activities, intended as the ~20-qubit case).

Times in minutes from 10:00. Kind: 9 activities (512 candidate selections), an activity with no
resources, a mandatory activity, explicit conflicts both with and without a time overlap.

    act           value  time        uses
    Welcome       1      [0, 30)     Aula1
    RoboticsDemo  3      [0, 60)     Lab, ProfSilva
    QuantumTalk   5      [30, 90)    Aula1, ProfSilva
    VRTour        2      [60, 120)   Lab, VRHeadset
    AIPanel       1      [60, 120)   Aula2, ProfSilva
    GameJam       3      [90, 150)   Lab, VRHeadset
    StudentFair   2      [120, 180)  Aula2
    CampusWalk    1      [120, 180)  (none)
    Closing       1      [150, 180)  Aula1             (mandatory)

Conflicts (5):
    RoboticsDemo-QuantumTalk  derived: ProfSilva, overlap [30, 60)
    QuantumTalk-AIPanel       derived: ProfSilva, overlap [60, 90)
    VRTour-GameJam            derived: Lab + VRHeadset, overlap [90, 120)
    StudentFair-CampusWalk    explicit: same student guides
    CampusWalk-Closing        explicit: guides needed at closing
    Back-to-back, no conflict: Welcome-QuantumTalk (Aula1), AIPanel-StudentFair (Aula2),
    RoboticsDemo-VRTour (Lab).

Closing is mandatory, so CampusWalk is out; StudentFair (2) is then free. QuantumTalk (5) beats
RoboticsDemo + AIPanel (4); GameJam (3) beats VRTour (2); Welcome is free.
Optimum: {Welcome, QuantumTalk, GameJam, StudentFair, Closing}, value 12 (unique).
"""

from models.instances._plan import PlanBuilder


def build():
    p = PlanBuilder("UniversityOpenDay")
    p.resource("Aula1", "ROOM")
    p.resource("Aula2", "ROOM")
    p.resource("Lab", "ROOM")
    p.resource("ProfSilva", "PERSON")
    p.resource("VRHeadset", "EQUIPMENT")

    p.activity("Welcome", 1, 0, 30, ["Aula1"])
    p.activity("RoboticsDemo", 3, 0, 60, ["Lab", "ProfSilva"])
    p.activity("QuantumTalk", 5, 30, 90, ["Aula1", "ProfSilva"])
    p.activity("VRTour", 2, 60, 120, ["Lab", "VRHeadset"])
    p.activity("AIPanel", 1, 60, 120, ["Aula2", "ProfSilva"])
    p.activity("GameJam", 3, 90, 150, ["Lab", "VRHeadset"])
    p.activity("StudentFair", 2, 120, 180, ["Aula2"])
    p.activity("CampusWalk", 1, 120, 180)
    p.activity("Closing", 1, 150, 180, ["Aula1"], mandatory=True)

    p.conflict("StudentFair", "CampusWalk", "same student guides")
    p.conflict("CampusWalk", "Closing", "guides needed at closing")
    return p.build("large_open_day")

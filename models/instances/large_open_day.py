"""Large instance: a university open day (9 activities, the ~20-qubit case of Annex A).

Times in minutes from 10:00. Kind: 9 activities (512 candidate selections), an activity with no
resources, a mandatory activity, a derived conflict and an explicit conflict without a time
overlap. Qubits at the GAS peak: 20 (python -m validation.qubit_count). Each conflict or mandatory
activity costs a 2-qubit register, so the schedule is mostly back-to-back to stay within budget.

    act           value  time        uses
    Welcome       1      [0, 30)     Aula1
    RoboticsDemo  3      [0, 60)     Lab, ProfSilva
    QuantumTalk   4      [30, 90)    Aula1, ProfSilva
    VRTour        2      [60, 120)   Lab, VRHeadset
    AIPanel       1      [90, 150)   Aula2, ProfSilva
    GameJam       2      [120, 180)  Lab, VRHeadset
    CampusWalk    1      [90, 150)   (none)
    StudentFair   1      [150, 180)  Aula2
    Closing       1      [150, 180)  Aula1             (mandatory)

Conflicts (2):
    RoboticsDemo-QuantumTalk  derived: ProfSilva, overlap [30, 60)
    CampusWalk-Closing        explicit: guides needed at closing (no time overlap)
    Back-to-back, no conflict: Welcome-QuantumTalk (Aula1), QuantumTalk-AIPanel (ProfSilva),
    RoboticsDemo-VRTour and VRTour-GameJam (Lab), AIPanel-StudentFair (Aula2).

Feasible selections: 96 of 512. Closing is mandatory, so CampusWalk is out; QuantumTalk (4)
beats RoboticsDemo (3); every other activity is free.
Optimum: all except RoboticsDemo and CampusWalk, value 12 (unique).
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
    p.activity("QuantumTalk", 4, 30, 90, ["Aula1", "ProfSilva"])
    p.activity("VRTour", 2, 60, 120, ["Lab", "VRHeadset"])
    p.activity("AIPanel", 1, 90, 150, ["Aula2", "ProfSilva"])
    p.activity("GameJam", 2, 120, 180, ["Lab", "VRHeadset"])
    p.activity("CampusWalk", 1, 90, 150)
    p.activity("StudentFair", 1, 150, 180, ["Aula2"])
    p.activity("Closing", 1, 150, 180, ["Aula1"], mandatory=True)

    p.conflict("CampusWalk", "Closing", "guides needed at closing")
    return p.build("large_open_day")

from besser.BUML.metamodel.object import ObjectModel
from besser.BUML.metamodel.object.builder import ObjectBuilder

from metamodels.problem_dsl import Activity, ActivityPlan, Conflict, Resource


def _object_name(name):
    return name.lower().replace(" ", "_").replace("-", "_")


class PlanBuilder:
    def __init__(self, plan_name):
        self.plan_name = plan_name
        self.activities, self.resources, self.conflicts = {}, {}, []

    def resource(self, name, kind):
        obj = ObjectBuilder(Resource).name(_object_name(name)).attributes(name=name, kind=kind).build()
        self.resources[name] = obj
        return obj

    def activity(self, name, value, start, end, uses=(), mandatory=False):
        obj = ObjectBuilder(Activity).name(_object_name(name)).attributes(
            name=name, value=value, start=start, end=end, mandatory=mandatory).build()
        obj.uses = {self.resources[r] for r in uses}
        self.activities[name] = obj
        return obj

    def conflict(self, left, right, reason):
        obj = (ObjectBuilder(Conflict)
               .name(f"{_object_name(left)}__{_object_name(right)}")
               .attributes(reason=reason)
               .link(self.activities[left], "left")
               .link(self.activities[right], "right")
               .build())
        self.conflicts.append(obj)
        return obj

    def build(self, model_name):
        plan = ObjectBuilder(ActivityPlan).name("plan").attributes(name=self.plan_name).build()
        plan.activities = set(self.activities.values())
        plan.resources = set(self.resources.values())
        plan.conflicts = set(self.conflicts)
        objects = {plan, *self.activities.values(), *self.resources.values(), *self.conflicts}
        return ObjectModel(name=model_name, objects=objects)

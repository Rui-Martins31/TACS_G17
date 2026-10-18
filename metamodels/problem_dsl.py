from besser.BUML.metamodel.structural import (
    BinaryAssociation, BooleanType, Class, Constraint, DomainModel, Enumeration,
    EnumerationLiteral, IntegerType, Multiplicity, Property, StringType,
)

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

ResourceKind = Enumeration(name="ResourceKind", literals={
    EnumerationLiteral(name="ROOM"),
    EnumerationLiteral(name="PERSON"),
    EnumerationLiteral(name="EQUIPMENT"),
})

# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

ActivityPlan = Class(name="ActivityPlan", attributes={
    Property(name="name", type=StringType),
})

Activity = Class(name="Activity", attributes={
    Property(name="name", type=StringType),
    Property(name="value", type=IntegerType),
    Property(name="start", type=IntegerType),
    Property(name="end", type=IntegerType),
    Property(name="mandatory", type=BooleanType),
})

Resource = Class(name="Resource", attributes={
    Property(name="name", type=StringType),
    Property(name="kind", type=ResourceKind),
})

Conflict = Class(name="Conflict", attributes={
    Property(name="reason", type=StringType),
})

# ---------------------------------------------------------------------------
# Associations
# ---------------------------------------------------------------------------

plan_activities = BinaryAssociation(name="plan_activities", ends={
    Property(name="plan", type=ActivityPlan, multiplicity=Multiplicity(1, 1), is_composite=True),
    Property(name="activities", type=Activity, multiplicity=Multiplicity(1, "*")),
})
plan_resources = BinaryAssociation(name="plan_resources", ends={
    Property(name="resourcePlan", type=ActivityPlan, multiplicity=Multiplicity(1, 1), is_composite=True),
    Property(name="resources", type=Resource, multiplicity=Multiplicity(0, "*")),
})
plan_conflicts = BinaryAssociation(name="plan_conflicts", ends={
    Property(name="conflictPlan", type=ActivityPlan, multiplicity=Multiplicity(1, 1), is_composite=True),
    Property(name="conflicts", type=Conflict, multiplicity=Multiplicity(0, "*")),
})

activity_resources = BinaryAssociation(name="activity_resources", ends={
    Property(name="uses", type=Resource, multiplicity=Multiplicity(0, "*")),
    Property(name="usedBy", type=Activity, multiplicity=Multiplicity(0, "*")),
})

conflict_left = BinaryAssociation(name="conflict_left", ends={
    Property(name="left", type=Activity, multiplicity=Multiplicity(1, 1)),
    Property(name="conflictsAsLeft", type=Conflict, multiplicity=Multiplicity(0, "*")),
})
conflict_right = BinaryAssociation(name="conflict_right", ends={
    Property(name="right", type=Activity, multiplicity=Multiplicity(1, 1)),
    Property(name="conflictsAsRight", type=Conflict, multiplicity=Multiplicity(0, "*")),
})

# ---------------------------------------------------------------------------
# OCL constraints
# ---------------------------------------------------------------------------

positive_value = Constraint(
    name="positiveValue", context=Activity, language="OCL",
    expression="context Activity inv positiveValue: self.value > 0")

valid_interval = Constraint(
    name="validInterval", context=Activity, language="OCL",
    expression="context Activity inv validInterval: self.start >= 0 and self.start < self.end")

distinct_ends = Constraint(
    name="distinctEnds", context=Conflict, language="OCL",
    expression="context Conflict inv distinctEnds: self.left.name <> self.right.name")

# Not checked by B-OCL
unique_activity_names = Constraint(
    name="uniqueActivityNames", context=ActivityPlan, language="OCL",
    expression="context ActivityPlan inv uniqueActivityNames: self.activities->isUnique(name)")

unique_resource_names = Constraint(
    name="uniqueResourceNames", context=ActivityPlan, language="OCL",
    expression="context ActivityPlan inv uniqueResourceNames: self.resources->isUnique(name)")

no_duplicate_conflicts = Constraint(
    name="noDuplicateConflicts", context=ActivityPlan, language="OCL",
    expression=(
        "context ActivityPlan inv noDuplicateConflicts: "
        "self.conflicts->forAll(c1, c2 | c1 <> c2 implies "
        "not ((c1.left = c2.left and c1.right = c2.right) or "
        "(c1.left = c2.right and c1.right = c2.left)))"))

conflict_within_plan = Constraint(
    name="conflictWithinPlan", context=Conflict, language="OCL",
    expression=(
        "context Conflict inv conflictWithinPlan: "
        "self.conflictPlan.activities->includes(self.left) and "
        "self.conflictPlan.activities->includes(self.right)"))

resources_within_plan = Constraint(
    name="resourcesWithinPlan", context=Activity, language="OCL",
    expression=(
        "context Activity inv resourcesWithinPlan: "
        "self.uses->forAll(r | self.plan.resources->includes(r))"))

BOCL_UNSUPPORTED = {
    "uniqueActivityNames",
    "uniqueResourceNames",
    "noDuplicateConflicts",
    "conflictWithinPlan",
    "resourcesWithinPlan",
}

# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------

problem_dsl = DomainModel(
    name="ActivitySelectionDSL",
    types={ActivityPlan, Activity, Resource, Conflict, ResourceKind},
    associations={plan_activities, plan_resources, plan_conflicts,
                  activity_resources, conflict_left, conflict_right},
    constraints={positive_value, valid_interval, distinct_ends,
                 unique_activity_names, unique_resource_names,
                 no_duplicate_conflicts, conflict_within_plan,
                 resources_within_plan},
)

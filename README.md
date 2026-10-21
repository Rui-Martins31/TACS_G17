# QMDE D3 — Part I: Weighted Non-Conflicting Activities

For TACS 2026/27 (FEUP M.EIC), we model the selection of non-conflicting activities
with the highest total value, a Maximum-Weight Independent Set problem. In Part I,
we define the problem DSL and a bounded integer linear programming (ILP) DSL.
In Part II, we will implement the chain from problem to ILP to quantum circuit and
Qiskit code, using Grover Adaptive Search.

We chose event programmes because each activity has a value, while conflicts limit
which activities can be included together. We keep activity times fixed so that
the problem focuses on selection. Rooms, speakers and equipment are shared resources,
and activities conflict when they overlap and need the same resource. Explicit conflicts
cover other restrictions, such as activities intended for the same audience.

The metamodel should reflect what event organisers need to describe and how they
work. We use familiar concepts such as activities, rooms and speakers to reduce
the effort of expressing an event's requirements. Our aim is to make the tool
easier to learn and use, including for organisers with no knowledge of quantum
computing, and give them a reason to adopt it in their work.

Separating the Problem DSL from the Solution DSL keeps these event concepts
independent of their mathematical formulation. Following Annex A, classes C/D,
the Solution DSL uses bounded integer variables, linear constraints and a
minimisation objective. Together, the two languages provide the basis for a
translation from the organiser's description to the quantum program, which we
will implement in Part II.

| Student number | Name              | GitHub        |
| -------------- | ----------------- | ------------- |
| 202207410      | Lucas Branquinho  | Lucasalf21    |
| 202104636      | Rui Martins       | Rui-Martins31 |
| 202207742      | Margarida Fonseca | gamicmf       |

## 1. Problem DSL

![Problem DSL metamodel with associations and OCL constraints](diagrams/problem_DSL.png)

The table summarises
the classes in the [B-UML metamodel](metamodels/problem_dsl.py) and
[diagram](diagrams/problem_DSL.png); the [full concept list](docs/part1/concepts.md#problem-dsl)
also includes the ILP mappings and references. Ownership is represented by composition.

| Concept | Attributes | Associations |
|---|---|---|
| ActivityPlan | name: str | Owns 1..* activities, 0..* resources and 0..* conflicts |
| Activity | name: str; value, start, end: int; mandatory: bool | Belongs to 1 plan; uses 0..* resources; can be either endpoint of conflicts |
| Resource | name: str; kind: ResourceKind | Belongs to 1 plan; used by 0..* activities |
| Conflict | reason: str | Belongs to 1 plan; references exactly 1 left and 1 right activity |

`ResourceKind = {ROOM, PERSON, EQUIPMENT}`. We use half-open intervals `[start, end)`
so that back-to-back activities do not overlap. Mandatory activities must be selected.
We allow conflicts between mandatory activities so that a valid
problem model can describe an instance with no feasible solution.

The OCL rules add restrictions beyond the associations. `positiveValue` requires `value > 0`; `validInterval` requires
`start >= 0 and start < end`; `distinctEnds` prevents self-conflicts.
`uniqueActivityNames` and `uniqueResourceNames` require uniqueness within a plan;
`noDuplicateConflicts` forbids repeated pairs in either order; `conflictWithinPlan`
and `resourcesWithinPlan` forbid cross-plan references.

## 2. Solution DSL

![Solution DSL metamodel with associations and OCL constraints](diagrams/solution_DSL.png)

The [B-UML metamodel](metamodels/solution_dsl.py) and [diagram](diagrams/solution_DSL.png)
describe the variables, constraints and objective of an optimisation problem.

| Concept | Attributes | Associations |
|---|---|---|
| ILPProblem | name: str | Owns 1..* variables, 1 objective expression and 0..1 root constraint |
| IntegerVariable | name: str; bitWidth: int | Belongs to 1 problem; referenced by 0..* terms |
| LinearExpression | constant: int | Owns 0..* terms; belongs to exactly 1 problem objective or linear constraint |
| LinearTerm | coefficient: int | Belongs to 1 expression; references 1 variable |
| ConstraintExpression (abstract) | None | Belongs to exactly 1 problem as root or logical constraint as operand |
| LinearConstraint | comparison: ComparisonKind | Inherits ConstraintExpression; owns 1 linear expression |
| LogicalConstraint | operator: LogicalOperator | Inherits ConstraintExpression; owns 2..* constraint operands |

`ComparisonKind = {EQ, LE}` specifies whether an expression must equal zero or be
less than or equal to zero. `LogicalOperator = {AND, OR}` specifies how constraints
are combined. A variable with `w` bits ranges
from `0` to `2^w - 1`. D3 uses one bit per activity. Expressions contain integer
coefficients and constants; the objective always means minimisation.

Following Annex A, D3, we represent each activity with a variable
`y_i`, its value contributes `-value_i * y_i` to the objective, and a conflict becomes
`y_i + y_j - 1 <= 0`. A mandatory activity adds `1 - y_i = 0`. Resources and times
identify conflicts but need no separate ILP objects. We combine these constraints
with AND and retain OR to support the wider class C/D language.

For this DSL, `positiveBitWidth` requires a positive width; `uniqueVariableNames`
requires names unique within a problem. `expressionOwner` and `constraintOwner`
require exactly one of their alternative owners. `acyclicConstraints` forbids parent
cycles; `concreteConstraints` forbids direct abstract-class instances;
`variablesWithinProblem` keeps variable references inside the enclosing problem.
A problem without a root constraint has no constraints.

## 3. Hand-built models and validation

The [problem example](models/examples/tiny_conference.py) contains four activities
A–D with values 3, 2, 4 and 1. A–B and B–C conflict because they overlap and use the
same room; C–D has an explicit conflict. We build the corresponding BESSER solution object model by hand in
`build_solution_example()` in [the Solution DSL tests](tests/test_solution_dsl.py):

```text
Minimise -3A - 2B - 4C - D, with A, B, C, D in {0,1}
Subject to A+B-1 <= 0, B+C-1 <= 0, C+D-1 <= 0
```

The test evaluates all 16 assignments and finds the unique optimum `{A, C}`,
with value 7 (objective −7). The transformation between the two models remains
Part II work.

The shared checker first calls `ObjectModel.validate()` for structural errors,
including multiplicities and enumeration values. It then evaluates invariants.
Our installed B-OCL evaluates three Problem DSL and two Solution DSL invariants.
We use Python equivalents for the five remaining rules in each language because
local B-OCL parsing or evaluation failed. These rules are marked in the
[constraint tables](docs/part1/concepts.md) and selected by `BOCL_UNSUPPORTED`.
The manual fallback declarations need to be preserved when re-exporting the metamodel.

## 4. Running the checks and references

Run these commands from the repository root. `requirements.txt` installs the course's BESSER fork:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m tests.test_problem_dsl
python -m unittest tests.test_solution_dsl -v
```

The Problem script checks a valid example and 16 invalid variants; unittest discovery
does not run it. The Solution suite has 11 tests for the example and invalid models.

The formulation follows the TACS 2026/27 Assignment, draft v0.7, Annex A, classes
C/D and problem D3. We organise the concept tables following Brambilla, Cabot and Wimmer,
*Model-Driven Software Engineering in Practice*, 2nd ed., 2017, Fig. 7.4.
The event-domain choices are our own. See [concepts.md](docs/part1/concepts.md)
for detailed mappings and [LLM_USAGE_LOG.md](LLM_USAGE_LOG.md) for AI assistance.

# Part I: Concept Lists

Format follows Fig. 7.4 of Brambilla et al., *Model-Driven Software Engineering in Practice*.
Intrinsic properties become attributes; extrinsic properties become associations.

## Problem DSL

Domain: planning an event programme (talks, workshops, sessions). Activities use shared
resources at given times; two activities conflict when they overlap in time **and** share a
resource, or when the modeller declares an explicit conflict. Metamodel:
[metamodels/problem_dsl.py](../../metamodels/problem_dsl.py).

| Concept | Intrinsic properties | Extrinsic properties | Maps to (ILP element) | Reference |
|---|---|---|---|---|
| ActivityPlan | name: str | 1..* Activities, 0..* Resources, 0..* Conflicts (composition) | the whole ILP model | Annex A, class D |
| Activity | name: str, value: int, start: int, end: int, mandatory: bool | 0..* Resources used; conflicts as left/right | 1-bit variable `y_i`; objective term `−value_i · y_i` | Annex A, class D (maximise value = minimise its negative) |
| Activity (mandatory = true) | | | atom `1 − y_i = 0` (i.e. `y_i = 1`) | Annex A, class C atom forms |
| Resource | name: str, kind: ResourceKind {ROOM, PERSON, EQUIPMENT} | used by 0..* Activities | none directly; used by T1 to derive conflicts | own design |
| Conflict (explicit) | reason: str | exactly 1 left + 1 right Activity | atom `y_i + y_j − 1 ≤ 0` | Annex A, D3 row (`x_i + x_j ≤ 1`) |
| Derived conflict (not a class; computed by T1) | | two activities sharing a resource with overlapping `[start, end)` | atom `y_i + y_j − 1 ≤ 0` (once per pair, merged with explicit ones) | Annex A, D3 row; own design |

OCL constraints (all standard OCL; B-OCL cannot evaluate the ones marked *, which are
checked by an equivalent Python function in [metamodels/checks.py](../../metamodels/checks.py)):

| Name | Context | Rule |
|---|---|---|
| positiveValue | Activity | `value > 0` |
| validInterval | Activity | `start >= 0 and start < end` |
| distinctEnds | Conflict | a conflict links two different activities |
| uniqueActivityNames * | ActivityPlan | activity names unique within the plan |
| uniqueResourceNames * | ActivityPlan | resource names unique within the plan |
| noDuplicateConflicts * | ActivityPlan | no two explicit conflicts on the same pair (in either order) |
| conflictWithinPlan * | Conflict | both activities belong to the conflict's plan |
| resourcesWithinPlan * | Activity | every resource used belongs to the activity's plan |

Design notes to discuss in the report:
- Conflicts derived from time + shared resource let the modeller describe the event naturally
  instead of listing every pair. Explicit conflicts stay, so the conflict graph is not limited to
  interval graphs (MWIS on interval graphs is solvable in polynomial time).
- Mandatory activities that conflict with each other make the instance infeasible. This is
  deliberately **not** forbidden by OCL: it is the "no solution" test instance asked for in Annex A.
- `value` is an integer because ILP coefficients in class C/D are integers (no scaling needed).

## Solution DSL (0/1 ILP)

A solution model represents a bounded integer optimisation problem: integer variables with explicit bit widths, linear constraints combined using AND/OR, and a linear objective to minimise. For our activity-selection problem, each variable uses one bit: 1 means the activity is selected, and 0 means it is omitted. Maximising the total activity value is expressed by minimising its negative. The table below defines the concepts, attributes and associations of this language.

| Concept | Intrinsic properties | Extrinsic properties | Reference |
|---|---|---|---|
| ILPProblem | name: str | owns 1..* IntegerVariables, exactly 1 LinearExpression as objective, and 0..1 ConstraintExpression as the root constraint (composition) | Annex A, class D: variables, constraints and minimisation objective |
| IntegerVariable | name: str, bitWidth: int | belongs to exactly 1 ILPProblem; referenced by 0..* LinearTerms | Annex A, class C: an unsigned variable with `w` bits ranges from `0` to `2^w - 1`; D3 uses `w = 1` |
| LinearExpression | constant: int | owns 0..* LinearTerms (composition); belongs to exactly 1 owner, either an ILPProblem as its objective or a LinearConstraint as its expression | Annex A, classes C/D: `a_0 + sum(a_i * y_i)` |
| LinearTerm | coefficient: int | belongs to exactly 1 LinearExpression; references exactly 1 IntegerVariable | Annex A, classes C/D: integer coefficient multiplied by a variable |
| ConstraintExpression (abstract) | none | belongs to exactly 1 owner, either an ILPProblem as its root constraint or a LogicalConstraint as an operand | Own structure for the constraint formulas defined in Annex A, class C |
| LinearConstraint (extends ConstraintExpression) | comparison: ComparisonKind {EQ, LE} | owns exactly 1 LinearExpression (composition); inherits constraint ownership | Annex A, class C: an atom compares a linear expression with zero using `=` or `<=` |
| LogicalConstraint (extends ConstraintExpression) | operator: LogicalOperator {AND, OR} | owns 2..* ConstraintExpressions as operands (composition); inherits constraint ownership | Annex A, class C: atoms combined with conjunction/disjunction |

`ComparisonKind` and `LogicalOperator` are enumerations. Inherited ownership is exclusive:
a constraint is either the root of a problem or a child of another constraint, never both.
The constraint structure is an acyclic tree. An absent root means there are no constraints;
a single atom needs no logical wrapper. All expressions refer only to variables declared in
the same ILPProblem. Variable names must be unique within a problem and bit widths positive.
These are rules to capture in the metamodel and OCL.

The objective always means minimisation, so no objective-direction attribute is needed.
For D3, each activity contributes a one-bit variable and a term with coefficient `-value`.
Each conflict becomes `y_i + y_j - 1 <= 0`, and each mandatory activity becomes
`1 - y_i = 0`; combine these atoms with AND. Resources and times determine which conflict
atoms are needed, but do not become separate ILP concepts. A solution model describes this
optimisation problem, not an assignment of values to its variables.

## Solver configuration

| Concept | Intrinsic properties | Extrinsic properties |
|---|---|---|
| | | |

## Test instances

| Name | Kind / story | #activities | #conflicts | Known optimum | Source |
|---|---|---|---|---|---|
| | | | | | |

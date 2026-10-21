# Part I: Concept Lists

Format follows Fig. 7.4 of Brambilla et al., *Model-Driven Software Engineering in Practice*.
Intrinsic properties become attributes; extrinsic properties become associations.

## Problem DSL

Domain: planning an event programme (talks, workshops, sessions). Activities use shared
resources at given times; two activities conflict when they overlap in time **and** share a
resource, or when the modeller declares an explicit conflict. Metamodel:
[metamodels/problem_dsl.py](../../metamodels/problem_dsl.py).

The tables distinguish **implemented** concepts from **proposed extensions**. A domain
concept need not become a separate metamodel class: it may be an attribute, enumeration,
association, or derived rule. ILP elements below are mathematical targets for T1; they do
not imply that the solution metamodel or transformations are already implemented.

### Concepts supported by the current metamodel

| Concept | Representation / intrinsic properties | Extrinsic properties / connections | Maps to (ILP element) | Reference |
|---|---|---|---|---|
| Activity plan | `ActivityPlan`; `name: str` | Owns 1..* activities, 0..* resources and 0..* explicit conflicts | One optimisation instance | Assignment §6.1; Annex A, class D |
| Activity | `Activity`; `name: str` | Belongs to exactly one plan; uses 0..* resources; participates in 0..* conflicts | One binary variable `y_i ∈ {0,1}`; 1 means selected | Annex A, D3 |
| Activity value | `Activity.value: int`, positive | Value attached to one activity | Objective coefficient `−value_i`; minimise `−Σ value_i y_i` | Annex A, class D, maximisation by negation |
| Fixed time interval | `Activity.start: int`, `end: int` | One interval per activity; all times in a plan use a common unit and origin | Input to conflict derivation; no time decision variables | Own design |
| Mandatory participation | `Activity.mandatory: bool` | Applies to one activity | If true, atom `1 − y_i = 0`; if false, no additional atom | Own design; Annex A, class C atom forms |
| Shared resource | `Resource`; `name: str`, `kind: ResourceKind` | Belongs to exactly one plan; used by 0..* activities | Supplies conflict pairs; no variable of its own | Own design |
| Resource category | Enumeration `ResourceKind`: ROOM, PERSON, EQUIPMENT | Classifies each resource | No direct ILP element | Own design |
| Room | Resource with kind ROOM; not a separate class | Activities using the same room cannot overlap | Pairwise conflict atoms for overlapping users | Own design; Annex A, D3 |
| Person | Resource with kind PERSON; not a separate class | A speaker, monitor or other person shared by activities | Pairwise conflict atoms for overlapping users | Own design; Annex A, D3 |
| Equipment item | Resource with kind EQUIPMENT; not a separate class | A specific exclusive item, such as one projector | Pairwise conflict atoms for overlapping users | Own design; Annex A, D3 |
| Resource use | Association `activity_resources`; no intrinsic properties | Many-to-many links through `uses` / `usedBy` | Used with intervals to compute conflict edges | Own design |
| Explicit incompatibility | `Conflict`; `reason: str` | Belongs to one plan; exactly one left and one right activity | Atom `y_i + y_j − 1 ≤ 0` | Annex A, D3; reason is own metadata |
| Temporal overlap | Derived predicate; not a class | Activities i and j overlap iff `start_i < end_j` and `start_j < end_i` | No atom by itself: overlap alone does not prohibit selection | Own design; half-open intervals |
| Resource-derived incompatibility | Derived relation; not a class | Overlapping activities share at least one resource | Atom `y_i + y_j − 1 ≤ 0` | Own derivation; Annex A, D3 |
| Effective conflict pair | Derived unordered pair; not a class | Union of explicit and resource-derived incompatibilities | Emit one conflict atom per unordered pair | Own T1 design; Annex A, D3 |

Times are fixed input data: T1 selects activities rather than assigning their start times.
Intervals are half-open `[start, end)`, so back-to-back activities do not overlap. Every
resource currently behaves as one exclusive item; the enumeration does not introduce
capacities or interchangeable resource pools. Explicit conflicts apply even when activities
do not overlap or share a resource. The `reason` field explains a conflict but does not
change its mathematical meaning.

### Proposed extensions (not implemented)

These are optional domain additions, not requirements stated by the assignment. Each stays
within the linear integer model of Annex A, class D. They must be reflected in the B-UML
metamodel, validation, examples and T1 before being described as supported.

| Concept | Proposed intrinsic properties | Proposed extrinsic properties / connections | Maps to (ILP element) | Reference / status |
|---|---|---|---|---|
| Activity group | `name: str` | Owned by one plan; contains 1..* activities from that plan; an activity may belong to multiple groups | Defines a set G used by group rules; no variable itself | Own extension; class D linear encoding |
| Group selection bounds | `minimumSelected: int`, `maximumSelected: int` on a group | Bounds selection among the group's member activities | `minimumSelected − Σ(i∈G)y_i ≤ 0`; `Σ(i∈G)y_i − maximumSelected ≤ 0` | Own extension; class C atom normalisation |
| Alternative activities | Special case of group bounds: minimum 0, maximum 1 | Activities offering interchangeable programme options | `Σ(i∈G)y_i − 1 ≤ 0` | Own extension; generalises D3 pairwise exclusion |
| Exactly-one choice | Special case of group bounds: minimum 1, maximum 1 | A group of alternative versions of a session | `Σ(i∈G)y_i − 1 = 0` | Own extension; class C equality |
| Prerequisite | Optional `reason: str` | Directed link from one dependent activity to one required activity in the same plan | `y_dependent − y_required ≤ 0` | Own extension; class D linear encoding |
| Joint participation | Optional `reason: str` | Links two distinct activities that must be selected together or both omitted | `y_i − y_j = 0` | Own extension; class C equality |
| Activity cost | `cost: int`, non-negative, on Activity | Cost incurred only when the activity is selected | Coefficient in a budget constraint; not an objective coefficient | Own extension; class D linear encoding |
| Programme budget | `budget: int`, non-negative, on ActivityPlan | Limits total selected activity cost | `Σ cost_i y_i − budget ≤ 0` | Own extension; Annex A, D1 knapsack pattern |
| Programme size bounds | `minimumSelected: int`, `maximumSelected: int` on ActivityPlan | Bounds the number of selected activities across the plan | `minimumSelected − Σ y_i ≤ 0`; `Σ y_i − maximumSelected ≤ 0` | Own extension; class D linear encoding |
| Selected-duration limit | `maximumTotalDuration: int`, non-negative, on ActivityPlan | Limits the sum of the durations of selected activities | `Σ (end_i − start_i)y_i − maximumTotalDuration ≤ 0` | Own extension; class D linear encoding |

The selected-duration limit counts activity-minutes, including concurrent activities
separately; it does not measure the elapsed span of the programme.

**Suggested first extension:** implement ActivityGroup with selection bounds and Prerequisite.
These add meaningful programme requirements using existing activity variables. Alternative
activities and exactly-one choice are examples of group bounds, not additional classes.
Budget and activity cost should be introduced together if the domain needs financial planning.
Keep the quantum algorithm, shots, registers and adaptive-search thresholds outside the
Problem DSL; these belong to solver configuration or the quantum model.

### Validation for proposed extensions

| Proposed rule | Context | Meaning |
|---|---|---|
| groupWithinPlan | ActivityGroup | Every member belongs to the group's plan; members are distinct |
| validGroupBounds | ActivityGroup | `0 ≤ minimumSelected ≤ maximumSelected ≤ number of members` |
| prerequisiteWithinPlan | Prerequisite | Both endpoints belong to its plan and are distinct |
| jointParticipationWithinPlan | JointParticipation | Both endpoints belong to its plan and are distinct |
| nonNegativeCost | Activity | `cost ≥ 0` |
| nonNegativeBudget | ActivityPlan | `budget ≥ 0` |
| validProgrammeBounds | ActivityPlan | `0 ≤ minimumSelected ≤ maximumSelected ≤ number of activities` |
| nonNegativeDurationLimit | ActivityPlan | `maximumTotalDuration ≥ 0` |

Prerequisite cycles need not be invalid: they imply joint selection of the cycle's activities.
Likewise, conflicting mandatory activities or incompatible group requirements may produce
well-formed but infeasible instances. Validation should distinguish malformed input from a
valid optimisation problem with no feasible solution.

### Traceability and limits of the sources

- Assignment §6.1–6.3 motivates the concept tables, connections and mapping to the solution DSL.
- Annex A, D3 supplies weighted non-conflicting activity selection and pairwise exclusion.
- Annex A, class C supplies integer linear atoms with equality and less-than-or-equal relations;
  class D adds a linear minimisation objective. Proposed rules use these forms.
- The supplied Introduction to Quantum Computing slides provide background on Grover,
  constraint oracles and reversible arithmetic; they do not define the event-planning concepts.
  The three supplied PDF copies have identical contents.
- “Own design” and “Own extension” explicitly identify group design choices rather than claims
  that the cited sources propose these domain concepts. Additional external domain examples
  and references are still needed for the broader analysis requested by §6.1.

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

## Solution DSL (bounded integer linear optimisation)

**Status: proposed concept design; no Solution DSL Python metamodel was supplied.**
For this project, the Solution DSL represents the mathematical optimisation instance
produced by T1, rather than the optimal activity subset returned after execution.
It follows Annex A, class D: class C constraints plus a linear minimisation objective.
D3 uses only binary variables; a `bits` attribute also allows the bounded unsigned
integer variables specified by the general class C/D intermediate model.

### Concept list

Intrinsic properties become attributes; extrinsic properties become associations.
“Abstract” denotes a shared supertype, not an instantiable model element. The class
names and containment structure below are our design; the mathematical semantics
come from the cited assignment sections.

| Concept | Intrinsic properties | Extrinsic properties / connections | Meaning and mapping from the Problem DSL | Reference |
|---|---|---|---|---|
| ILPModel | `name: str` | Owns 1..* IntegerVariables; exactly 1 Objective; exactly 1 root BooleanExpression | Complete optimisation instance generated from one ActivityPlan | Annex A, class D; own structure |
| IntegerVariable | `name: str`, `bits: int` | Owned by exactly 1 ILPModel; referenced by 0..* LinearTerms | Unsigned domain `0..2^bits−1`; each Activity creates one variable with `bits = 1` | Annex A, classes C/D; D3 |
| LinearExpression | `constant: int` | Owned by exactly 1 Objective or LinearAtom; owns 0..* LinearTerms | Represents `a_0 + Σ a_i y_i`; permits constant-only expressions | Annex A, classes C/D |
| LinearTerm | `coefficient: int` | Owned by exactly 1 LinearExpression; refers to exactly 1 IntegerVariable | One integer coefficient multiplied by one variable; no variable products | Annex A, classes C/D |
| Objective | No required intrinsic properties; minimisation is fixed by the language | Owned by exactly 1 ILPModel; owns exactly 1 LinearExpression | Minimise `g(y)`; activity values become coefficients `−value_i`, with constant 0 | Annex A, class D |
| BooleanExpression (abstract) | None | Has exactly 1 containment owner: the ILPModel as root, or a BooleanGroup as child | Common type for atoms, groups and Boolean constants | Annex A, class C; own hierarchy |
| LinearAtom | `comparison: ComparisonOperator` | Subtype of BooleanExpression; owns exactly 1 LinearExpression | Tests `expression = 0` or `expression ≤ 0`; right-hand side fixed at zero | Annex A, class C |
| ComparisonOperator | Enumeration literals `EQ`, `LE` | Classifies each LinearAtom | Only the two normalised comparison forms are primitive | Annex A, class C |
| BooleanGroup | `operator: LogicalOperator` | Subtype of BooleanExpression; owns 2..* BooleanExpressions as children | Recursively combines constraints through AND or OR | Annex A, class C |
| LogicalOperator | Enumeration literals `AND`, `OR` | Classifies each BooleanGroup | Conjunction requires all children; disjunction requires at least one | Annex A, class C |
| BooleanConstant | `value: bool` | Subtype of BooleanExpression; no children | Explicit TRUE for an unconstrained instance; FALSE can represent an unsatisfiable formula | Own representation of Boolean identities |

A binary variable is an IntegerVariable with `bits = 1`, not a separate class.
For D3, every generated variable has this width. Each expression is owned rather than
shared, while variable references are shared across expressions. The constraint structure
is a finite tree: nodes cannot have two containment parents or contain themselves.

### T1 mapping rules

Let `y_i = 1` mean that activity i is selected. Preserve the activity-to-variable mapping
in a transformation trace so measured assignments can later be decoded into activity
names. This trace can be external to the reusable mathematical DSL; it must be derived
from the models rather than reconstructed manually.

| Problem input | Solution model generated by T1 |
|---|---|
| ActivityPlan | One ILPModel |
| Activity i | One IntegerVariable named deterministically, with `bits = 1` |
| All activity values | Objective expression: constant 0, one term `−value_i · y_i` per activity |
| Effective conflict pair {i,j} | LE atom: constant −1, terms `1·y_i` and `1·y_j` |
| Mandatory activity i | EQ atom: constant 1, term `−1·y_i` |
| All generated hard constraints | AND group when there are at least two atoms; the atom itself when there is one; BooleanConstant(TRUE) when there are none |
| Names, conflict reasons, intervals and resource links | Names/trace metadata and inputs to conflict derivation; no additional ILP variables |
| Proposed group bounds, prerequisite, budget and other extensions | Additional atoms using the same expressions and variables, only after the corresponding Problem DSL extension is implemented |

Explicit and resource-derived conflicts are merged before generating atoms, so each
unordered pair produces only one exclusion constraint. The current D3 mapping needs
only AND; OR remains available because the assignment's general intermediate language
allows both connectives. Resource exclusivity is a hard constraint, not an objective penalty.

### Well-formedness constraints to implement

These are proposed validation rules, not claims that B-OCL already supports them.
Express them in OCL and provide tested Python equivalents where the evaluator cannot
handle the required navigation or recursion.

| Rule | Context | Requirement |
|---|---|---|
| uniqueVariableNames | ILPModel | Variable names are unique within the model |
| positiveBitWidth | IntegerVariable | `bits ≥ 1` |
| referencesWithinModel | LinearTerm | The referenced variable belongs to the model containing the expression |
| uniqueVariableTerms | LinearExpression | At most one term per variable; combine repeated coefficients before constructing the model |
| nonZeroCoefficient | LinearTerm | `coefficient ≠ 0`; omit zero terms as a canonicalisation choice |
| validComparison | LinearAtom | Comparison is EQ or LE, with zero as the implicit right-hand side |
| validBooleanGroup | BooleanGroup | Operator is AND or OR and there are at least two children |
| validContainment | ILPModel / owned elements | Exactly one objective and root; each contained element has one owner; all nodes are reachable from the root/objective; no containment cycles |
| binaryD3Encoding | T1 output for D3 | Every generated variable has `bits = 1`; this is specific to D3, not the general DSL |

Infeasibility is not a well-formedness violation. Contradictory atoms are valid input to
the solver. An absent feasible solution must be reported as such. The empty selection
is feasible for the current D3 model when there are no mandatory activities.

### Small hand-worked mapping example

Three activities A, B and C have values 5, 8 and 4. A conflicts with B, and B conflicts
with C. A is mandatory. Each activity produces one one-bit variable.

| Model element | Mathematical content | Expression representation |
|---|---|---|
| Objective | Minimise `−5y_A − 8y_B − 4y_C` | Constant 0; coefficients −5, −8, −4 |
| Conflict A–B | `y_A + y_B − 1 ≤ 0` | LE atom; constant −1; coefficients 1, 1 |
| Conflict B–C | `y_B + y_C − 1 ≤ 0` | LE atom; constant −1; coefficients 1, 1 |
| Mandatory A | `1 − y_A = 0` | EQ atom; constant 1; coefficient −1 |
| Root constraint | AND of the three atoms | BooleanGroup(AND) with three children |

The optimal assignment is `(y_A, y_B, y_C) = (1, 0, 1)`, with objective −9 and
selected value 9. This illustrates the mapping; a hand-built B-UML object model is
still a separate Part I deliverable.

### Boundary with solver configuration and the quantum model

The Solution DSL contains the objective and feasibility formula. Grover rounds, shots,
random seeds and the unsuccessful-search stopping limit belong to solver configuration;
qubits, gates, registers and measurements belong to the BESSER quantum model.

For class D, execution maintains a threshold `t` and searches for a feasible assignment
satisfying `g(y) − t + 1 ≤ 0`. This transient atom uses the same LinearAtom representation,
but its changing threshold is execution state rather than a fixed activity-plan property.
The strict improvement rewrite relies on the objective being integer-valued.

For T2, bounds for an expression `e = a_0 + Σ a_i y_i` can be derived using
`U_i = 2^bits_i − 1`:

- `e_min = a_0 + Σ min(0, a_i U_i)`.
- `e_max = a_0 + Σ max(0, a_i U_i)`.
- Choose the smallest signed width B ≥ 1 such that
  `−2^(B−1) ≤ e_min` and `e_max ≤ 2^(B−1) − 1`.

These bounds size arithmetic result registers; they do not include all ancillary qubits.
Recompute bounds for transient threshold expressions as needed. Bounds and register
sizes are derived information, not independently editable mathematical inputs.
References: Annex A, class C (expression ranges and reversible arithmetic) and class D
(adaptive threshold search). The quantum introduction slides provide background rather
than a specification of this metamodel structure.

## Solver configuration

| Concept | Intrinsic properties | Extrinsic properties |
|---|---|---|
| | | |

## Test instances

| Name | Kind / story | #activities | #conflicts | Known optimum | Source |
|---|---|---|---|---|---|
| | | | | | |
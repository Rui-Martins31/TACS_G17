# QMDE D3: Weighted Non-Conflicting Activities via Grover Adaptive Search

TACS 2026/27 (FEUP M.EIC) group project. A model-driven chain that turns an activity-selection
problem written in a domain-specific language into a runnable Qiskit program:

```
Problem model ──T1──▶ 0/1 ILP model ──T2──▶ BESSER quantum circuit ──T3 (BESSER)──▶ Qiskit ──▶ Aer
```

Problem D3: choose the subset of non-conflicting activities with maximum total value
(Maximum-Weight Independent Set), solved with Grover Adaptive Search (Dürr–Høyer; Gilliam et al. 2021).

## Group

| Student number | Name              | GitHub |
|----------------|-------------------|--------|
| 202207410      | Lucas Branquinho  |        |
| 202104636      | Rui Martins       |        |
| 202207742      | Margarida Fonseca |        |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Checking the metamodels

```bash
python -m tests.test_problem_dsl   # Valid example, 8 broken variants and 8 malformed models
```

The checker reports BESSER structural errors before evaluating domain constraints.
This test module uses `run()`; execute it with the command above, not unittest discovery.

## Repository layout

| Path | Contents |
|---|---|
| `metamodels/` | B-UML metamodels with OCL: problem DSL, ILP DSL, solver configuration |
| `models/examples/` | Hand-built example models (Part I) |
| `models/instances/` | Test instances written in the problem DSL |
| `tests/` | B-OCL checks over valid and invalid models |
| `transformations/` | T1 (problem → ILP) and T2 (ILP → quantum circuit) (Part II) |
| `generated/` | Generated Qiskit code; **never edited by hand** |
| `validation/` | Classical baseline and metrics (Part II) |
| `docs/part1/` | Concept lists and Part I report |
| `docs/planning/` | Deadlines, deliverables, problem guide |
| `LLM_USAGE_LOG.md` | LLM usage log (required by the assignment) |

## Running the demo

_Part II: single documented command goes here._

# Oracle: ILP to quantum circuit

Implementation: [ilp_to_oracle.py](../../transformations/ilp_to_oracle.py), issue #6. \
Worked example: [oracle_expected_tiny_conference.md](oracle_expected_tiny_conference.md).

The oracle flips the phase of every assignment `y` that satisfies all ILP constraints.

---

## Usage

```python
from models.instances.tiny_conference import build
from transformations.problem_to_ilp import transform
from transformations.ilp_to_oracle import build_oracle

ilp_model, mapping = transform(build())
circuit, layout = build_oracle(ilp_model, mapping)
```

- `build_oracle` -> compute, mark, uncompute
- `build_compute` -> compute only (to test the arithmetic)
- `extra_atoms=[Atom(...)]` -> lets T2 add the threshold atom `g(y) - t + 1 <= 0`

---

## Layout

- `y_i` -> qubit `i` (same order as T1's mapping)
- one register per atom, lowest bit first, sign bit last

tiny_conference: 4 (y) + 3 x 2 (atoms) = 10 qubits.

---

## Steps

| Step | What it does | Reference |
|------|--------------|-----------|
| Width | smallest B with -2^(B-1) <= min and max <= 2^(B-1) - 1 | Annex A, class C |
| Compute | add `e - 1` (LE) or `e` (EQ) into the register with QFT + phase gates | Draper (2000) |
| Compare | LE: sign bit is 1. EQ: all bits are 0 | Gilliam et al. (2021) |
| Mark | one multi-controlled Z over all atom flags | Annex A, class C |
| Uncompute | same additions with negative angles | Bennett (1973) |

Only basic gates are used (X, Z, Phase, CPhase, QFT). BESSER's `ComparisonGate` becomes a placeholder in the Qiskit generator.

---

## Testing

```bash
.venv/bin/python -m unittest tests.test_ilp_to_oracle -v
```

Checks all 16 tiny_conference inputs against the classical constraints, scratch qubits returning to 0, qubit order, an equality atom, an infeasible instance and an instance with no constraints.

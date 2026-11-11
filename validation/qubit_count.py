"""Exact qubit counts of the GAS circuits for each instance.

The counts come from the same code that builds the circuits (T1 + oracle), not
from a separate formula:

- Round 1 has no threshold: the oracle layout gives the exact qubit count
  (one qubit per activity, plus one register per constraint atom whose width
  follows Annex A, class C: the smallest two's-complement width that holds every
  value of the atom).
- Later rounds add the threshold atom g(y) - t + 1 <= 0, where t is the best
  objective found so far (Durr & Hoyer; Gilliam et al., Quantum 5, 428, 2021).
  Its register width depends on t, so we build it for every value t can take
  (every feasible objective value, by brute force) and report the largest.

Run: python -m validation.qubit_count
"""

from dataclasses import dataclass
from itertools import product

from transformations.ilp_to_gas import objective_atom
from transformations.ilp_to_oracle import Atom, atoms_from_ilp, build_oracle
from transformations.problem_to_ilp import transform

# Annex A, Test instances / Section 7.3: "roughly up to 20 qubits".
QUBIT_BUDGET = 20


@dataclass(frozen=True)
class QubitCount:
    activities: int        # decision qubits, one per y_i
    conflict_qubits: int   # registers of LE atoms (conflicts)
    mandatory_qubits: int  # registers of EQ atoms (mandatory activities)
    threshold_qubits: int  # largest threshold register over all reachable thresholds
    first_round: int       # exact circuit size without threshold
    peak: int              # exact largest circuit size over the whole search


def _holds(atom, bits):
    value = atom.constant + sum(c * bits[i] for i, c in atom.coefficients.items())
    return value <= 0 if atom.comparison == "LE" else value == 0


def count_qubits(problem_model):
    ilp, mapping = transform(problem_model)
    atoms = atoms_from_ilp(ilp, mapping)
    _, layout = build_oracle(ilp, mapping)
    objective = objective_atom(ilp, mapping)

    def g(bits):
        return objective.constant + sum(c * bits[i] for i, c in objective.coefficients.items())

    reachable = {g(bits) for bits in product((0, 1), repeat=len(mapping))
                 if all(_holds(a, bits) for a in atoms)}
    # Same threshold atom as transformations.ilp_to_gas.search; with no feasible
    # selection no best value is ever found and no threshold round happens.
    threshold = max((Atom(objective.name, "LE", objective.constant - best + 1,
                          objective.coefficients).width() for best in reachable), default=0)
    width = {"LE": 0, "EQ": 0}
    for atom in atoms:
        width[atom.comparison] += atom.width()
    return QubitCount(len(mapping), width["LE"], width["EQ"], threshold,
                      layout.num_qubits, layout.num_qubits + threshold)


def main():
    from models.instances import INSTANCES

    header = (f"{'instance':<14}{'activities':>11}{'conflicts':>10}{'mandatory':>10}"
              f"{'threshold':>10}{'round 1':>9}{'peak':>6}  within ~{QUBIT_BUDGET}")
    print(header)
    print("-" * len(header))
    for inst in sorted(INSTANCES, key=lambda i: count_qubits(i.build()).peak):
        q = count_qubits(inst.build())
        print(f"{inst.name:<14}{q.activities:>11}{q.conflict_qubits:>10}{q.mandatory_qubits:>10}"
              f"{q.threshold_qubits:>10}{q.first_round:>9}{q.peak:>6}  "
              f"{'yes' if q.peak <= QUBIT_BUDGET else 'NO'}")
    print("\nColumns other than 'round 1' and 'peak' are qubits per part of the circuit.")


if __name__ == "__main__":
    main()

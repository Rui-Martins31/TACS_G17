from dataclasses import dataclass
from math import pi

from besser.BUML.metamodel.quantum import quantum as bq

from metamodels.problem_checks import linked, objects_of


@dataclass
class Atom:
    """One linear atom `constant + sum(coefficients[i] * y_i) (<= | =) 0`.

    `coefficients` maps variable position i (T1 mapping order) to its coefficient.
    T2 can pass extra atoms of this type, e.g. the threshold atom g(y) - t + 1 <= 0.
    """
    name: str
    comparison: str  # "LE" or "EQ"
    constant: int
    coefficients: dict

    def stored_constant(self):
        # e <= 0  <=>  e - 1 < 0 for integers, and "< 0" is the sign bit of a
        # two's-complement register (Gilliam et al., Quantum 5, 428, 2021).
        # The shift is folded into the constant, so it costs no gates.
        return self.constant - 1 if self.comparison == "LE" else self.constant

    def value_range(self):
        # Each y_i is one bit, so the extremes take each coefficient or 0.
        low = self.stored_constant() + sum(min(0, a) for a in self.coefficients.values())
        high = self.stored_constant() + sum(max(0, a) for a in self.coefficients.values())
        return low, high

    def width(self):
        # Annex A, class C (pp. 12-13): smallest B with
        # -2^(B-1) <= min and max <= 2^(B-1) - 1 (two's complement).
        low, high = self.value_range()
        bits = 1
        while not (-(1 << (bits - 1)) <= low and high <= (1 << (bits - 1)) - 1):
            bits += 1
        return bits


@dataclass
class OracleLayout:
    """Qubit positions. Atom registers are listed lowest bit first, sign bit last."""
    variable_qubits: list
    atom_qubits: dict
    num_qubits: int


def atoms_from_ilp(ilp_model, mapping):
    """Read the conjunction of linear atoms under the ILP problem's root."""
    problem, = objects_of(ilp_model, "ILPProblem")
    position = {variable: i for i, variable in enumerate(mapping.values())}
    for variable in position:
        if variable.bitWidth != 1:
            raise NotImplementedError("Oracle supports one-bit variables only (Annex A, D3)")

    def collect(constraint):
        if constraint.classifier.name == "LinearConstraint":
            return [constraint]
        # Annex A, class C (pp. 12-13): constraints are a conjunction of atoms.
        if constraint.operator != "AND":
            raise NotImplementedError(f"Unsupported logical operator {constraint.operator}")
        return [a for operand in linked(constraint, "operands") for a in collect(operand)]

    atoms = []
    for constraint in sorted((a for root in linked(problem, "root") for a in collect(root)),
                             key=lambda a: a.name):
        expression, = linked(constraint, "linearExpression")
        coefficients = {}
        for term in linked(expression, "terms"):
            i = position[linked(term, "variable")[0]]
            coefficients[i] = coefficients.get(i, 0) + term.coefficient
        atoms.append(Atom(constraint.name, constraint.comparison, expression.constant,
                          coefficients))
    return atoms


def _layout(num_variables, atoms):
    # T1 contract (docs/part2/t1.md): y_i is position i of the mapping -> qubit i.
    next_qubit = num_variables
    atom_qubits = {}
    for atom in atoms:
        atom_qubits[atom.name] = list(range(next_qubit, next_qubit + atom.width()))
        next_qubit += atom.width()
    return OracleLayout(list(range(num_variables)), atom_qubits, next_qubit)


def _add_atom(circuit, atom, register, sign=1):
    """Add sign * (stored constant + sum a_i y_i) into register, modulo 2^B.

    Draper, "Addition on a quantum computer", arXiv:quant-ph/0008033 (2000):
    in the Fourier basis, adding c is a phase 2*pi*c*2^j / 2^B on qubit j.
    A term a_i * y_i is the same phase controlled by y_i. Negative values wrap
    modulo 2^B, which is exactly two's complement.
    """
    size = 1 << len(register)

    def angle(value, j):
        # None when the phase is a multiple of 2*pi (the gate would be identity).
        return None if (value << j) % size == 0 else 2 * pi * sign * value * (1 << j) / size

    circuit.add_operation(bq.QFTGate(register))
    for j, qubit in enumerate(register):
        if (theta := angle(atom.stored_constant(), j)) is not None:
            circuit.add_operation(bq.PhaseGate(qubit, theta))
        for i, coefficient in sorted(atom.coefficients.items()):
            if (theta := angle(coefficient, j)) is not None:
                circuit.add_operation(bq.CPhaseGate(i, qubit, theta))
    circuit.add_operation(bq.QFTGate(register, inverse=True))


def _compute(circuit, atoms, layout, sign=1):
    for atom in atoms:
        _add_atom(circuit, atom, layout.atom_qubits[atom.name], sign)


def _mark(circuit, atoms, layout):
    """Phase -1 iff every atom holds.

    LE atom: holds iff its sign bit is 1. EQ atom: holds iff all bits are 0, so
    X every bit first and require all of them to be 1 (no anti-controls needed).
    """
    if not atoms:
        # No constraints: every assignment is feasible, so the oracle is -I.
        # (XZ)^2 = -I on any qubit (Nielsen & Chuang, sec. 2.1.3 Pauli algebra).
        for _ in range(2):
            circuit.add_operation(bq.PauliXGate(0))
            circuit.add_operation(bq.PauliZGate(0))
        return

    flips = [q for a in atoms if a.comparison == "EQ" for q in layout.atom_qubits[a.name]]
    controls = []
    for atom in atoms:
        register = layout.atom_qubits[atom.name]
        controls += register if atom.comparison == "EQ" else [register[-1]]
    for qubit in flips:
        circuit.add_operation(bq.PauliXGate(qubit))
    # Annex A, class C (pp. 12-13): conjunction of atoms -> one multi-controlled Z.
    circuit.add_operation(bq.PauliZGate(controls[-1], control_qubits=controls[:-1] or None))
    for qubit in flips:
        circuit.add_operation(bq.PauliXGate(qubit))


def _prepare(ilp_model, mapping, extra_atoms):
    atoms = atoms_from_ilp(ilp_model, mapping) + list(extra_atoms)
    layout = _layout(len(mapping), atoms)
    circuit = bq.QuantumCircuit(f"{ilp_model.name}_oracle", layout.num_qubits)
    return atoms, layout, circuit


def build_compute(ilp_model, mapping, extra_atoms=()):
    """Only the arithmetic: each atom register ends holding its stored value."""
    atoms, layout, circuit = _prepare(ilp_model, mapping, extra_atoms)
    _compute(circuit, atoms, layout)
    return circuit, layout


def build_oracle(ilp_model, mapping, extra_atoms=()):
    """Compute -> mark -> uncompute. Scratch registers return to |0>, so the
    oracle acts as a pure phase flip on y (Bennett, IBM J. Res. Dev. 17, 1973)."""
    atoms, layout, circuit = _prepare(ilp_model, mapping, extra_atoms)
    _compute(circuit, atoms, layout)
    _mark(circuit, atoms, layout)
    _compute(circuit, list(reversed(atoms)), layout, sign=-1)
    return circuit, layout

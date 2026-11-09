"""Check the reversible feasibility oracle against classical constraint evaluation."""

import unittest
from itertools import product

import numpy as np
from qiskit import QuantumCircuit as QiskitCircuit
from qiskit.circuit.library import HGate, PhaseGate, QFTGate, XGate, ZGate
from qiskit.quantum_info import Statevector

from besser.BUML.metamodel.quantum import quantum as bq

from metamodels.problem_checks import linked, objects_of
from models.instances.tiny_conference import build
from tests.test_problem_dsl import add_conflict
from tests.test_problem_to_ilp import independent_plan
from tests.test_solution_dsl import evaluate_constraint, evaluate_expression, slot_value
from transformations.ilp_to_oracle import build_compute, build_oracle
from transformations.problem_to_ilp import transform


# From docs/part2/oracle_expected_tiny_conference.md.
# Qiskit strings: q0 on the right, so each string is y_3 y_2 y_1 y_0.
TINY_MARKED = {"0000", "0001", "0010", "0100", "1000", "0101", "1001", "1010"}


def to_qiskit(circuit):
    """Translate a BESSER circuit gate by gate. Fail on anything unsupported."""
    qc = QiskitCircuit(circuit.num_qubits)
    for op in circuit.operations:
        if any(state is not bq.ControlState.CONTROL for state in op.control_states):
            raise AssertionError(f"{op!r}: use X gates around a control instead of anti-controls")
        if isinstance(op, bq.QFTGate):
            gate = QFTGate(len(op.target_qubits))
            if op.inverse:
                gate = gate.inverse()
        elif isinstance(op, (bq.PauliXGate, bq.CNOT)):
            gate = XGate()
        elif isinstance(op, bq.PauliZGate):
            gate = ZGate()
        elif isinstance(op, bq.HadamardGate):
            gate = HGate()
        elif isinstance(op, bq.CPhaseGate):
            gate = PhaseGate(op.theta)
        elif isinstance(op, bq.PhaseGate):
            gate = PhaseGate(op.parameter)
        else:
            raise AssertionError(f"Unsupported operation in oracle: {op!r}")
        controls = list(op.control_qubits)
        if controls:
            gate = gate.control(len(controls), annotated=False)
        qc.append(gate, controls + list(op.target_qubits))
    return qc


def basis_index(bits, qubits):
    """Statevector index with bits[k] placed on qubits[k]."""
    return sum(bit << qubit for bit, qubit in zip(bits, qubits))


def run_basis(circuit, index):
    """Run the circuit on one basis state and return the output statevector."""
    return Statevector.from_int(index, 2 ** circuit.num_qubits).evolve(to_qiskit(circuit))


def read_signed(index, qubits):
    """Two's-complement value stored on qubits (lowest bit first, sign bit last)."""
    unsigned = sum(((index >> qubit) & 1) << k for k, qubit in enumerate(qubits))
    return unsigned - (1 << len(qubits)) if unsigned >> (len(qubits) - 1) else unsigned


def atoms_of(model):
    return {atom.name: atom for atom in objects_of(model, "LinearConstraint")}


def stored_value(atom, assignment):
    """What the atom register must hold: e - 1 for e <= 0 (so the sign bit
    answers it), e itself for e = 0 (all bits zero answers it)."""
    value = evaluate_expression(linked(atom, "linearExpression")[0], assignment)
    return value - 1 if slot_value(atom, "comparison") == "LE" else value


def classically_feasible(model, assignment):
    problem, = objects_of(model, "ILPProblem")
    roots = linked(problem, "root")
    return not roots or evaluate_constraint(roots[0], assignment)


def assignments(mapping):
    for bits in product((0, 1), repeat=len(mapping)):
        yield bits, dict(zip(mapping.values(), bits))


def infeasible_plan():
    """Two mandatory activities that explicitly conflict: no feasible assignment."""
    model = independent_plan(("A", "B"), mandatory=("A", "B"))
    add_conflict(model, "a_b", "activity_0", "activity_1")
    return model


class TestOracleLayout(unittest.TestCase):
    def test_tiny_registers(self):
        model, mapping = transform(build())
        circuit, layout = build_oracle(model, mapping)
        self.assertIsInstance(circuit, bq.QuantumCircuit)
        # T1 contract (docs/part2/t1.md): y_i is position i of the mapping.
        self.assertEqual(layout.variable_qubits, [0, 1, 2, 3])
        self.assertEqual(set(layout.atom_qubits),
                         {"conflict_0_1", "conflict_1_2", "conflict_2_3"})
        used = list(layout.variable_qubits)
        for qubits in layout.atom_qubits.values():
            self.assertEqual(len(qubits), 2)
            used += qubits
        self.assertEqual(sorted(used), list(range(10)))
        self.assertEqual(layout.num_qubits, 10)
        self.assertEqual(circuit.num_qubits, 10)

    def test_register_width_rule(self):
        """Annex A, class C: smallest B with -2^(B-1) <= min and max <= 2^(B-1) - 1,
        taken over the value the register actually stores."""
        for source in (build(), independent_plan(mandatory=("A",)), infeasible_plan()):
            model, mapping = transform(source)
            _, layout = build_oracle(model, mapping)
            for name, atom in atoms_of(model).items():
                values = [stored_value(atom, a) for _, a in assignments(mapping)]
                width = 1
                while not (-(1 << (width - 1)) <= min(values)
                           and max(values) <= (1 << (width - 1)) - 1):
                    width += 1
                self.assertEqual(len(layout.atom_qubits[name]), width, name)


class TestCompute(unittest.TestCase):
    def assert_compute_matches_classical(self, source):
        model, mapping = transform(source)
        circuit, layout = build_compute(model, mapping)
        atoms = atoms_of(model)
        for bits, assignment in assignments(mapping):
            state = run_basis(circuit, basis_index(bits, layout.variable_qubits))
            index = int(np.argmax(np.abs(state.data)))
            self.assertAlmostEqual(abs(state.data[index]), 1.0, places=6,
                                   msg=f"{bits}: output is not a basis state")
            self.assertEqual([(index >> q) & 1 for q in layout.variable_qubits], list(bits),
                             f"{bits}: compute changed the input register")
            for name, qubits in layout.atom_qubits.items():
                self.assertEqual(read_signed(index, qubits),
                                 stored_value(atoms[name], assignment), f"{bits}, {name}")

    def test_tiny_conflict_atoms(self):
        """For conflict_0_1 the register must read 10, 11, 11, 00 (-2, -1, -1, 0)."""
        self.assert_compute_matches_classical(build())

    def test_equality_atom(self):
        self.assert_compute_matches_classical(independent_plan(mandatory=("A",)))


class TestOracleMarking(unittest.TestCase):
    def assert_marks(self, source, expected_marked):
        """Every basis input: phase -1 iff marked, all other qubits unchanged."""
        model, mapping = transform(source)
        circuit, layout = build_oracle(model, mapping)
        for bits, _ in assignments(mapping):
            index = basis_index(bits, layout.variable_qubits)
            state = run_basis(circuit, index)
            sign = -1 if bits in expected_marked else 1
            expected = Statevector.from_int(index, 2 ** circuit.num_qubits) * sign
            self.assertTrue(np.allclose(state.data, expected.data, atol=1e-6),
                            f"{bits}: expected phase {sign} with scratch qubits back to 0")

    def marked_labels(self, model, mapping):
        """Run the oracle on every Qiskit label of the y register (q0 on the right,
        scratch qubits at 0) and return the labels that get phase -1."""
        circuit, layout = build_oracle(model, mapping)
        qc = to_qiskit(circuit)
        n = len(layout.variable_qubits)
        marked = set()
        for label in ("".join(s) for s in product("01", repeat=n)):
            state = Statevector.from_label("0" * (layout.num_qubits - n) + label)
            out = state.evolve(qc)
            if np.allclose(out.data, -state.data, atol=1e-6):
                marked.add(label)
            else:
                self.assertTrue(np.allclose(out.data, state.data, atol=1e-6),
                                f"{label}: neither marked nor left unchanged")
        return marked

    def test_tiny_matches_hand_derived_list(self):
        model, mapping = transform(build())
        self.assertEqual(self.marked_labels(model, mapping), TINY_MARKED)

    def test_tiny_matches_classical_evaluation(self):
        model, mapping = transform(build())
        feasible = {bits for bits, a in assignments(mapping) if classically_feasible(model, a)}
        # The hand-derived list and the classical evaluation must agree.
        self.assertEqual({"".join(map(str, reversed(bits))) for bits in feasible}, TINY_MARKED)
        self.assert_marks(build(), feasible)

    def test_qubit_order(self):
        """Activities declared as (B, A); A sorts first, so A = y_0 = qubit 0.
        Only A is mandatory, so the marked labels have a 1 in the rightmost place."""
        source = independent_plan(("B", "A"), mandatory=("A",))
        model, mapping = transform(source)
        self.assertEqual([a.name for a in mapping], ["A", "B"])
        _, layout = build_oracle(model, mapping)
        self.assertEqual(layout.variable_qubits, [0, 1])
        self.assert_marks(source, {(1, 0), (1, 1)})
        self.assertEqual(self.marked_labels(model, mapping), {"01", "11"})

    def test_infeasible_marks_nothing(self):
        self.assert_marks(infeasible_plan(), set())

    def test_no_constraints_marks_everything(self):
        self.assert_marks(independent_plan(("A", "B")), set(product((0, 1), repeat=2)))


if __name__ == "__main__":
    unittest.main()

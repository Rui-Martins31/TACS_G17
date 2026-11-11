"""BESSER generation and Aer execution for the D3 gate subset."""

from pathlib import Path
from runpy import run_path
from tempfile import TemporaryDirectory

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from besser.BUML.metamodel.quantum import quantum as bq
from besser.generators.qiskit.qiskit_generator import QiskitGenerator


class D3QiskitGenerator(QiskitGenerator):
    """Supply the missing template and CP support; reuse BESSER's gate mapper."""

    def _get_base_gate_code(self, gate):
        if isinstance(gate, bq.CPhaseGate):
            # BESSER's _map_operation adds the existing control qubit separately.
            return f"PhaseGate({gate.theta!r})"
        return super()._get_base_gate_code(gate)

    def generate(self):
        if self.backend_type != "aer_simulator":
            raise ValueError("D3 execution supports only backend='aer_simulator'")
        if type(self.shots) is not int or self.shots < 1:
            raise ValueError("shots must be a positive integer")
        if len(self.model.qregs) != 1 or len(self.model.cregs) != 1:
            raise ValueError("D3 execution requires one quantum and one classical register")
        for op in self.model.operations:
            if type(op) not in {bq.HadamardGate, bq.PauliXGate, bq.PauliZGate,
                                bq.PhaseGate, bq.CPhaseGate, bq.QFTGate, bq.Measurement}:
                raise NotImplementedError(f"Unsupported D3 gate: {type(op).__name__}")
            if isinstance(op, bq.Measurement):
                if (op.basis != "Z" or type(op.output_bit) is not int
                        or not 0 <= op.output_bit < self.model.num_clbits):
                    raise ValueError("measurements need an explicit classical output bit in Z basis")
            if any(type(q) is not int or not 0 <= q < self.model.num_qubits
                   for q in op.target_qubits + op.control_qubits):
                raise ValueError("operation references a qubit outside the circuit")
        env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"),
                          undefined=StrictUndefined)
        source = env.get_template("qiskit_circuit.py.j2").render(
            circuit=self.model, operations_code=self._generate_operations_code(), shots=self.shots)
        path = Path(self.build_generation_path("qiskit_circuit.py"))
        path.write_text(source, encoding="utf-8")
        return path


def execute(besser_circuit, *, backend, shots, seed):
    """Generate fresh code, run it on Aer and return displayed counts unchanged."""
    if backend != "aer_simulator":
        raise ValueError("D3 execution supports only backend='aer_simulator'")
    if seed is not None and (type(seed) is not int or not 0 <= seed < 2 ** 32):
        raise ValueError("seed must be None or a 32-bit unsigned integer")
    # A unique path and fresh namespace prevent importing a previous round's code.
    with TemporaryDirectory(prefix="tacs_qiskit_") as directory:
        path = D3QiskitGenerator(besser_circuit, directory, backend_type=backend, shots=shots).generate()
        return dict(run_path(str(path))["run"](seed=seed))

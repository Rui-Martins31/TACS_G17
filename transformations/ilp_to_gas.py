"""T2 Grover rounds and adaptive search over the reversible feasibility oracle."""

from dataclasses import dataclass
from random import Random

from besser.BUML.metamodel.quantum import quantum as bq

from metamodels.problem_checks import linked, objects_of
from models.solver_config import SolverConfig
from transformations.ilp_to_oracle import Atom, atoms_from_ilp, build_oracle


@dataclass(frozen=True)
class RoundRecord:
    """One GAS round, kept for validation metrics."""
    threshold: int | None   # best objective before the round; None = feasibility-only oracle
    iterations: int         # Grover iterations k in this round's circuit
    shots: int              # executions of that circuit
    improved: bool

    @property
    def oracle_calls(self):
        # Each shot runs a circuit containing k oracle applications
        # (query counting as in Boyer et al. 1998 and Durr & Hoyer 1996).
        return self.iterations * self.shots


@dataclass(frozen=True)
class SearchResult:
    bits: tuple[int, ...] | None
    objective: int | None
    rounds: int
    stop_reason: str
    history: tuple[RoundRecord, ...] = ()

    @property
    def oracle_calls(self):
        return sum(record.oracle_calls for record in self.history)

    def selected_activities(self, mapping):
        """Names in T1 order, or None when no feasible candidate was sampled."""
        if self.bits is None:
            return None
        if len(mapping) != len(self.bits):
            raise ValueError("mapping must match the search result")
        return tuple(activity.name for activity, bit in zip(mapping, self.bits) if bit)


def build_round(oracle, layout, iterations):
    """Prepare uniform decision bits, then oracle/diffusion; scratch starts at zero."""
    if type(iterations) is not int or iterations < 0:
        raise ValueError("iterations must be a nonnegative integer")
    decision = layout.variable_qubits
    if not decision or oracle.num_qubits != layout.num_qubits:
        raise ValueError("oracle and layout must describe a nonempty decision register")
    circuit = bq.QuantumCircuit(oracle.name + "_round", layout.num_qubits)
    for qubit in decision:
        circuit.add_operation(bq.HadamardGate(qubit))
    for _ in range(iterations):
        for operation in oracle.operations:
            circuit.add_operation(operation)
        # Grover diffusion H X (controlled Z) X H on decisions only, up to global -1.
        for qubit in decision:
            circuit.add_operation(bq.HadamardGate(qubit))
            circuit.add_operation(bq.PauliXGate(qubit))
        circuit.add_operation(bq.PauliZGate(decision[-1], control_qubits=decision[:-1]))
        for qubit in decision:
            circuit.add_operation(bq.PauliXGate(qubit))
            circuit.add_operation(bq.HadamardGate(qubit))
    return circuit


def quantum_sampler(execute):
    """Adapt #8's executor to search's sampler contract; create once per search.

    execute(circuit, *, backend, shots, seed) returns Qiskit-style counts for
    the single classical register. It owns BESSER generation/backend execution.
    """
    rng = None

    def sample(oracle, layout, iterations, config):
        nonlocal rng
        if rng is None:
            rng = Random(config.seed)
        circuit = build_round(oracle, layout, iterations)
        n = len(layout.variable_qubits)
        circuit.add_creg(bq.ClassicalRegister("c", n))
        for i, qubit in enumerate(layout.variable_qubits):
            circuit.add_operation(bq.Measurement(qubit, output_bit=i))
        counts = execute(circuit, backend=config.backend, shots=config.shots,
                         seed=rng.randrange(2 ** 32))
        samples = []
        for label, count in counts.items():
            if (not isinstance(label, str) or len(label) != n or set(label) - {"0", "1"}
                    or type(count) is not int or count < 0):
                raise ValueError("executor must return binary counts for the decision register")
            # c[i] measured decision[i]; Qiskit displays c[n-1] ... c[0].
            samples.extend([tuple(map(int, reversed(label)))] * count)
        if len(samples) != config.shots:
            raise ValueError("executor counts must sum to config.shots")
        return samples

    return sample


def objective_atom(ilp_model, mapping):
    problem, = objects_of(ilp_model, "ILPProblem")
    expression, = linked(problem, "objective")
    positions = {variable: i for i, variable in enumerate(mapping.values())}
    coefficients = {}
    for term in linked(expression, "terms"):
        i = positions[linked(term, "variable")[0]]
        coefficients[i] = coefficients.get(i, 0) + term.coefficient
    return Atom("objective_threshold", "LE", expression.constant, coefficients)


def _value(atom, bits):
    return atom.constant + sum(coefficient * bits[i] for i, coefficient in atom.coefficients.items())


def search(ilp_model, mapping, config, sampler):
    """Minimise an ILP via sampled candidates; a finite stop is not a proof.

    The first round marks all feasible assignments. Subsequent rounds mark only
    feasible assignments with objective strictly below the best observed value.
    The sampler is responsible for honouring config.shots, seed and backend.
    """
    if not isinstance(config, SolverConfig):
        raise TypeError("config must be a SolverConfig")
    objective = objective_atom(ilp_model, mapping)
    constraints = atoms_from_ilp(ilp_model, mapping)
    if any(atom.name == objective.name for atom in constraints):
        raise ValueError("constraint name reserved for objective threshold")
    rng = Random(config.seed)
    best_bits, best_value, failures, rounds = None, None, 0, 0
    history = []
    window = float(config.initial_window)
    while rounds < config.max_rounds and failures < config.max_rounds_without_improvement:
        threshold = () if best_value is None else (
            Atom(objective.name, "LE", objective.constant - best_value + 1, objective.coefficients),
        )
        oracle, layout = build_oracle(ilp_model, mapping, threshold)
        iterations = (config.fixed_iterations if config.round_policy == "fixed"
                      else rng.randrange(max(1, int(window))))
        improved = False
        threshold_before = best_value
        for candidate in sampler(oracle, layout, iterations, config):
            bits = tuple(candidate)
            if len(bits) != len(mapping) or any(type(bit) is not int or bit not in (0, 1) for bit in bits):
                raise ValueError("sampler must return bit tuples in mapping order")
            if any((_value(a, bits) > 0 if a.comparison == "LE" else _value(a, bits) != 0)
                   for a in constraints):
                continue
            value = _value(objective, bits)
            if best_value is None or value < best_value:
                best_bits, best_value, improved = bits, value, True
        rounds += 1
        history.append(RoundRecord(threshold_before, iterations, config.shots, improved))
        if improved:
            failures, window = 0, float(config.initial_window)
        else:
            failures += 1
            window = min(config.max_window, window * config.growth_factor)
    reason = "max_rounds" if rounds == config.max_rounds else "max_rounds_without_improvement"
    return SearchResult(best_bits, best_value, rounds, reason, tuple(history))

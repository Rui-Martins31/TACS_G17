"""T2 adaptive-search orchestration over the existing reversible oracle.

The caller supplies a sampler: (oracle, layout, iterations, config) -> iterable
of bit tuples in mapping order. It owns circuit diffusion, execution and decoding.
"""

from dataclasses import dataclass
from random import Random

from metamodels.problem_checks import linked, objects_of
from models.solver_config import SolverConfig
from transformations.ilp_to_oracle import Atom, atoms_from_ilp, build_oracle


@dataclass(frozen=True)
class SearchResult:
    bits: tuple[int, ...] | None
    objective: int | None
    rounds: int
    stop_reason: str


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
    window = float(config.initial_window)
    while rounds < config.max_rounds and failures < config.max_rounds_without_improvement:
        threshold = () if best_value is None else (
            Atom(objective.name, "LE", objective.constant - best_value + 1, objective.coefficients),
        )
        oracle, layout = build_oracle(ilp_model, mapping, threshold)
        iterations = (config.fixed_iterations if config.round_policy == "fixed"
                      else rng.randrange(max(1, int(window))))
        improved = False
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
        if improved:
            failures, window = 0, float(config.initial_window)
        else:
            failures += 1
            window = min(config.max_window, window * config.growth_factor)
    reason = "max_rounds" if rounds == config.max_rounds else "max_rounds_without_improvement"
    return SearchResult(best_bits, best_value, rounds, reason)

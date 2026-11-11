import argparse
from dataclasses import dataclass, replace
from math import asin, floor, pi, sin, sqrt
from statistics import mean, median

from execution.qiskit_executor import execute
from models.gas_defaults import DEFAULT_CONFIG
from models.instances import BY_NAME, INSTANCES
from transformations.ilp_to_gas import objective_atom, quantum_sampler, search
from transformations.ilp_to_oracle import Atom, atoms_from_ilp, build_oracle
from transformations.problem_to_ilp import transform
from validation.classical_baseline import solve
from validation.qubit_count import count_qubits


def ideal_probability(marked, total, k):
    if marked == 0:
        return 0.0
    theta = asin(sqrt(marked / total))
    return sin((2 * k + 1) * theta) ** 2


def best_iterations(marked, total):
    """Iterations maximising P(k): floor(pi / (4 theta)) (Boyer et al. 1998)."""
    return floor(pi / (4 * asin(sqrt(marked / total)))) if marked else 0


def _value(atom, bits):
    return atom.constant + sum(c * bits[i] for i, c in atom.coefficients.items())


def _feasible(atoms, bits):
    return all(_value(a, bits) <= 0 if a.comparison == "LE" else _value(a, bits) == 0
               for a in atoms)


@dataclass(frozen=True)
class AmplificationRow:
    instance: str
    marked_set: str      # "valid" or "optimal"
    marked: int          # M, from the classical baseline
    total: int           # N = 2^n
    iterations: int
    ideal: float
    measured: float
    shots: int


def amplification(name, iterations=None, shots=2048, seed=7):
    """Experiment A for one instance; returns AmplificationRow objects."""
    ilp, mapping = transform(BY_NAME[name].build())
    baseline = solve(BY_NAME[name].build())
    constraints = atoms_from_ilp(ilp, mapping)
    objective = objective_atom(ilp, mapping)
    total = 2 ** len(mapping)
    config = replace(DEFAULT_CONFIG, shots=shots, seed=seed)

    cases = [("valid", (), baseline.feasible_count, lambda b: _feasible(constraints, b))]
    if baseline.optimum_value is not None:
        best = -baseline.optimum_value
        # Threshold atom g(y) - best <= 0 marks exactly the optimal selections.
        only_optimal = Atom(objective.name, "LE", objective.constant - best, objective.coefficients)
        cases.append(("optimal", (only_optimal,), len(baseline.optimal_selections),
                      lambda b: _feasible(constraints, b) and _value(objective, b) == best))

    rows = []
    for label, extra, marked, is_marked in cases:
        oracle, layout = build_oracle(ilp, mapping, extra)
        ks = iterations if iterations is not None else sorted({0, 1, best_iterations(marked, total)})
        for k in ks:
            samples = quantum_sampler(execute)(oracle, layout, k, config)
            hits = sum(1 for bits in samples if is_marked(bits))
            rows.append(AmplificationRow(name, label, marked, total, k,
                                         ideal_probability(marked, total, k), hits / shots, shots))
    return rows


@dataclass(frozen=True)
class GasStatistics:
    instance: str
    qubits: int
    brute_force_evaluations: int   # 2^n selections checked classically
    runs: int
    successes: int                 # optimum found (or, if infeasible, nothing reported)
    oracle_calls: tuple            # per run, whole search
    oracle_calls_to_best: tuple    # per run, up to the round that found the returned answer
    rounds: tuple

    @property
    def success_rate(self):
        return self.successes / self.runs


def gas_statistics(name, runs=10, config=DEFAULT_CONFIG, first_seed=0):
    """Experiment B for one instance."""
    baseline = solve(BY_NAME[name].build())
    successes, calls, calls_to_best, rounds = 0, [], [], []
    for seed in range(first_seed, first_seed + runs):
        ilp, mapping = transform(BY_NAME[name].build())
        result = search(ilp, mapping, replace(config, seed=seed), quantum_sampler(execute))
        if baseline.optimum_value is None:
            successes += result.bits is None
        else:
            successes += result.objective == -baseline.optimum_value
        last = max((i for i, r in enumerate(result.history) if r.improved), default=-1)
        calls.append(result.oracle_calls)
        calls_to_best.append(sum(r.oracle_calls for r in result.history[:last + 1]))
        rounds.append(result.rounds)
    return GasStatistics(name, count_qubits(BY_NAME[name].build()).peak, 2 ** baseline.n,
                         runs, successes, tuple(calls), tuple(calls_to_best), tuple(rounds))


def print_amplification(rows):
    print("A. Amplification: measured vs ideal probability of a marked selection")
    print("| Instance | Marked | M / N | k | Ideal P(k) | Measured | Shots |")
    print("|---|---|---:|---:|---:|---:|---:|")
    for r in rows:
        print(f"| {r.instance} | {r.marked_set} | {r.marked}/{r.total} | {r.iterations} "
              f"| {r.ideal:.3f} | {r.measured:.3f} | {r.shots} |")


def print_gas(stats):
    print("\nB. Grover Adaptive Search vs exact optimum "
          f"(solver config: {DEFAULT_CONFIG.round_policy}, shots={DEFAULT_CONFIG.shots}, "
          f"max_rounds={DEFAULT_CONFIG.max_rounds}, "
          f"stop after {DEFAULT_CONFIG.max_rounds_without_improvement} without improvement)")
    print("| Instance | Qubits | Brute force 2^n | Success | Oracle calls to answer (median / mean) "
          "| Oracle calls total (mean) | Rounds (mean) |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for s in stats:
        print(f"| {s.instance} | {s.qubits} | {s.brute_force_evaluations} "
              f"| {s.successes}/{s.runs} ({s.success_rate:.0%}) "
              f"| {median(s.oracle_calls_to_best):g} / {mean(s.oracle_calls_to_best):.1f} "
              f"| {mean(s.oracle_calls):.1f} | {mean(s.rounds):.1f} |")
    print("\nSuccess for the infeasible instance means no selection was reported. A bounded "
          "search proves neither optimality nor infeasibility; the classical baseline does.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate the quantum chain against the exact classical baseline.")
    parser.add_argument("--instance", action="append", choices=BY_NAME,
                        help="repeat to select several (default: all)")
    parser.add_argument("--runs", type=int, default=10, help="GAS runs (seeds) per instance")
    parser.add_argument("--shots", type=int, default=2048, help="shots per amplification point")
    parser.add_argument("--skip-gas", action="store_true", help="run only experiment A")
    args = parser.parse_args(argv)
    names = args.instance or [i.name for i in INSTANCES]
    names = sorted(names, key=lambda n: count_qubits(BY_NAME[n].build()).peak)

    print_amplification([row for n in names for row in amplification(n, shots=args.shots)])
    if not args.skip_gas:
        print_gas([gas_statistics(n, runs=args.runs) for n in names])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

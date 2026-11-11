"""Run an existing activity instance through T1, GAS and generated Qiskit/Aer."""

import argparse
from dataclasses import replace

from execution.qiskit_executor import execute
from models.gas_defaults import DEFAULT_CONFIG
from models.instances import BY_NAME
from transformations.ilp_to_gas import quantum_sampler, search
from transformations.problem_to_ilp import transform


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", choices=BY_NAME, default="tiny")
    parser.add_argument("--max-rounds", type=int, default=DEFAULT_CONFIG.max_rounds)
    parser.add_argument("--shots", type=int, default=DEFAULT_CONFIG.shots)
    parser.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    args = parser.parse_args(argv)
    config = replace(DEFAULT_CONFIG, max_rounds=args.max_rounds, shots=args.shots, seed=args.seed)
    ilp, mapping = transform(BY_NAME[args.instance].build())
    result = search(ilp, mapping, config, quantum_sampler(execute))
    names = result.selected_activities(mapping)
    if names is None:
        print("No feasible solution found within the search budget.")
    else:
        total = sum(activity.value for activity, bit in zip(mapping, result.bits) if bit)
        if result.objective != -total:
            raise RuntimeError("ILP objective does not equal negative selected activity value")
        print("Selected activities:", ", ".join(names) if names else "(empty selection; feasible)")
        print("Total activity value:", total)
    print("Rounds:", result.rounds)
    print("Stopping reason:", result.stop_reason)
    print("Bounded search does not prove optimality or infeasibility.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

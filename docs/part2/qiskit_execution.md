# Generated Qiskit execution (issue #8)

The runnable path is: existing instance → T1 → adaptive search → BESSER Grover
round → BESSER Qiskit generator → Aer → counts → T1 mapping → activity names.

## Setup and run

From the repository root, use Python 3.12 and the tracked requirements:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B -m run_gas --instance tiny --max-rounds 8 --shots 8 --seed 42
.venv/bin/python -B -m run_gas --instance infeasible --max-rounds 2 --shots 4 --seed 42
```

On this Linux installation Aer requires the bundled OpenMP library preloaded:

```bash
export LD_PRELOAD="$PWD/.venv/lib/python3.12/site-packages/qiskit_aer.libs/libgomp-a34b3233.so.1.0.0"
```

Set that before running the commands above or the tests below. The library path
is installation-specific. `.venv/` is ignored; no environment edits or generated
artifacts need to be committed. Existing environments can install requirements
without being recreated.

The entry point prints selected activity names, total activity value, rounds
and stopping reason. It checks that the ILP objective equals the negative sum of
selected activity values. A feasible empty selection prints value 0; failure to
sample a feasible candidate prints “No feasible solution found within the search
budget.” Neither a returned candidate nor an unsuccessful run proves optimality
or infeasibility. Available instance names are listed by `--help`. All instances
stay within 20 qubits (`python -m validation.qubit_count`); the largest takes
about 16 s with the default solver configuration.

## Generator compatibility

`requirements.txt` pins the course BESSER fork to revision
`9cf7a90928f44dabbe418dab69879014319ee38e`. Qiskit is constrained to version 2.x
because that generator emits the legacy QFT API (deprecated, removed in Qiskit 3).

`execution/qiskit_executor.py::D3QiskitGenerator` subclasses the installed
`QiskitGenerator`. It renders the repository-owned template in
`execution/templates/qiskit_circuit.py.j2`, using BESSER's
`_generate_operations_code` and `_map_operation`. It supplies only the missing
base `PhaseGate(theta)` mapping for `CPhaseGate`; BESSER then applies its control.
The generator retains BESSER's mappings for H, X, Z (including controlled and
multi-controlled Z), Phase, QFT/inverse QFT and Z measurements.

The supported circuit has one quantum register and one classical register, as
produced by `quantum_sampler`. Unsupported gates fail instead of generating
placeholders. Tests check generated phase marking, scratch cleanup, count totals,
bit order and running the generated file without editing it. This is the sole
production generator path; the oracle test converter is not used by the executor.

## Executor contract

```python
from execution.qiskit_executor import execute
counts = execute(besser_circuit, backend="aer_simulator", shots=8, seed=42)
```

Only `aer_simulator` is supported. Backend, shot and seed errors are propagated;
generation or Aer failures never become an empty/no-feasible result. The seed
is applied to both transpilation and simulation. The sampler already advances
its seed between rounds.

Each call generates a new file in a unique temporary directory and runs it in a
fresh namespace, then removes the directory. Threshold changes and new register
sizes therefore cannot reuse a previous round's imported module or bytecode.
Counts remain in Qiskit's displayed order; `quantum_sampler` reverses them once
to the mapping's logical order.

For a persistent, reviewable generated file, call
`D3QiskitGenerator(besser_circuit, output_dir="/tmp/tacs_generated", shots=8).generate()`.
The returned Python path can be executed directly, or loaded to call its
`run(seed=42)` function. Regenerate from the model rather than editing that file.

## Verification

With the OpenMP prefix above where needed:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -W ignore::DeprecationWarning -m unittest tests.test_qiskit_executor -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -W ignore::DeprecationWarning -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m tests.test_problem_dsl
```

The warning filter hides the known upstream Qiskit 2.x deprecation messages only.
Production integration tests use a two-activity example with a unique feasible
selection and the supplied infeasible retreat. The small example reaches its
marked state with probability one after one ideal Grover iteration; tests do not
require unseeded stochastic optimisation success. Tests also execute the tiny
entry point reproducibly, verify later threshold/register changes and reject stale
generated-code reuse. The classical solver is used for verification, not search.

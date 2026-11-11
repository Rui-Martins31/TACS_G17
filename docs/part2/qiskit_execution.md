# Generated Qiskit execution

The runnable path is: existing instance → T1 → adaptive search → BESSER Grover
round → BESSER Qiskit generator → Aer → counts → T1 mapping → activity names.

## Setup and run

From the repository root, create a virtual environment with a Python version
supported by the dependencies in `requirements.txt` (for example, Python 3.12).
Use that interpreter as `python` in the commands below:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -B -m run_gas --instance tiny --max-rounds 8 --shots 8 --seed 42
python -B -m run_gas --instance infeasible --max-rounds 2 --shots 4 --seed 42
```

The activation command above is for Bash/Zsh. In Windows PowerShell, use
`.venv\Scripts\Activate.ps1` instead. Once activated, `python` selects the
environment's interpreter. Existing environments can install requirements without
being recreated. `.venv/` is ignored; environment files and generated artifacts
do not need to be committed.

The entry point prints selected activity names, total activity value, rounds
and stopping reason. It checks that the ILP objective equals the negative sum of
selected activity values. A feasible empty selection prints value 0; failure to
sample a feasible candidate prints “No feasible solution found within the search
budget.” Neither a returned candidate nor an unsuccessful run proves optimality
or infeasibility. Available instance names are listed by `--help`. Check circuit
sizes with `python -m validation.qubit_count`. Simulation time and memory use
depend on qubit count, circuit depth, solver configuration, dependency versions
and hardware; the supplied instances do not define a general simulation limit.

## Generator compatibility

`requirements.txt` pins the course BESSER fork to revision
`9cf7a90928f44dabbe418dab69879014319ee38e`. Qiskit is constrained to version 2.x
because that generator emits the legacy QFT API (deprecated, removed in Qiskit 3).

At the pinned revision, BESSER's Qiskit generator needs a template and a
`CPhaseGate` mapping for the D3 circuits. The repository supplies both through
`execution/qiskit_executor.py::D3QiskitGenerator`, which subclasses BESSER's
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
`D3QiskitGenerator(besser_circuit, output_dir="generated_qiskit", shots=8).generate()`.
The returned Python path can be executed directly, or loaded to call its
`run(seed=42)` function. Regenerate from the model rather than editing that file.

## Troubleshooting Aer imports on Linux

Some Linux environments may fail to import Aer with
`cannot allocate memory in static TLS block`, caused by OpenMP library loading.
If that specific error occurs, preloading Aer's bundled OpenMP library may help.
This is an environment workaround, not a normal setup requirement.

Locate the library in the active environment without assuming a Python version
or a wheel-specific filename:

```bash
python -c "import sysconfig; from pathlib import Path; print(*Path(sysconfig.get_path('platlib')).glob('qiskit_aer.libs/libgomp*.so*'), sep='\n')"
```

If a library path is printed, substitute it below and retry the failing command:

```bash
LD_PRELOAD="/absolute/path/reported/above" python -B -m run_gas --instance tiny
```

The same prefix can be applied to a failing test command. If no matching library
exists, check the Aer installation and its platform-specific dependencies rather
than copying a library path from another machine.

## Verification

Run in the activated environment from the repository root:

```bash
python -B -m unittest tests.test_qiskit_executor -v
python -B -m unittest discover -s tests -v
python -B -m tests.test_problem_dsl
```

Qiskit 2.x may emit deprecation warnings for the generator's legacy QFT API.
Production integration tests use a two-activity example with a unique feasible
selection and the supplied infeasible retreat. The small example reaches its
marked state with probability one after one ideal Grover iteration; tests do not
require unseeded stochastic optimisation success. Tests also execute the tiny
entry point reproducibly, verify later threshold/register changes and reject stale
generated-code reuse. The classical solver is used for verification, not search.

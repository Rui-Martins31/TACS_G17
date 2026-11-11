# D3 solver configuration and T2 search controller

`models/solver_config.py` defines the immutable `SolverConfig` model. A sample
configuration is in `models/gas_defaults.py`; callers may construct another one
or use `dataclasses.replace` to change individual choices. Invalid values fail
at construction, rather than silently falling back to a hard-coded choice.

| Field | Meaning |
|---|---|
| `max_rounds` | Maximum number of search rounds |
| `max_rounds_without_improvement` | Stop after this many consecutive rounds without a better feasible sample |
| `round_policy` | `fixed` or `adaptive` Grover iteration policy |
| `fixed_iterations` | Grover iterations per round under the fixed policy (zero is allowed) |
| `initial_window`, `growth_factor`, `max_window` | Adaptive policy: sample an integer in `[0, floor(window))`; grow the window on failure, reset it on improvement, and cap it |
| `shots` | Requested number of samples per round |
| `seed` | Seed for round selection and the sampler's reproducible stream of per-round execution seeds |
| `backend` | Backend identifier supplied to the sampler |

`transformations.ilp_to_gas.search(ilp_model, mapping, config, sampler)` consumes
the configuration. Initially T2 builds the feasibility oracle. Once a feasible
sample is found, it builds an oracle with the additional integer constraint
`objective - best + 1 <= 0`, so only strict improvements are marked. Every
sample is checked against the original constraints before updating the best.

## Quantum rounds and execution boundary

`build_round(oracle, layout, iterations)` constructs a BESSER quantum model. It
prepares only the decision qubits with H gates, leaving scratch at zero. Each
iteration appends the existing compute/mark/uncompute oracle and then diffusion
on the decision register only: H, X, multi-controlled Z, X, H. This implements
Grover diffusion up to an irrelevant global phase. Zero iterations produces the
uniform decision state. The builder uses the supplied layout every round:
adding or changing the threshold can change the arithmetic register widths.

`quantum_sampler(execute)` connects these rounds to the existing callable
contract `(oracle, layout, iterations, config) -> iterable of bit tuples`.
It adds one classical register and measures decision qubit `layout.variable_qubits[i]`
into classical bit `i`. It calls the injected execution adapter as follows:

```python
counts = execute(besser_circuit, backend=config.backend,
                 shots=config.shots, seed=round_seed)
```

The executor must generate and run the circuit, honour those options, and return
binary counts for that single classical register, totalling `shots`. The sampler
reverses Qiskit's displayed `c[n-1] ... c[0]` labels into logical decision tuples
in mapping insertion order. It validates the count labels and multiplicities.
Create a fresh sampler for each search: it seeds a private random stream once,
then advances it for each execution instead of resetting the backend identically.

Production generation/execution is provided by
`execution.qiskit_executor.execute`. Its repository-tracked BESSER generator
subclass supplies the missing template and controlled-phase mapping, retaining
BESSER's gate mapper for the remaining D3 operations. Each round generates and
executes fresh code on Aer. See [setup, runnable command and supported gates](qiskit_execution.md).

`tests/test_gas_simulator.py` retains the independent test converter for quantum
checks. `tests/test_qiskit_executor.py` additionally tests the actual production
generator/executor, including direct execution of generated files, changed
threshold layouts and baseline agreement. The classical solver is used only for
verification. Quantum hardware has not been tested.

## Usage

Use the production executor with the existing sampler:

```python
from models.gas_defaults import DEFAULT_CONFIG
from transformations.problem_to_ilp import transform
from transformations.ilp_to_gas import quantum_sampler, search
from execution.qiskit_executor import execute

def run_gas(problem_model, config=DEFAULT_CONFIG):
    ilp_model, mapping = transform(problem_model)
    result = search(ilp_model, mapping, config, quantum_sampler(execute))
    return result, result.selected_activities(mapping)
```

Activity names are decoded using the original T1 mapping. Do not reorder it by
ILP object-set iteration or raw measurement labels. A feasible empty selection
decodes to `()`, while no feasible candidate found decodes to `None`.

The returned `SearchResult` reports the best observed assignment and objective,
round count and stopping reason. An empty result means no feasible sample was
observed, not that the instance is proven infeasible. Likewise, stopping after
finite rounds does not prove that a sampled solution is optimal.

## Verification

Deterministic controller/adapter tests and actual simulator tests are separate:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest tests.test_solver_config tests.test_ilp_to_gas -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest tests.test_gas_simulator -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest tests.test_qiskit_executor -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m tests.test_problem_dsl
```

The standalone Problem DSL `run()` is not invoked by unittest discovery, so its
module command must run separately. Quantum tests check scratch cleanup,
amplification, strict threshold phases, changing layouts, decision ordering,
seeded Aer sampling and baseline agreement. Their small unique-feasible example
has exactly one marked state out of four, so one Grover iteration selects it with
probability one in the ideal simulator. No unseeded stochastic success is required.

On this Linux environment, importing Aer needs its bundled OpenMP library
preloaded to avoid `cannot allocate memory in static TLS block`. The simulator
and discovery commands passed with this prefix (adjust the library path for
another Python/Aer installation):

```bash
LD_PRELOAD="$PWD/.venv/lib/python3.12/site-packages/qiskit_aer.libs/libgomp-a34b3233.so.1.0.0" PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s tests -v
```

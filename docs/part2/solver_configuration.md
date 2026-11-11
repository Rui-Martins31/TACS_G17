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
| `seed` | Seed for round selection; also supplied to the sampler for execution |
| `backend` | Backend identifier supplied to the sampler |

`transformations.ilp_to_gas.search(ilp_model, mapping, config, sampler)` consumes
the configuration. Initially T2 builds the feasibility oracle. Once a feasible
sample is found, it builds an oracle with the additional integer constraint
`objective - best + 1 <= 0`, so only strict improvements are marked. Every
sample is checked against the original constraints before updating the best.

The sampler is a callable `(oracle, layout, iterations, config)` returning an
iterable of bit tuples in T1 mapping order. It must prepare the search state,
apply the oracle and diffusion for the requested iterations, execute using the
configured backend, shots and seed, and decode measurements. **A quantum sampler,
diffusion circuit and backend integration are not implemented yet.** The
controller and its tests use an injected sampler; passing configuration does not
itself run a quantum circuit. A backend may manage its random seed across rounds
to avoid restarting the same random sequence each time.

The returned `SearchResult` reports the best observed assignment and objective,
round count and stopping reason. An empty result means no feasible sample was
observed, not that the instance is proven infeasible. Likewise, stopping after
finite rounds does not prove that a sampled solution is optimal.

```bash
python -m unittest tests.test_solver_config -v
```

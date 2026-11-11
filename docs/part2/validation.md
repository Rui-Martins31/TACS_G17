# Validation against the classical baseline

Every instance runs through the production chain (T1 → oracle/T2 → BESSER Qiskit
generator → Aer) and is compared with the exact brute-force baseline
(`validation/classical_baseline.py`). Reproduce everything with:

```bash
python -m validation.qubit_count           # circuit sizes
python -m validation.quantum_vs_classical  # experiments A and B
python -m validation.quantum_vs_classical --skip-gas   # experiment A only
```

Run in the activated project environment. Runtime depends on hardware, dependency
versions, circuit sizes and solver configuration. For conditional Aer import
troubleshooting, see [Qiskit execution](qiskit_execution.md#troubleshooting-aer-imports-on-linux).

## Instances and qubits

| Instance | Activities | Brute force 2^n | Feasible | Optima | Peak qubits |
|---|---:|---:|---:|---:|---:|
| tiny | 3 | 8 | 6 | 1 | 8 |
| infeasible | 4 | 16 | 0 | 0 | 10 |
| multi_optima | 5 | 32 | 18 | 4 | 14 |
| medium | 4 | 16 | 8 | 1 | 15 |
| large | 9 | 512 | 96 | 1 | 20 |

Peak qubits = activities + one register per constraint atom (2 qubits per conflict
or mandatory activity) + the threshold register added after the first round. All
instances stay within the ~20-qubit limit of Annex A.

## A. Amplification: does the generated circuit behave as Grover predicts?

One Grover round with k iterations, 2048 shots. "Valid" marks feasible selections
(round-1 oracle); "optimal" adds the threshold atom `g(y) − g* ≤ 0`, marking only
the optimal selections. M (marked count) comes from the classical baseline. The
ideal value is `P(k) = sin²((2k+1)θ)`, `sin θ = √(M/N)` (Boyer et al. 1998;
Nielsen & Chuang §6.1). k = 0 is uniform sampling; the largest k listed is the
best number of iterations, `⌊π / 4θ⌋`.

| Instance | Marked | M / N | k | Ideal P(k) | Measured |
|---|---|---:|---:|---:|---:|
| tiny | valid | 6/8 | 0 | 0.750 | 0.727 |
| tiny | valid | 6/8 | 1 | 0.000 | 0.000 |
| tiny | optimal | 1/8 | 0 | 0.125 | 0.124 |
| tiny | optimal | 1/8 | 1 | 0.781 | 0.772 |
| tiny | optimal | 1/8 | 2 | 0.945 | 0.936 |
| infeasible | valid | 0/16 | 0 | 0.000 | 0.000 |
| infeasible | valid | 0/16 | 1 | 0.000 | 0.000 |
| multi_optima | valid | 18/32 | 0 | 0.562 | 0.550 |
| multi_optima | valid | 18/32 | 1 | 0.316 | 0.311 |
| multi_optima | optimal | 4/32 | 0 | 0.125 | 0.131 |
| multi_optima | optimal | 4/32 | 1 | 0.781 | 0.775 |
| multi_optima | optimal | 4/32 | 2 | 0.945 | 0.945 |
| medium | valid | 8/16 | 0 | 0.500 | 0.488 |
| medium | valid | 8/16 | 1 | 0.500 | 0.513 |
| medium | optimal | 1/16 | 0 | 0.062 | 0.060 |
| medium | optimal | 1/16 | 1 | 0.473 | 0.479 |
| medium | optimal | 1/16 | 3 | 0.961 | 0.958 |
| large | valid | 96/512 | 0 | 0.187 | 0.180 |
| large | valid | 96/512 | 1 | 0.949 | 0.954 |
| large | optimal | 1/512 | 0 | 0.002 | 0.003 |
| large | optimal | 1/512 | 1 | 0.017 | 0.014 |
| large | optimal | 1/512 | 17 | 0.999 | 0.999 |

All measurements are within sampling error (σ ≈ 0.01 at 2048 shots). Since M is
counted classically, agreement checks oracle marking, the `−1` shift of `≤`
atoms, uncomputation, diffusion and qubit order together.
`tests/test_quantum_vs_classical.py` asserts agreement within 5σ; we checked that
it fails when the uncompute step is removed, when the qubit order is reversed and
when the `−1` shift is dropped.

Observations:
- **Over-rotation.** tiny with M/N = 6/8: one iteration drops P(valid) from 0.75
  to 0. When M/N is large, more iterations make things worse. This is why GAS
  draws the iteration count at random (Boyer et al.) instead of fixing it.
- **Large, optimal.** With 1 optimal selection among 512, 17 iterations measure
  it with probability 0.999, against 1/512 by uniform sampling.

## B. Grover Adaptive Search vs exact optimum

10 runs (seeds 0–9) per instance, default solver configuration
(`models/gas_defaults.py`: adaptive iterations, window starting at 1 with growth
1.2 and cap 16, 1 shot per round, at most 100 rounds, stop after 20 rounds
without improvement). Oracle calls = Σ over rounds of k × shots. "To answer"
counts calls up to the round that found the returned selection; "total" adds the
rounds the stopping rule spends confirming no further improvement.

| Instance | Qubits | Brute force 2^n | Optimum found | Oracle calls to answer (median / mean) | Oracle calls total (mean) | Rounds (mean) |
|---|---:|---:|---:|---:|---:|---:|
| tiny | 8 | 8 | 10/10 | 0 / 0.5 | 60.6 | 25.9 |
| infeasible | 10 | 16 | 10/10 (none reported) | 0 / 0.0 | 63.8 | 20.0 |
| multi_optima | 14 | 32 | 10/10 | 0 / 0.2 | 62.4 | 24.5 |
| medium | 15 | 16 | 10/10 | 0 / 0.6 | 60.7 | 28.9 |
| large | 20 | 512 | 10/10 | 29 / 29.4 | 93.3 | 54.7 |

Observations:
- Every run returned an exact optimum; for multi_optima, any of the four is accepted.
- **Small instances need no oracle calls.** The adaptive window starts at 1, so
  early rounds use k = 0 (uniform sampling). With N ≤ 32, sampling alone finds
  the optimum, so the median number of oracle calls before the answer is 0.
- **Large.** About 29 oracle calls before the answer, on the order of
  √512 ≈ 23. That is the expected scale for Dürr–Høyer (O(√N)), compared with
  512 classical evaluations.
- **Stopping rule.** Most of the total oracle calls come from the 20 rounds
  without improvement needed to stop. That is a solver-configuration choice, not
  part of finding the answer.

## Limitations (notes for the report)

- A bounded search proves neither optimality nor infeasibility; only the
  classical baseline does. The infeasible instance "succeeds" only in the sense
  that no feasible selection was ever measured.
- Each conflict or mandatory activity costs a 2-qubit register and the threshold
  costs ~5, so 20 qubits allows only about 9 activities with few conflicts. The
  instances are deliberately small and easy for brute force (Annex A, final remarks).
- Simulation is ideal (statevector, no noise). Gate counts and depth were not
  optimised, and real hardware was not tried.
- Experiment B uses 10 seeds per instance, so success rates are coarse estimates.
- The generated code uses Qiskit's legacy `QFT` class, deprecated in Qiskit 2.1
  and removed in 3.0 (the requirements pin Qiskit 2.x).

"""Integration tests through the production BESSER generator and Aer executor."""

from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from itertools import product
from runpy import run_path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
from qiskit.quantum_info import Statevector
from besser.BUML.metamodel.quantum import quantum as bq
from besser.generators.qiskit.qiskit_generator import QiskitGenerator

from execution.qiskit_executor import D3QiskitGenerator, execute
from models.gas_defaults import DEFAULT_CONFIG
from models.instances.infeasible_retreat import build as infeasible
from run_gas import main
from tests.test_gas_simulator import unique_feasible_plan
from transformations.ilp_to_gas import SearchResult, build_round, quantum_sampler, search
from transformations.ilp_to_oracle import Atom, build_oracle
from transformations.problem_to_ilp import transform
from validation.classical_baseline import solve


def measured_round():
    ilp, mapping = transform(unique_feasible_plan())
    oracle, layout = build_oracle(ilp, mapping)
    circuit = build_round(oracle, layout, 1)
    circuit.add_creg(bq.ClassicalRegister("c", len(mapping)))
    for i, qubit in enumerate(layout.variable_qubits):
        circuit.add_operation(bq.Measurement(qubit, i))
    return circuit, oracle, layout


class TestProductionGenerator(unittest.TestCase):
    def test_generated_file_runs_directly_without_edits(self):
        circuit, _, _ = measured_round()
        with TemporaryDirectory() as directory:
            generator = D3QiskitGenerator(circuit, directory, shots=8)
            self.assertIsInstance(generator, QiskitGenerator)
            path = generator.generate()
            original = path.read_bytes()
            completed = subprocess.run([sys.executable, "-B", str(path)], check=True,
                                       capture_output=True, text=True)
            self.assertEqual(completed.stdout.strip(), "{'01': 8}")
            self.assertEqual(path.read_bytes(), original)

    def test_generated_phase_oracle_and_scratch_cleanup(self):
        ilp, mapping = transform(unique_feasible_plan())
        for extra in ((), (Atom("threshold", "LE", 3, {0: -2, 1: -1}),)):
            oracle, layout = build_oracle(ilp, mapping, extra)
            oracle.add_creg(bq.ClassicalRegister("c", len(mapping)))
            with self.subTest(threshold=bool(extra)), TemporaryDirectory() as directory:
                path = D3QiskitGenerator(oracle, directory).generate()
                circuit = run_path(str(path))["build_circuit"]()
                for bits in product((0, 1), repeat=2):
                    index = bits[0] + 2 * bits[1]
                    initial = Statevector.from_int(index, 2 ** layout.num_qubits)
                    expected = -initial if bits == (1, 0) and not extra else initial
                    self.assertTrue(np.allclose(initial.evolve(circuit).data, expected.data,
                                                atol=1e-6), bits)

    def test_counts_and_sampler_use_distinct_bit_order_contracts(self):
        circuit, oracle, layout = measured_round()
        options = dict(backend="aer_simulator", shots=8, seed=42)
        counts = execute(circuit, **options)
        self.assertEqual(counts, {"01": 8})
        self.assertEqual(execute(circuit, **options), counts)
        config = replace(DEFAULT_CONFIG, shots=8)
        self.assertEqual(quantum_sampler(execute)(oracle, layout, 1, config), [(1, 0)] * 8)

    def test_same_named_circuits_do_not_reuse_old_generated_code(self):
        for n, selected in ((2, 0), (3, 2), (2, 1)):
            circuit = bq.QuantumCircuit("same_name", n)
            circuit.add_creg(bq.ClassicalRegister("c", n))
            circuit.add_operation(bq.PauliXGate(selected))
            for i in range(n):
                circuit.add_operation(bq.Measurement(i, i))
            self.assertEqual(execute(circuit, backend="aer_simulator", shots=3, seed=0),
                             {format(1 << selected, f"0{n}b"): 3})

    def test_generation_and_execution_errors_propagate(self):
        circuit, _, _ = measured_round()
        with self.assertRaisesRegex(ValueError, "aer_simulator"):
            execute(circuit, backend="ibm_quantum", shots=1, seed=1)
        for kwargs in ({"shots": 0, "seed": 1}, {"shots": 1, "seed": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                execute(circuit, backend="aer_simulator", **kwargs)
        circuit.add_operation(bq.ComparisonGate("LessThan", [0], [1]))
        with self.assertRaisesRegex(NotImplementedError, "ComparisonGate"):
            execute(circuit, backend="aer_simulator", shots=1, seed=1)
        circuit, _, _ = measured_round()
        with patch("execution.qiskit_executor.run_path", side_effect=RuntimeError("Aer failed")):
            with self.assertRaisesRegex(RuntimeError, "Aer failed"):
                execute(circuit, backend="aer_simulator", shots=1, seed=1)


class TestProductionSearch(unittest.TestCase):
    def test_search_threshold_round_and_baseline(self):
        source = unique_feasible_plan()
        ilp, mapping = transform(source)
        config = replace(DEFAULT_CONFIG, round_policy="fixed", fixed_iterations=1, shots=8,
                         max_rounds=2, max_rounds_without_improvement=3)
        sizes = []
        def recording_execute(circuit, **options):
            sizes.append(circuit.num_qubits)
            return execute(circuit, **options)
        result = search(ilp, mapping, config, quantum_sampler(recording_execute))
        self.assertGreater(sizes[1], sizes[0])
        baseline = solve(source)
        self.assertEqual(result.bits, (1, 0))
        self.assertIn(frozenset(result.selected_activities(mapping)), baseline.optimal_selections)
        self.assertEqual(-result.objective, baseline.optimum_value)

    def test_supplied_infeasible_instance(self):
        source = infeasible()
        ilp, mapping = transform(source)
        config = replace(DEFAULT_CONFIG, round_policy="fixed", fixed_iterations=1, shots=4,
                         max_rounds=2, max_rounds_without_improvement=3)
        result = search(ilp, mapping, config, quantum_sampler(execute))
        self.assertIsNone(result.bits)
        self.assertIsNone(result.selected_activities(mapping))
        self.assertEqual(result.rounds, 2)
        self.assertEqual(solve(source).feasible_count, 0)


class TestGasEntryPoint(unittest.TestCase):
    def output(self, args):
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(args), 0)
        return stdout.getvalue()

    def test_runnable_entry_point_is_seeded(self):
        args = ["--instance", "tiny", "--max-rounds", "2", "--shots", "8", "--seed", "42"]
        output = self.output(args)
        self.assertEqual(output, self.output(args))
        self.assertIn("Selected activities:", output)
        self.assertIn("Total activity value:", output)
        self.assertIn("Rounds: 2", output)
        self.assertIn("Stopping reason: max_rounds", output)

    def test_no_feasible_candidate_message(self):
        output = self.output(["--instance", "infeasible", "--max-rounds", "1", "--shots", "2"])
        self.assertIn("No feasible solution found within the search budget.", output)
        self.assertNotIn("Total activity value:", output)

    def test_empty_selection_and_objective_value_check(self):
        # Default instance is tiny (3 activities), so results carry 3 bits.
        with patch("run_gas.search", return_value=SearchResult((0, 0, 0), 0, 1, "max_rounds")):
            output = self.output(["--max-rounds", "1"])
        self.assertIn("empty selection; feasible", output)
        self.assertIn("Total activity value: 0", output)
        with patch("run_gas.search", return_value=SearchResult((1, 0, 0), 0, 1, "max_rounds")):
            with self.assertRaisesRegex(RuntimeError, "negative selected activity value"):
                self.output(["--max-rounds", "1"])


if __name__ == "__main__":
    unittest.main()

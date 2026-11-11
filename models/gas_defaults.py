"""An example set of solver choices; applications may construct their own."""

from models.solver_config import SolverConfig

DEFAULT_CONFIG = SolverConfig(
    max_rounds=100,
    max_rounds_without_improvement=20,
    round_policy="adaptive",
    fixed_iterations=1,
    initial_window=1,
    growth_factor=1.2,
    max_window=16,
    shots=1,
    seed=42,
    backend="aer_simulator",
)

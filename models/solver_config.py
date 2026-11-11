"""Solver configuration model for the D3 adaptive search controller."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class SolverConfig:
    # Stop after either limit; neither limit proves optimality or infeasibility.
    max_rounds: int
    max_rounds_without_improvement: int
    # fixed: always use fixed_iterations; adaptive: sample [0, window),
    # growing the window after unsuccessful rounds and resetting it on improvement.
    round_policy: str
    fixed_iterations: int
    initial_window: int
    growth_factor: float
    max_window: int
    shots: int
    seed: int | None
    backend: str

    def __post_init__(self):
        for name in ("max_rounds", "max_rounds_without_improvement", "initial_window",
                     "max_window", "shots"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.fixed_iterations) is not int or self.fixed_iterations < 0:
            raise ValueError("fixed_iterations must be a nonnegative integer")
        if self.round_policy not in {"fixed", "adaptive"}:
            raise ValueError("round_policy must be 'fixed' or 'adaptive'")
        if not isinstance(self.growth_factor, (int, float)) or isinstance(self.growth_factor, bool) or not isfinite(self.growth_factor) or self.growth_factor < 1:
            raise ValueError("growth_factor must be finite and at least 1")
        if self.initial_window > self.max_window:
            raise ValueError("initial_window cannot exceed max_window")
        if self.seed is not None and type(self.seed) is not int:
            raise ValueError("seed must be an integer or None")
        if not isinstance(self.backend, str) or not self.backend.strip():
            raise ValueError("backend must be a nonempty string")

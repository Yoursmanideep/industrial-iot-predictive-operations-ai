from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID


@dataclass
class SimulationContext:
    """Mutable execution context shared by later simulation stages."""

    simulator_run_id: UUID
    deterministic_seed: int
    generator_version: str
    configuration_version: str
    current_time: datetime
    generation_sequence: int = 0

    def __post_init__(self) -> None:
        if self.current_time.tzinfo is None:
            raise ValueError("current_time must be timezone-aware.")
        if self.deterministic_seed < 0:
            raise ValueError("deterministic_seed must be non-negative.")
        if self.generation_sequence < 0:
            raise ValueError("generation_sequence cannot be negative.")

    def next_sequence(self) -> int:
        """Advance and return the next run-scoped generation sequence."""
        self.generation_sequence += 1
        return self.generation_sequence

    def now_utc(self) -> datetime:
        """Return current simulation time normalized to UTC."""
        return self.current_time.astimezone(timezone.utc)

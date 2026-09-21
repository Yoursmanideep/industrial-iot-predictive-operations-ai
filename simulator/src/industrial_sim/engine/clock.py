from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class SimulationClock:
    """Simulation-time clock independent from wall-clock execution time."""

    current_time: datetime
    tick_seconds: int = 5

    def __post_init__(self) -> None:
        if self.current_time.tzinfo is None:
            raise ValueError("Simulation clock requires a timezone-aware datetime.")
        if self.tick_seconds <= 0:
            raise ValueError("tick_seconds must be greater than zero.")

    def tick(self) -> datetime:
        self.current_time += timedelta(seconds=self.tick_seconds)
        return self.current_time

    def advance(self, seconds: int) -> datetime:
        if seconds < 0:
            raise ValueError("Cannot move simulation time backwards.")
        self.current_time += timedelta(seconds=seconds)
        return self.current_time

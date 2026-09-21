from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class RunMode(StrEnum):
    BOOTSTRAP = "BOOTSTRAP"
    BACKFILL = "BACKFILL"
    LIVE = "LIVE"
    REPLAY = "REPLAY"


class RunStatus(StrEnum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REPLAYED = "REPLAYED"


@dataclass(frozen=True)
class SimulationRun:
    simulator_run_id: UUID
    run_mode: RunMode
    generator_version: str
    configuration_version: str
    deterministic_seed: int
    simulation_start_time: datetime
    simulation_end_time: datetime
    source_run_id: UUID | None = None
    status: RunStatus = RunStatus.PLANNED

    def __post_init__(self) -> None:
        if self.deterministic_seed < 0:
            raise ValueError("deterministic_seed must be non-negative.")
        if self.simulation_start_time.tzinfo is None:
            raise ValueError("simulation_start_time must be timezone-aware.")
        if self.simulation_end_time.tzinfo is None:
            raise ValueError("simulation_end_time must be timezone-aware.")
        if self.simulation_end_time < self.simulation_start_time:
            raise ValueError("simulation_end_time cannot precede simulation_start_time.")
        if self.run_mode is RunMode.REPLAY and self.source_run_id is None:
            raise ValueError("REPLAY runs require source_run_id.")

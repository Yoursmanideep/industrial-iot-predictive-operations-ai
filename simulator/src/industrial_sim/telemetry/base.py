from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from industrial_sim.domain.machine import Machine
from industrial_sim.machines.base import MachineBehaviorContext


@dataclass(frozen=True)
class TelemetryPhysicsContext:
    machine: Machine
    behavior_context: MachineBehaviorContext
    event_time: datetime

    def __post_init__(self) -> None:
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware.")


class TelemetryPhysics(Protocol):
    machine_type: str

    def generate(self, context: TelemetryPhysicsContext) -> dict[str, float]:
        ...
